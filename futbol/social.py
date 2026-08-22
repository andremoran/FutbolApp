# -*- coding: utf-8 -*-
"""
futbol/social.py — Lo que conecta al entrenador con su plantilla.

· Mensajes  — el entrenador escribe al equipo o a un jugador concreto.
· Partidos  — resultados y estadísticas individuales.
· Observaciones de entrenamiento — notas del coach tras cada sesión.
"""
import logging
from datetime import datetime, timezone
from functools import wraps

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles
from roles import solo_pro

from . import bp, db

logger = logging.getLogger(__name__)


def solo_entrenador(f):
    @wraps(f)
    @login_required
    def wrapper(*a, **kw):
        if getattr(current_user, 'role', '') != 'especialista':
            return redirect(url_for('futbol.inicio'))
        return f(*a, **kw)
    return wrapper


def _ahora():
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════ MENSAJES ═══════════════════════
@bp.route('/coach/mensajes')
@solo_entrenador
def c_mensajes():
    uid = db.equipo_id(current_user.id)
    jugadores = db.jugadores_del_entrenador(uid)
    por_id = {j['id']: j for j in jugadores}

    enviados = db.rows('fut_messages', 'mensajes coach', coach_id=uid,
                       _order='creado', _desc=True, _limit=50)
    for m in enviados:
        m['_fecha'] = db.parse_fecha(m.get('creado'))
        m['_destino'] = (por_id.get(m.get('player_id'), {}).get('name')
                         if m.get('player_id') else 'Todo el equipo')

    return render_template('c_mensajes.html',
                           tab_activa='equipo', hide_tabbar=True,
                           jugadores=jugadores, mensajes=enviados)


@bp.route('/mensajes')
@login_required
def mensajes():
    """Bandeja del jugador: lo dirigido a él más lo enviado a todo el equipo."""
    uid = current_user.id
    coach = db.entrenador_del_jugador(uid)
    lista = []

    if coach:
        todos = db.rows('fut_messages', 'mensajes jugador', coach_id=coach['id'],
                        _order='creado', _desc=True, _limit=60)
        lista = [m for m in todos
                 if not m.get('player_id') or str(m['player_id']) == str(uid)]
        for m in lista:
            m['_fecha'] = db.parse_fecha(m.get('creado'))
            m['_para_mi'] = bool(m.get('player_id'))

        # Marcar como leídos los personales. Sin obligatorio: esto pasa
        # mientras se pinta la pantalla, y no verlo en negrita es mucho menos
        # grave que romperle los mensajes al jugador por un fallo de red.
        for m in lista:
            if m.get('player_id') and not m.get('leido'):
                db.update('fut_messages', {'leido': True}, 'leer', id=m['id'])

    return render_template('p_mensajes.html',
                           tab_activa='inicio', hide_tabbar=True,
                           mensajes=lista, entrenador=coach)


@bp.route('/api/mensaje', methods=['POST'])
@login_required
def api_mensaje():
    from .api import api_guard, cuerpo

    err = api_guard(solo_coach=True)
    if err:
        return err

    d = cuerpo()
    texto = (d.get('texto') or '').strip()
    if not texto:
        return jsonify({'error': 'Escribe el mensaje.'}), 400

    destino = d.get('player_id') or None
    if destino:
        mios = {str(j['id']) for j in db.jugadores_del_entrenador(db.equipo_id(current_user.id))}
        if str(destino) not in mios:
            return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    fila = db.insert('fut_messages', {
        'coach_id': db.equipo_id(current_user.id),
        'player_id': destino,
        'texto': texto[:2000],
        'leido': False,
        'creado': _ahora(),
    }, 'enviar mensaje')
    if not fila:
        return jsonify({'error': 'No se pudo enviar.'}), 500
    return jsonify({'ok': True})


@bp.route('/api/mensaje/<mid>', methods=['DELETE'])
@login_required
def api_mensaje_borrar(mid):
    from .api import api_guard

    err = api_guard(solo_coach=True)
    if err:
        return err
    db.delete('fut_messages', 'borrar mensaje', id=mid, coach_id=db.equipo_id(current_user.id), obligatorio=True)
    return jsonify({'ok': True})


# ═══════════════════════ PARTIDOS (entrenador) ═══════════════════════
@bp.route('/coach/partidos')
@solo_entrenador
def c_partidos():
    uid = db.equipo_id(current_user.id)
    partidos = db.rows('fut_matches', 'partidos coach', coach_id=uid,
                       _order='fecha', _desc=True, _limit=40)

    balance = {'ganados': 0, 'empatados': 0, 'perdidos': 0, 'gf': 0, 'gc': 0}
    for m in partidos:
        m['_fecha'] = db.parse_fecha(m.get('fecha'))
        gf, gc = int(m.get('goles_favor') or 0), int(m.get('goles_contra') or 0)
        balance['gf'] += gf
        balance['gc'] += gc
        balance['ganados' if gf > gc else ('perdidos' if gf < gc else 'empatados')] += 1

    return render_template('c_partidos.html',
                           tab_activa='agenda', hide_tabbar=True,
                           partidos=partidos, balance=balance,
                           hoy=db.hoy_iso())


