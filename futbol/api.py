# -*- coding: utf-8 -*-
"""
futbol/api.py — Endpoints JSON de FutbolApp.

Los consume profoot.js con PF.api(). Todos exigen sesión iniciada y token CSRF,
con el mismo patrón "synchronizer token" de main2.py (_csrf_ok): el token viaja
en la cabecera X-CSRFToken y se compara con el de la sesión.
"""
import logging
from datetime import date, datetime, timezone

from flask import jsonify, request, url_for
from flask_login import login_required, current_user

from . import bp, db
from .ia import responder_ia

logger = logging.getLogger(__name__)


# ─── Guardias ────────────────────────────────────────────────────────────────
def csrf_ok():
    from app import csrf_ok as _ok
    return _ok()


def api(f):
    """Sesión + CSRF + errores en JSON. Nunca deja escapar un traceback al cliente."""
    from functools import wraps

    @wraps(f)
    @login_required
    def wrapper(*a, **kw):
        if request.method != 'GET' and not csrf_ok():
            return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
        try:
            return f(*a, **kw)
        except Exception as e:
            logger.error('api %s: %s', request.path, e, exc_info=True)
            return jsonify({'error': 'No se pudo completar la acción. Inténtalo de nuevo.'}), 500
    return wrapper


def body():
    return request.get_json(silent=True) or {}


# Alias usados por los módulos mental.py y social.py
cuerpo = body


def api_guard(solo_coach=False):
    """Comprueba CSRF y rol. Devuelve la respuesta de error, o None si todo bien."""
    if request.method != 'GET' and not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if solo_coach and getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el entrenador puede hacer esto.'}), 403
    return None


def es_coach():
    return getattr(current_user, 'role', '') == 'especialista'


def de_mi_plantilla(pid):
    """Un entrenador solo puede escribir sobre jugadores de su propia plantilla."""
    return any(str(j['id']) == str(pid) for j in db.jugadores_del_entrenador(current_user.id))


def ahora():
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════ HÁBITOS ═══════════════════════
@bp.route('/api/habito', methods=['POST'])
@api
def api_habito_crear():
    d = body()
    nombre = (d.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'Ponle un nombre al hábito.'}), 400
    fila = db.insert('fut_habits', {
        'player_id': current_user.id,
        'nombre': nombre[:80],
        'icono': (d.get('icono') or 'check')[:32],
        'activo': True,
        'creado': ahora(),
    })
    if not fila:
        return jsonify({'error': 'No se pudo crear. ¿Ya corriste sql/futbol_schema.sql?'}), 500
    return jsonify({'ok': True, 'habito': fila})


@bp.route('/api/habito/<hid>/toggle', methods=['POST'])
@api
def api_habito_toggle(hid):
    uid = current_user.id
    hoy = db.hoy_iso()
    existente = db.one('fut_habit_completions', 'toggle',
                       habit_id=hid, player_id=uid, fecha=hoy)
    if existente:
        nuevo = not existente.get('hecho')
        db.update('fut_habit_completions', {'hecho': nuevo}, 'toggle up', id=existente['id'])
    else:
        nuevo = True
        db.insert('fut_habit_completions', {
            'habit_id': hid, 'player_id': uid, 'fecha': hoy, 'hecho': True,
        })
    return jsonify({'ok': True, 'hecho': nuevo, 'racha': db.racha_actual(uid)})


@bp.route('/api/habito/<hid>', methods=['DELETE'])
@api
def api_habito_borrar(hid):
    db.update('fut_habits', {'activo': False}, 'borrar habito',
              id=hid, player_id=current_user.id)
    return jsonify({'ok': True})


