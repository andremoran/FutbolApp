# -*- coding: utf-8 -*-
"""
futbol/salud.py — Ficha médica y control de lesiones.

La frontera de privacidad, que es lo importante aquí
────────────────────────────────────────────────────
La ficha médica del jugador (alergias, medicación, condiciones) la escribe y la
lee ÉL. El entrenador solo ve lo que hace falta para no matarlo en un campo: el
contacto de emergencia y las alergias. No ve medicación ni condiciones.

Las lesiones son lo contrario: las lleva el entrenador porque afectan a las
convocatorias, y el jugador las ve todas.

Es la misma regla que ya rige el check-in de bienestar: si el jugador sospecha
que el entrenador lee todo, deja de escribir la verdad y el módulo no sirve
para nada.
"""
import logging
from datetime import date, datetime, timezone

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles

from . import bp, db

logger = logging.getLogger(__name__)

ZONAS = ['Tobillo', 'Rodilla', 'Isquiotibiales', 'Cuádriceps', 'Aductores',
         'Gemelo', 'Cadera', 'Ingle', 'Espalda baja', 'Hombro', 'Pie',
         'Muñeca', 'Cabeza', 'Otra']

TIPOS_LESION = [('muscular', 'Muscular'), ('articular', 'Articular'),
                ('osea', 'Ósea'), ('ligamentosa', 'Ligamentosa'),
                ('contusion', 'Contusión'), ('otra', 'Otra')]

GRAVEDADES = [('leve', 'Leve', '#f59e0b', '1 a 7 días'),
              ('moderada', 'Moderada', '#f97316', '1 a 4 semanas'),
              ('grave', 'Grave', '#ef4444', 'más de 4 semanas')]
GRAVEDAD_META = {c: {'etiqueta': e, 'color': col, 'plazo': p}
                 for c, e, col, p in GRAVEDADES}

#  'cronico' es el estado que faltaba (INJURY_STATUS de PlayerMedicalScreen):
#  una rodilla que se arrastra desde hace años no está de baja, pero tampoco
#  curada, y meterla en cualquiera de los otros tres falsea la disponibilidad.
ESTADOS = [('activa', 'De baja', '#ef4444'),
           ('recuperando', 'Recuperándose', '#f59e0b'),
           ('alta', 'De alta', '#10b981'),
           ('cronico', 'Crónica', '#b45309')]
ESTADO_META = {c: {'etiqueta': e, 'color': col} for c, e, col in ESTADOS}

#  Quién cuenta como disponible para convocar. Una lesión crónica no aparta al
#  jugador del equipo: juega con ella.
ESTADOS_DE_BAJA = ('activa', 'recuperando')

#  RISK_LEVELS de PlayerMedicalScreen. El valor vive en fut_attributes, no en
#  la ficha médica, porque es parte del Perfil Dinámico.
RIESGOS = [('bajo', 'Bajo', '#10b981'),
           ('medio', 'Medio', '#f59e0b'),
           ('alto', 'Alto', '#ef4444')]
RIESGO_META = {c: {'etiqueta': e, 'color': col} for c, e, col in RIESGOS}


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _guardia():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    return None


def decorar_lesiones(filas):
    hoy = date.today()
    for l in filas or []:
        l['_fecha'] = db.parse_fecha(l.get('fecha'))
        l['_alta_prevista'] = db.parse_fecha(l.get('alta_prevista'))
        l['_alta_real'] = db.parse_fecha(l.get('alta_real'))
        l['_gravedad'] = GRAVEDAD_META.get(l.get('gravedad') or 'leve', GRAVEDADES[0][1])
        l['_estado'] = ESTADO_META.get(l.get('estado') or 'activa',
                                       {'etiqueta': 'De baja', 'color': '#ef4444'})
        fin = l['_alta_real'] or hoy
        l['_dias'] = (fin - l['_fecha']).days if l['_fecha'] else None
        l['_restantes'] = ((l['_alta_prevista'] - hoy).days
                           if l['_alta_prevista'] and not l['_alta_real'] else None)
    return filas or []


def lesiones_activas(coach_id):
    filas = db.rows('fut_injuries', 'lesiones activas', coach_id=coach_id) or []
    return decorar_lesiones([f for f in filas if f.get('estado') in ESTADOS_DE_BAJA])


def _dias_o_nada(v):
    """Los días estimados de recuperación, o nada si no es un número."""
    if v in (None, ''):
        return None
    try:
        return max(0, min(999, int(v)))
    except (TypeError, ValueError):
        return None