@bp.route('/coach/partidos/<mid>')
@solo_entrenador
def c_partido(mid):
    uid = db.equipo_id(current_user.id)
    partido = db.one('fut_matches', 'partido', id=mid, coach_id=uid)
    if not partido:
        abort(404)
    partido['_fecha'] = db.parse_fecha(partido.get('fecha'))

    jugadores = db.jugadores_del_entrenador(uid)
    stats = {s['player_id']: s for s in db.rows('fut_match_stats', 'stats', match_id=mid)}
    for j in jugadores:
        j['_stats'] = stats.get(j['id'], {})

    return render_template('c_partido.html',
                           tab_activa='agenda', hide_tabbar=True,
                           partido=partido, jugadores=jugadores)


# ═══════════════════════ OBSERVACIONES DE ENTRENAMIENTO ═══════════════════════
def _evento_del_coach(eid, uid):
    """El evento, solo si es de este equipo. None si no lo es o no existe.

    Se comprueba SIEMPRE contra el equipo y no contra quien mira: un asistente
    entra a la ficha del entreno del principal, y si aqui se filtrara por
    current_user.id la observacion se le quedaria colgando sin sesion.
    """
    if not eid:
        return None
    return db.one('fut_events', 'evento de la observacion', id=eid, coach_id=uid)


def _titulo_de_sesion(ev):
    """«Presion alta · jue 21/08» — para encabezar la observacion."""
    if not ev:
        return ''
    f = db.parse_fecha(ev.get('fecha'))
    return '%s%s' % (ev.get('titulo') or 'Sesion',
                     ' · ' + f.strftime('%d/%m/%Y') if f else '')


@bp.route('/coach/observaciones')
@solo_entrenador
def c_observaciones():
    uid = db.equipo_id(current_user.id)
    lista = db.rows('fut_observaciones', 'observaciones', coach_id=uid,
                    _order='fecha', _desc=True, _limit=40)
    jugadores = {j['id']: j for j in db.jugadores_del_entrenador(uid)}
    for o in lista:
        o['_fecha'] = db.parse_fecha(o.get('fecha'))
        o['_jugador'] = jugadores.get(o.get('player_id'), {}).get('name')

    #  Al entrar desde la ficha de un entreno, la pantalla tiene que saber de
    #  cual. Antes el enlace ya mandaba ?evento=<id> pero aqui se ignoraba, y
    #  ademas la columna event_id no existia: la observacion quedaba suelta y
    #  la ficha del entreno nunca llegaba a decir que ya habia una.
    evento = _evento_del_coach(request.args.get('evento'), uid)
    ya = None
    if evento:
        ya = next((o for o in lista if o.get('event_id') == evento['id']), None)

    return render_template('c_observaciones.html',
                           tab_activa='agenda', hide_tabbar=True,
                           observaciones=lista,
                           jugadores=list(jugadores.values()),
                           hoy=db.hoy_iso(),
                           evento=evento,
                           titulo_sesion=_titulo_de_sesion(evento),
                           observacion_previa=ya,
                           es_pro=roles.es_pro(current_user))


@bp.route('/api/observacion', methods=['POST'])
@login_required
def api_observacion():
    from .api import api_guard, cuerpo

    err = api_guard(solo_coach=True)
    if err:
        return err

    d = cuerpo()
    texto = (d.get('texto') or '').strip()
    if not texto:
        return jsonify({'error': 'Escribe la observación.'}), 400

    destino = d.get('player_id') or None
    if destino:
        mios = {str(j['id']) for j in db.jugadores_del_entrenador(db.equipo_id(current_user.id))}
        if str(destino) not in mios:
            return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    uid = db.equipo_id(current_user.id)

    #  El entreno del que sale. Se valida contra el equipo: con un id de otro
    #  la observacion se guardaria colgada de una sesion ajena.
    evento = _evento_del_coach(d.get('event_id'), uid)
    if d.get('event_id') and not evento:
        return jsonify({'error': 'Ese entrenamiento no es de tu equipo.'}), 403

    datos = {
        'coach_id': uid,
        'player_id': destino,
        'event_id': evento['id'] if evento else None,
        'fecha': (evento or {}).get('fecha') or d.get('fecha') or db.hoy_iso(),
        'titulo': (d.get('titulo') or 'Sesión')[:120],
        'texto': texto[:4000],
        'transcripcion': (d.get('transcripcion') or '').strip()[:6000] or None,
        'analisis_ia': (d.get('analisis_ia') or '').strip()[:4000] or None,
        'audio_segundos': _entero(d.get('audio_segundos')),
        'creado': _ahora(),
    }

    #  Editar la que ya hay en vez de amontonar otra: una sesion tiene UNA
    #  observacion, y al volver a entrar desde la ficha del entreno lo que se
    #  espera es seguir la de antes.
    previa = d.get('id')
    if previa:
        filas = db.update('fut_observaciones', datos, 'observacion editada',
                          id=previa, coach_id=uid)
        if not filas:
            return jsonify({'error': 'Esa observación no es tuya o ya no existe.'}), 404
        return jsonify({'ok': True, 'id': previa})

    fila = db.insert('fut_observaciones', datos, 'observacion')
    if not fila:
        return jsonify({'error': 'No se pudo guardar.'}), 500
    return jsonify({'ok': True, 'id': fila['id']})