# ═══════════════════════ METAS ═══════════════════════
@bp.route('/api/meta', methods=['POST'])
@api
def api_meta_crear():
    d = body()
    titulo = (d.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'error': 'Ponle un título a la meta.'}), 400

    # El entrenador puede asignar metas a sus jugadores; el jugador solo a sí mismo.
    destino = d.get('player_id') if es_coach() else current_user.id
    if es_coach():
        if not destino or not de_mi_plantilla(destino):
            return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    fila = db.insert('fut_goals', {
        'player_id': destino,
        'titulo': titulo[:120],
        'descripcion': (d.get('descripcion') or '')[:600],
        'categoria': (d.get('categoria') or 'general')[:40],
        'objetivo_num': d.get('objetivo_num'),
        'progreso': 0,
        'fecha_limite': d.get('fecha_limite') or None,
        'estado': 'activa',
        'creado_por': current_user.id,
        'creado': ahora(),
    })
    if not fila:
        return jsonify({'error': 'No se pudo crear la meta.'}), 500
    return jsonify({'ok': True, 'meta': fila})


@bp.route('/api/meta/<mid>', methods=['POST'])
@api
def api_meta_actualizar(mid):
    d = body()
    cambios = {}
    if 'progreso' in d:
        cambios['progreso'] = max(0, min(100, int(d.get('progreso') or 0)))
        if cambios['progreso'] >= 100:
            cambios['estado'] = 'completada'
    if 'estado' in d:
        cambios['estado'] = str(d['estado'])[:20]
    if not cambios:
        return jsonify({'error': 'Nada que actualizar.'}), 400

    filtro = {'id': mid}
    if not es_coach():
        filtro['player_id'] = current_user.id
    db.update('fut_goals', cambios, 'meta up', **filtro)
    return jsonify({'ok': True, **cambios})


@bp.route('/api/meta/<mid>', methods=['DELETE'])
@api
def api_meta_borrar(mid):
    filtro = {'id': mid}
    if not es_coach():
        filtro['player_id'] = current_user.id
    db.delete('fut_goals', 'meta del', **filtro)
    return jsonify({'ok': True})


# ═══════════════════════ ENTRENOS ═══════════════════════
@bp.route('/api/entreno', methods=['POST'])
@api
def api_entreno_crear():
    d = body()
    fila = db.insert('fut_trainings', {
        'player_id': current_user.id,
        'fecha': d.get('fecha') or db.hoy_iso(),
        'tipo': (d.get('tipo') or 'general')[:40],
        'duracion_min': int(d.get('duracion_min') or 0),
        'intensidad': (d.get('intensidad') or 'media')[:20],
        'rpe': int(d.get('rpe')) if d.get('rpe') else None,
        'notas': (d.get('notas') or '')[:800],
        'creado': ahora(),
    })
    if not fila:
        return jsonify({'error': 'No se pudo guardar el entrenamiento.'}), 500
    return jsonify({'ok': True, 'entreno': fila})


@bp.route('/api/entreno/<eid>', methods=['DELETE'])
@api
def api_entreno_borrar(eid):
    db.delete('fut_trainings', 'entreno del', id=eid, player_id=current_user.id)
    return jsonify({'ok': True})


# ═══════════════════════ AGENDA Y ASISTENCIA ═══════════════════════
@bp.route('/api/evento', methods=['POST'])
@api
def api_evento_crear():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador agenda eventos.'}), 403
    d = body()
    titulo = (d.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'error': 'Ponle un título al evento.'}), 400
    fila = db.insert('fut_events', {
        'coach_id': current_user.id,
        'tipo': (d.get('tipo') or 'entreno')[:20],
        'titulo': titulo[:120],
        'fecha': d.get('fecha') or db.hoy_iso(),
        'hora': d.get('hora') or None,
        'lugar': (d.get('lugar') or '')[:120],
        'descripcion': (d.get('descripcion') or '')[:800],
        'creado': ahora(),
    })
    if not fila:
        return jsonify({'error': 'No se pudo crear el evento.'}), 500
    return jsonify({'ok': True, 'evento': fila})


@bp.route('/api/evento/<eid>', methods=['DELETE'])
@api
def api_evento_borrar(eid):
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador borra eventos.'}), 403
    db.delete('fut_events', 'evento del', id=eid, coach_id=current_user.id)
    return jsonify({'ok': True})