def _dueno_de_la_plantilla(coach_id, player_id=None, manual_player_id=None):
    """Comprueba que el jugador (con o sin cuenta) es de este equipo.

    Devuelve el filtro listo para escribir, o None si no lo es.
    """
    if player_id:
        if any(str(j['id']) == str(player_id)
               for j in db.jugadores_del_entrenador(coach_id)):
            return db.dueno_filtro(player_id=player_id)
        return None
    if manual_player_id:
        if db.one('fut_manual_players', 'manual mio',
                  id=manual_player_id, coach_id=coach_id):
            return db.dueno_filtro(manual_player_id=manual_player_id)
    return None


def _dueno_por_id(coach_id, pid):
    """Un id suelto que puede ser de cualquiera de los dos tipos de jugador.

    Lo usan las pantallas cuyo `<pid>` viene de la URL y no dicen si es un
    jugador con cuenta o apuntado a mano.
    """
    return (_dueno_de_la_plantilla(coach_id, player_id=pid)
            or _dueno_de_la_plantilla(coach_id, manual_player_id=pid))


# ═══════════════════════ LADO DEL JUGADOR ═══════════════════════
@bp.route('/medico')
@login_required
def p_medico():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_medico'))

    uid = current_user.id
    ficha = db.one('fut_medical', 'mi ficha', player_id=uid) or {}
    lesiones = decorar_lesiones(
        db.rows('fut_injuries', 'mis lesiones', player_id=uid,
                _order='fecha', _desc=True, _limit=60) or [])

    return render_template('p_medico.html',
                           tab_activa='ficha', hide_tabbar=True,
                           ficha=ficha,
                           lesiones=lesiones,
                           activas=[l for l in lesiones if l.get('estado') != 'alta'],
                           entrenador=db.entrenador_del_jugador(uid),
                           gravedades=GRAVEDADES, estados=ESTADOS)


@bp.route('/api/medico', methods=['POST'])
@login_required
def api_medico():
    """Solo el propio jugador escribe su ficha médica. El entrenador no."""
    error = _guardia()
    if error:
        return error
    if getattr(current_user, 'role', '') == 'especialista':
        return jsonify({'error': 'La ficha médica la escribe el jugador.'}), 403

    d = request.get_json(silent=True) or {}
    datos = {}
    for campo, tope in (('grupo_sanguineo', 10), ('alergias', 600),
                        ('medicacion', 600), ('condiciones', 800),
                        ('contacto_nombre', 120), ('contacto_tel', 30),
                        ('contacto_parentesco', 60), ('seguro', 120)):
        if campo in d:
            datos[campo] = (str(d[campo]) or '')[:tope]

    # `solo_basicos`: el jugador escribe lo suyo, pero el veredicto de aptitud
    # y el cribado médico los firma el cuerpo técnico, no el interesado.
    if not db.guardar_ficha_medica(player_id=current_user.id,
                                   actualizado_por=current_user.id,
                                   solo_basicos=True, **datos):
        return jsonify({'error': 'No se pudo guardar la ficha.'}), 500
    return jsonify({'ok': True, 'mensaje': 'Ficha médica guardada.'})


# ═══════════════════════ LADO DEL ENTRENADOR ═══════════════════════
@bp.route('/coach/medico')
@login_required
@roles.solo_pro('medico')
def c_medico():
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.p_medico'))

    uid = db.equipo_id(current_user.id)

    # La plantilla entera: el que no tiene cuenta se lesiona igual.
    jugadores = [dict(j, _tipo='registrado') for j in db.jugadores_del_entrenador(uid)]
    for m in (db.rows('fut_manual_players', 'manuales medico',
                      coach_id=uid, activo=True) or []):
        jugadores.append({'id': m['id'], 'name': m.get('nombre'),
                          'profile_photo': None, '_tipo': 'manual'})

    lesiones = decorar_lesiones(
        db.rows('fut_injuries', 'lesiones equipo', coach_id=uid,
                _order='fecha', _desc=True, _limit=200) or [])

    por_jugador = {}
    for l in lesiones:
        clave = str(l.get('player_id') or l.get('manual_player_id'))
        por_jugador.setdefault(clave, []).append(l)

    fichas = _fichas_del_equipo(jugadores)

    for j in jugadores:
        suyas = por_jugador.get(str(j['id']), [])
        j['_lesiones'] = suyas
        # Crónica no es baja: el jugador convive con ella y se le convoca.
        j['_baja'] = next((l for l in suyas if l.get('estado') in ESTADOS_DE_BAJA), None)
        j['_cronica'] = next((l for l in suyas if l.get('estado') == 'cronico'), None)
        j['_medico'] = fichas.get(str(j['id']), {})
        j['_aptitud'] = db.APTITUD_META.get((j['_medico'] or {}).get('apto'))

    de_baja = [l for l in lesiones if l.get('estado') in ESTADOS_DE_BAJA]
    return render_template('c_medico.html',
                           tab_activa='equipo', hide_tabbar=True,
                           jugadores=jugadores,
                           lesiones=lesiones[:40], activas=de_baja,
                           n_disponibles=len([j for j in jugadores if not j['_baja']]),
                           zonas=ZONAS, tipos=TIPOS_LESION,
                           gravedades=GRAVEDADES, estados=ESTADOS,
                           hoy=date.today().isoformat())