# ═══════════════════════ NOTAS DE VOZ ═══════════════════════
@bp.route('/api/observacion/voz', methods=['POST'])
@login_required
@solo_pro('ia')
def api_observacion_voz():
    """Recibe las notas dictadas, las transcribe y las lee como entrenador.

    No guarda nada: devuelve el texto para que el entrenador lo vea, lo
    corrija si hace falta y decida. Guardar por su cuenta lo que ha entendido
    una maquina, sin que el coach lo haya leido, es justo lo que no se quiere
    en una ficha de la que despues cuelgan evaluaciones.
    """
    from .api import api_guard, cuerpo
    from .ia import FORMATOS_AUDIO, MAX_AUDIO_MB, analizar_notas_de_voz

    err = api_guard(solo_coach=True)
    if err:
        return err

    d = cuerpo()
    notas = d.get('audios') or []
    if not isinstance(notas, list) or not notas:
        return jsonify({'error': 'No llegó ninguna nota de voz.'}), 400
    if len(notas) > 8:
        return jsonify({'error': 'Máximo 8 notas de voz a la vez.'}), 400

    audios, total = [], 0
    for n in notas:
        if not isinstance(n, dict):
            continue
        mime = (n.get('mime') or 'audio/webm').split(';')[0].strip().lower()
        datos = (n.get('datos') or '').strip()
        if not datos:
            continue
        if mime not in FORMATOS_AUDIO:
            return jsonify({'error': 'Ese formato de audio no vale (%s).' % mime}), 400
        #  base64 abulta un tercio mas que el binario.
        total += len(datos) * 3 // 4
        audios.append((mime, datos))

    if not audios:
        return jsonify({'error': 'Las notas llegaron vacías.'}), 400
    if total > MAX_AUDIO_MB * 1024 * 1024:
        return jsonify({'error': 'Son demasiados minutos de audio. Graba notas '
                                 'más cortas y súbelas por tandas.'}), 413

    uid = db.equipo_id(current_user.id)
    evento = _evento_del_coach(d.get('event_id'), uid)
    contexto = _contexto_de_sesion(evento, uid)

    transcripcion, analisis = analizar_notas_de_voz(audios, contexto)
    if not transcripcion and not analisis:
        return jsonify({'error': 'La IA no pudo con el audio. Vuelve a '
                                 'intentarlo en un momento.'}), 503

    return jsonify({'ok': True,
                    'transcripcion': transcripcion or '',
                    'analisis': analisis or '',
                    'titulo': _titulo_de_sesion(evento) or None})


def _contexto_de_sesion(evento, uid):
    """Cuatro datos de la sesion para que la IA sepa de que le hablan.

    Sin esto la lectura sale generica: con el tipo de entreno, la duracion y
    quien falto, la IA puede atar lo que dice el audio a lo que ya se sabe.
    """
    if not evento:
        return ''
    from . import calendario as cal

    trozos = ['Entreno del %s' % (evento.get('fecha') or 'sin fecha')]
    if evento.get('titulo'):
        trozos.append('"%s"' % evento['titulo'])
    if evento.get('tipo_entreno'):
        meta = cal.ENTRENO_META.get(evento['tipo_entreno'], {})
        trozos.append((meta.get('etiqueta') or evento['tipo_entreno']).lower())
    if evento.get('duracion_min'):
        trozos.append('%s min' % evento['duracion_min'])
    if evento.get('intensidad'):
        trozos.append('intensidad %s' % evento['intensidad'])

    marcas = db.asistencia_de([evento['id']]) or []
    if marcas:
        faltaron = [m for m in marcas if m.get('estado') in ('ausente', 'justificado')]
        tarde = [m for m in marcas if m.get('estado') == 'tarde']
        trozos.append('%d jugadores en la lista' % len(marcas))
        if faltaron:
            trozos.append('%d no vinieron' % len(faltaron))
        if tarde:
            trozos.append('%d llegaron tarde' % len(tarde))
    return ', '.join(trozos) + '.'


def _entero(v):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if 0 < n < 60 * 60 * 4 else None


@bp.route('/api/observacion/<oid>', methods=['DELETE'])
@login_required
def api_observacion_borrar(oid):
    from .api import api_guard

    err = api_guard(solo_coach=True)
    if err:
        return err
    db.delete('fut_observaciones', 'borrar obs', id=oid, coach_id=db.equipo_id(current_user.id), obligatorio=True)
    return jsonify({'ok': True})