@bp.route('/api/asistencia', methods=['POST'])
@api
def api_asistencia():
    """Marca la asistencia de UNA persona a UN evento.

    Los nombres viejos ('asiste'/'falta'/'duda') se siguen aceptando y se
    traducen: hay clientes ya instalados como PWA que los mandan.
    """
    from .calendario import ESTADOS_ASISTENCIA

    d = body()
    eid = d.get('event_id')
    estado = (d.get('estado') or '').strip()
    estado = {'asiste': 'presente', 'falta': 'ausente',
              'duda': 'pendiente'}.get(estado, estado)

    validos = {c for c, _, _, _ in ESTADOS_ASISTENCIA}
    if not eid or estado not in validos:
        return jsonify({'error': 'Datos incompletos.'}), 400

    # El entrenador puede pasar lista por un jugador suyo; el jugador solo por sí mismo.
    pid = d.get('player_id') if es_coach() else current_user.id
    if es_coach():
        if not pid or not de_mi_plantilla(pid):
            return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    existente = db.one('fut_attendance', 'asist', event_id=eid, player_id=pid)
    if existente:
        db.update('fut_attendance',
                  {'estado': estado, 'motivo': (d.get('motivo') or '')[:200],
                   'actualizado': ahora()},
                  'asist up', id=existente['id'])
    else:
        db.insert('fut_attendance', {
            'event_id': eid, 'player_id': pid, 'estado': estado,
            'motivo': (d.get('motivo') or '')[:200],
            'registrado_por': current_user.id,
            'creado': ahora(), 'actualizado': ahora(),
        })
    return jsonify({'ok': True, 'estado': estado})


# ═══════════════════════ EQUIPO Y PERFIL ═══════════════════════
@bp.route('/api/equipo', methods=['POST'])
@api
def api_equipo_guardar():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador edita el equipo.'}), 403
    d = body()
    datos = {
        'coach_id': current_user.id,
        'nombre': (d.get('nombre') or 'Mi equipo')[:80],
        'categoria': (d.get('categoria') or '')[:60],
        'codigo': db.codigo_equipo(current_user.id),
    }
    existente = db.one('fut_teams', 'equipo', coach_id=current_user.id)
    if existente:
        db.update('fut_teams', datos, 'equipo up', id=existente['id'])
    else:
        datos['creado'] = ahora()
        if not db.insert('fut_teams', datos):
            return jsonify({'error': 'No se pudo guardar el equipo.'}), 500
    return jsonify({'ok': True, 'equipo': datos})


@bp.route('/api/perfil_jugador', methods=['POST'])
@api
def api_perfil_jugador():
    d = body()
    pid = d.get('player_id') if es_coach() else current_user.id
    if es_coach():
        if not pid or not de_mi_plantilla(pid):
            return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    datos = {'user_id': pid}
    for campo, tope in (('posicion', 40), ('pie_habil', 20), ('notas', 400)):
        if campo in d:
            datos[campo] = (d.get(campo) or '')[:tope]
    if 'dorsal' in d:
        try:
            datos['dorsal'] = int(d['dorsal']) if d['dorsal'] not in ('', None) else None
        except (TypeError, ValueError):
            datos['dorsal'] = None

    if not db.upsert('fut_player_profile', datos, 'perfil jug', on_conflict='user_id'):
        return jsonify({'error': 'No se pudo guardar la ficha.'}), 500
    return jsonify({'ok': True})