def _fichas_del_equipo(jugadores):
    """Las fichas médicas de toda la plantilla, en dos consultas.

    El entrenador ve la ficha completa —así es la app— pero eso no le hace
    autor de lo que declaró el jugador: quién puede escribir cada parte lo
    decide db.guardar_ficha_medica, no esta consulta.
    """
    con_cuenta = [j['id'] for j in jugadores if j['_tipo'] == 'registrado']
    sin_cuenta = [j['id'] for j in jugadores if j['_tipo'] == 'manual']

    fichas = {}
    if con_cuenta:
        for f in db.q(lambda: db.sb().table('fut_medical').select('*')
                      .in_('player_id', con_cuenta).execute().data or [],
                      [], 'fichas con cuenta'):
            fichas[str(f['player_id'])] = f
    if sin_cuenta:
        for f in db.q(lambda: db.sb().table('fut_medical').select('*')
                      .in_('manual_player_id', sin_cuenta).execute().data or [],
                      [], 'fichas sin cuenta'):
            fichas[str(f['manual_player_id'])] = f
    return fichas


@bp.route('/coach/medico/<pid>')
@login_required
@roles.solo_pro('medico')
def c_medico_jugador(pid):
    """La ficha médica de UN jugador — screens/PlayerMedicalScreen.tsx.

    Es la pantalla que llevaba el cuerpo técnico en la app y que aquí no
    existía: la web solo tenía el listado del equipo.
    """
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.p_medico'))

    uid = db.equipo_id(current_user.id)
    jugador = next((j for j in db.jugadores_del_entrenador(uid)
                    if str(j['id']) == str(pid)), None)
    manual = None
    if not jugador:
        manual = db.one('fut_manual_players', 'manual medico', id=pid, coach_id=uid)
        if not manual:
            abort(404)

    dueno = db.dueno_filtro(player_id=None if manual else pid,
                            manual_player_id=pid if manual else None)
    ficha = db.ficha_medica(**dueno)
    atributos = db.ficha_atributos(**dueno)
    lesiones = decorar_lesiones(
        db.rows('fut_injuries', 'lesiones jugador', coach_id=uid,
                _order='fecha', _desc=True, **dueno) or [])

    return render_template(
        'c_medico_jugador.html',
        tab_activa='equipo', hide_tabbar=True,
        jugador=jugador or {'id': pid, 'name': manual['nombre']},
        es_manual=bool(manual),
        ficha=ficha,
        # La parte declarativa de un jugador CON cuenta la escribe él: el
        # cuerpo técnico la lee, pero no la pisa (decisión del usuario).
        declaracion_editable=bool(manual),
        atributos=atributos,
        lesiones=lesiones,
        de_baja=[l for l in lesiones if l.get('estado') in ESTADOS_DE_BAJA],
        aptitudes=db.APTITUDES,
        aptitud=db.APTITUD_META.get(ficha.get('apto')),
        zonas=ZONAS, tipos=TIPOS_LESION,
        gravedades=GRAVEDADES, estados=ESTADOS,
        riesgos=RIESGOS,
        niveles_fatiga=db.NIVELES_FATIGA,
        fatiga_nivel=db.nivel_de_fatiga(atributos.get('fatiga')),
        hoy=date.today().isoformat())