# ═══════════════════════ EVALUACIONES Y ATRIBUTOS ═══════════════════════
@bp.route('/api/evaluacion', methods=['POST'])
@api
def api_evaluacion():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador evalúa.'}), 403
    d = body()
    pid = d.get('player_id')
    if not pid or not de_mi_plantilla(pid):
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    puntuaciones = {}
    for k in db.ATRIBUTOS:
        if k in d:
            try:
                puntuaciones[k] = max(0, min(100, int(d[k])))
            except (TypeError, ValueError):
                pass

    db.insert('fut_evaluations', {
        'player_id': pid,
        'coach_id': current_user.id,
        'fecha': d.get('fecha') or db.hoy_iso(),
        'notas': (d.get('notas') or '')[:2000],
        'puntuaciones': puntuaciones,
        'creado': ahora(),
    })

    if puntuaciones:
        puntuaciones['player_id'] = pid
        puntuaciones['actualizado'] = ahora()
        db.upsert('fut_attributes', puntuaciones, 'atributos', on_conflict='player_id')

    return jsonify({'ok': True, 'redirect': url_for('futbol.c_jugador', pid=pid)})


# ═══════════════════════ PARTIDOS ═══════════════════════
@bp.route('/api/partido', methods=['POST'])
@api
def api_partido():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador registra partidos.'}), 403
    d = body()
    fila = db.insert('fut_matches', {
        'coach_id': current_user.id,
        'rival': (d.get('rival') or 'Rival')[:80],
        'fecha': d.get('fecha') or db.hoy_iso(),
        'local': bool(d.get('local', True)),
        'goles_favor': int(d.get('goles_favor') or 0),
        'goles_contra': int(d.get('goles_contra') or 0),
        'competicion': (d.get('competicion') or '')[:80],
        'creado': ahora(),
    })
    if not fila:
        return jsonify({'error': 'No se pudo guardar el partido.'}), 500
    return jsonify({'ok': True, 'partido': fila})


@bp.route('/api/partido/<mid>/stats', methods=['POST'])
@api
def api_partido_stats(mid):
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador registra estadísticas.'}), 403
    d = body()
    pid = d.get('player_id')
    if not pid or not de_mi_plantilla(pid):
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    datos = {'match_id': mid, 'player_id': pid}
    for campo in ('minutos', 'goles', 'asistencias', 'tarjetas_a', 'tarjetas_r', 'valoracion'):
        if campo in d:
            try:
                datos[campo] = int(d[campo] or 0)
            except (TypeError, ValueError):
                datos[campo] = 0

    existente = db.one('fut_match_stats', 'stats', match_id=mid, player_id=pid)
    if existente:
        db.update('fut_match_stats', datos, 'stats up', id=existente['id'])
    else:
        db.insert('fut_match_stats', datos)
    return jsonify({'ok': True})


# ═══════════════════════ TESTS ═══════════════════════
@bp.route('/api/test', methods=['POST'])
@api
def api_test_crear():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador crea pruebas.'}), 403
    d = body()
    nombre = (d.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'Ponle un nombre a la prueba.'}), 400
    fila = db.insert('fut_tests', {
        'coach_id': current_user.id,
        'nombre': nombre[:80],
        'tipo': (d.get('tipo') or 'distancia')[:30],
        'unidad': (d.get('unidad') or '')[:20],
        'fecha': d.get('fecha') or db.hoy_iso(),
        'creado': ahora(),
    })
    if not fila:
        return jsonify({'error': 'No se pudo crear la prueba.'}), 500
    return jsonify({'ok': True, 'test': fila,
                    'redirect': url_for('futbol.c_test_detalle', tid=fila['id'])})


@bp.route('/api/test/<tid>/resultado', methods=['POST'])
@api
def api_test_resultado(tid):
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador registra resultados.'}), 403
    d = body()
    pid = d.get('player_id')
    if not pid or not de_mi_plantilla(pid):
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403
    try:
        valor = float(d.get('valor'))
    except (TypeError, ValueError):
        return jsonify({'error': 'El valor debe ser un número.'}), 400

    existente = db.one('fut_test_results', 'res', test_id=tid, player_id=pid)
    if existente:
        db.update('fut_test_results', {'valor': valor}, 'res up', id=existente['id'])
    else:
        db.insert('fut_test_results', {
            'test_id': tid, 'player_id': pid, 'valor': valor, 'creado': ahora(),
        })
    return jsonify({'ok': True})


# ═══════════════════════ TÁCTICA ═══════════════════════
@bp.route('/api/jugada', methods=['POST'])
@api
def api_jugada_guardar():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador guarda jugadas.'}), 403
    d = body()
    nombre = (d.get('nombre') or '').strip() or 'Jugada sin nombre'
    datos = {
        'coach_id': current_user.id,
        'nombre': nombre[:80],
        'formacion': (d.get('formacion') or '')[:20],
        'datos': d.get('datos') or {},
    }
    jid = d.get('id')
    if jid:
        db.update('fut_tactical_plays', datos, 'jugada up', id=jid, coach_id=current_user.id)
        return jsonify({'ok': True, 'id': jid})

    datos['creado'] = ahora()
    fila = db.insert('fut_tactical_plays', datos)
    if not fila:
        return jsonify({'error': 'No se pudo guardar la jugada.'}), 500
    return jsonify({'ok': True, 'id': fila['id']})


@bp.route('/api/jugada/<jid>', methods=['DELETE'])
@api
def api_jugada_borrar(jid):
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador borra jugadas.'}), 403
    db.delete('fut_tactical_plays', 'jugada del', id=jid, coach_id=current_user.id)
    return jsonify({'ok': True})


# ═══════════════════════ CHECK-IN DE BIENESTAR ═══════════════════════
@bp.route('/api/checkin', methods=['POST'])
@api
def api_checkin():
    d = body()
    respuestas = d.get('respuestas') or {}
    if not respuestas:
        return jsonify({'error': 'Responde al menos una pregunta.'}), 400

    valores = []
    for v in respuestas.values():
        try:
            valores.append(max(1, min(5, int(v))))
        except (TypeError, ValueError):
            pass
    if not valores:
        return jsonify({'error': 'Respuestas no válidas.'}), 400

    puntaje = round(sum(valores) / len(valores) / 5 * 100)
    semaforo = 'verde' if puntaje >= 70 else ('ambar' if puntaje >= 45 else 'rojo')

    # Si el entrenador se lo había asignado, queda cerrada.
    from .mental import cerrar_asignacion
    cerrar_asignacion(current_user.id)

    fila = db.insert('fut_checkins', {
        'player_id': current_user.id,
        'fecha': db.hoy_iso(),
        'respuestas': respuestas,
        'puntaje': puntaje,
        'semaforo': semaforo,
        'creado': ahora(),
    })
    if not fila:
        return jsonify({'error': 'No se pudo guardar el check-in.'}), 500
    return jsonify({'ok': True, 'puntaje': puntaje, 'semaforo': semaforo,
                    'redirect': url_for('futbol.checkin_resultado', cid=fila['id'])})


# ═══════════════════════ IA ═══════════════════════
@bp.route('/api/ia', methods=['POST'])
@api
def api_ia():
    import roles

    pregunta = (body().get('mensaje') or '').strip()
    if not pregunta:
        return jsonify({'error': 'Escribe una pregunta.'}), 400
    if len(pregunta) > 1200:
        pregunta = pregunta[:1200]

    # El plan gratuito tiene cupo diario, no candado: se comprueba aquí y no
    # al abrir la pantalla, para que pueda leer lo que ya preguntó.
    restantes = roles.ia_restantes(current_user)
    if restantes is not None and restantes <= 0:
        return jsonify({
            'error': f'Gastaste tus {roles.IA_MENSAJES_GRATIS} mensajes de hoy. '
                     'Vuelven mañana, o pásate a Pro y pregunta sin límite.',
            'pro': True, 'agotado': True,
            'url': url_for('futbol.planes')}), 402

    respuesta = responder_ia(current_user, pregunta)

    db.insert('fut_ia_chat', {
        'user_id': current_user.id,
        'rol': getattr(current_user, 'role', 'paciente'),
        'pregunta': pregunta,
        'respuesta': respuesta,
        'creado': ahora(),
    })
    return jsonify({'ok': True, 'respuesta': respuesta,
                    'restantes': (restantes - 1) if restantes is not None else None})