@bp.route('/api/medico/<pid>', methods=['POST'])
@login_required
def api_medico_coach(pid):
    """El cuerpo técnico guarda la parte clínica de la ficha de un jugador."""
    error = _guardia()
    if error:
        return error
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Esta ficha la lleva el cuerpo técnico.'}), 403

    uid = db.equipo_id(current_user.id)
    dueno = _dueno_por_id(uid, pid)
    if not dueno:
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403
    es_manual = 'manual_player_id' in dueno

    from .equipo import _limpiar_ficha_medica
    d = request.get_json(silent=True) or {}
    campos = _limpiar_ficha_medica(d)
    if 'apto_competir' in d:
        campos['apto_competir'] = bool(d['apto_competir'])

    # Fatiga y riesgo viven en el Perfil Dinámico, no en la ficha médica: son
    # los mismos que mueve la evaluación semanal (ver sql/schema_v5).
    estado = {}
    if d.get('fatiga') in db.FATIGA_A_NUMERO:
        estado['fatiga'] = db.FATIGA_A_NUMERO[d['fatiga']]
    if d.get('riesgo_sobrecarga') in dict((c, e) for c, e, _ in RIESGOS):
        estado['riesgo_sobrecarga'] = d['riesgo_sobrecarga']
    if estado:
        db.guardar_atributos(**dueno, **estado)

    if campos:
        db.guardar_ficha_medica(
            **dueno, actualizado_por=current_user.id,
            # A un jugador sin cuenta le escribe todo el entrenador; a uno con
            # cuenta, solo lo clínico.
            solo_clinicos=not es_manual,
            autor=db.AUTOR_CUERPO_TECNICO if es_manual else None,
            **campos)

    return jsonify({'ok': True, 'mensaje': 'Ficha médica guardada.'})


@bp.route('/api/lesion', methods=['POST'])
@login_required
def api_lesion():
    """Crea o actualiza una lesión. La lleva el entrenador."""
    error = _guardia()
    if error:
        return error
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'El parte de lesiones lo lleva el entrenador.'}), 403

    uid = db.equipo_id(current_user.id)
    d = request.get_json(silent=True) or {}
    lid = d.get('id')

    # Al actualizar, el jugador es el que ya tenía el parte: pedirlo otra vez
    # solo daría ocasión de equivocarse (y de mover una lesión a otra persona).
    if lid:
        previa = db.one('fut_injuries', 'lesion mia', id=lid, coach_id=uid)
        if not previa:
            return jsonify({'error': 'Ese parte no es tuyo.'}), 403
        dueno = db.dueno_filtro(previa.get('player_id'), previa.get('manual_player_id'))
    else:
        # Se lesionan igual los que no tienen cuenta, y hasta ahora no se les
        # podía abrir parte: el jugador manual solo existía en la plantilla.
        dueno = _dueno_de_la_plantilla(uid, d.get('player_id'), d.get('manual_player_id'))
        if not dueno:
            return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    # Al actualizar solo se tocan los campos que vengan: dar el alta manda
    # {id, estado} y no puede borrar la zona ni la fecha de la lesión.
    datos = {**dueno, 'coach_id': uid}
    campos = {
        'zona': lambda v: str(v)[:60],
        'lado': lambda v: str(v)[:20],
        'tipo': lambda v: v if v in dict(TIPOS_LESION) else 'otra',
        'gravedad': lambda v: v if v in GRAVEDAD_META else 'leve',
        'estado': lambda v: v if v in ESTADO_META else 'activa',
        'fecha': lambda v: v or db.hoy_iso(),
        'alta_prevista': lambda v: v or None,
        'alta_real': lambda v: v or None,
        'descripcion': lambda v: str(v)[:1000],
        'tratamiento': lambda v: str(v)[:1000],
        'dias_estimados': _dias_o_nada,
    }
    for campo, limpiar in campos.items():
        if campo in d:
            datos[campo] = limpiar(d[campo])

    if not lid:
        datos.setdefault('estado', 'activa')
        datos.setdefault('fecha', db.hoy_iso())
        if not datos.get('zona'):
            return jsonify({'error': 'Indica la zona de la lesión.'}), 400

    # Dar el alta sin fecha deja el parte a medias y descuadra los días de baja.
    if datos.get('estado') == 'alta' and not datos.get('alta_real'):
        datos['alta_real'] = db.hoy_iso()

    if lid:
        db.update('fut_injuries', datos, 'lesion up', id=lid, coach_id=uid)
        return jsonify({'ok': True, 'id': lid, 'mensaje': 'Parte actualizado.'})

    datos['registrado_por'] = current_user.id
    datos['creado'] = _ahora()
    fila = db.insert('fut_injuries', datos, 'lesion nueva')
    if not fila:
        return jsonify({'error': 'No se pudo guardar el parte.'}), 500
    return jsonify({'ok': True, 'id': fila['id'], 'mensaje': 'Lesión registrada.'})


@bp.route('/api/lesion/<lid>', methods=['DELETE'])
@login_required
def api_lesion_borrar(lid):
    error = _guardia()
    if error:
        return error
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el entrenador borra partes.'}), 403
    db.delete('fut_injuries', 'borrar lesion', id=lid, coach_id=db.equipo_id(current_user.id))
    return jsonify({'ok': True, 'mensaje': 'Parte borrado.'})
