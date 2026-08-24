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
    """¿Ese jugador es del equipo en el que estoy?

    Se comprueba contra el EQUIPO y no contra mi id: un asistente técnico
    trabaja sobre la plantilla del entrenador principal, y con `current_user.id`
    no vería a nadie.
    """
    equipo = db.equipo_id(current_user.id)
    return any(str(j['id']) == str(pid) for j in db.jugadores_del_entrenador(equipo))


def quien_es_del_equipo(pid):
    """Dice si es del equipo Y en que columna se guarda lo suyo.

    Devuelve 'player_id', 'manual_player_id', o None si no es de la plantilla.
    Hace falta porque de un jugador sin cuenta lo suyo no cuelga de player_id,
    y quien llama no tiene por que andar averiguando de que tipo es cada uno.
    """
    if not pid:
        return None
    for j in db.plantilla_completa(db.equipo_id(current_user.id)):
        if str(j['id']) == str(pid):
            return 'manual_player_id' if j['es_manual'] else 'player_id'
    return None


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
        db.update('fut_habit_completions', {'hecho': nuevo}, 'toggle up', id=existente['id'], obligatorio=True)
    else:
        nuevo = True
        db.insert('fut_habit_completions', {
            'habit_id': hid, 'player_id': uid, 'fecha': hoy, 'hecho': True,
        }, obligatorio=True)
    return jsonify({'ok': True, 'hecho': nuevo, 'racha': db.racha_actual(uid)})


@bp.route('/api/habito/<hid>', methods=['DELETE'])
@api
def api_habito_borrar(hid):
    if not db.update('fut_habits', {'activo': False}, 'borrar habito',
                     id=hid, player_id=current_user.id):
        return jsonify({'error': 'Ese hábito no es tuyo o ya no existe.'}), 404
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
    if not db.update('fut_goals', cambios, 'meta up', **filtro):
        return jsonify({'error': 'Esa meta no es tuya o ya no existe.'}), 404
    return jsonify({'ok': True, **cambios})


@bp.route('/api/meta/<mid>', methods=['DELETE'])
@api
def api_meta_borrar(mid):
    filtro = {'id': mid}
    if not es_coach():
        filtro['player_id'] = current_user.id
    db.delete('fut_goals', 'meta del', **filtro, obligatorio=True)
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
    db.delete('fut_trainings', 'entreno del', id=eid, player_id=current_user.id, obligatorio=True)
    return jsonify({'ok': True})


# ═══════════════════════ AGENDA Y ASISTENCIA ═══════════════════════
#  El alta rapida de eventos vivia aqui y se ha retirado: la creaba solo el
#  formulario de la pestaña Lista, que ya no existe porque el calendario tiene
#  el alta completa (tipo de entreno, intensidad, duracion, rival, volcar un
#  plan). Ademas estaba peor hecha que la del calendario: guardaba el evento
#  bajo `current_user.id` en vez del equipo —los de un asistente tecnico se
#  perdian— y no pasaba por el tope de eventos del plan gratuito.
#  El alta buena es POST /api/calendario/evento, en calendario.py.

@bp.route('/api/evento/<eid>', methods=['DELETE'])
@api
def api_evento_borrar(eid):
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador borra eventos.'}), 403
    db.delete('fut_events', 'evento del', id=eid, coach_id=db.equipo_id(current_user.id), obligatorio=True)
    return jsonify({'ok': True})


@bp.route('/api/asistencia', methods=['POST'])
@api
def api_asistencia():
    """Dos cosas distintas que antes se escribian en la misma casilla.

    · Si quien llama es el ENTRENADOR, marca la asistencia de verdad
      (`estado`): quien vino, quien llego tarde y quien falto. Eso es lo que
      cuenta en las estadisticas.

    · Si es el JUGADOR, deja un AVISO (`aviso`): dice si piensa ir, si va a
      llegar tarde o si no puede, y por que. NO toca `estado`.

    Antes el boton «Voy» del jugador escribia `estado = presente`, o sea que
    se apuntaba a si mismo como asistente antes de que empezara el
    entrenamiento — y eso subia su porcentaje de asistencia aunque luego no
    apareciera. La asistencia la pone el entrenador DESPUES de ver quien vino;
    lo del jugador es un aviso para que se pueda contar con el.

    Los nombres viejos ('asiste'/'falta'/'duda') se siguen aceptando y se
    traducen: hay clientes ya instalados como PWA que los mandan.
    """
    from .calendario import ESTADOS_ASISTENCIA

    d = body()
    eid = d.get('event_id')
    if not eid:
        return jsonify({'error': 'Datos incompletos.'}), 400

    # ─── El jugador: un aviso, no una asistencia ────────────────────────────
    if not es_coach():
        crudo = (d.get('aviso') or d.get('estado') or '').strip()
        #  Se traduce lo que mandan los botones (y los clientes viejos) a los
        #  tres avisos que existen.
        aviso = {'presente': 'ire', 'asiste': 'ire', 'ire': 'ire',
                 'tarde': 'tarde',
                 'ausente': 'no_ire', 'falta': 'no_ire', 'no_ire': 'no_ire',
                 'justificado': 'no_ire', 'duda': 'tarde'}.get(crudo)
        if not aviso:
            return jsonify({'error': 'Datos incompletos.'}), 400

        motivo = (d.get('motivo') or d.get('aviso_motivo') or '').strip()[:300]
        #  Si no va a venir o llega tarde, el motivo es lo util del aviso: sin
        #  el, el entrenador tiene que preguntar igual.
        if aviso in ('tarde', 'no_ire') and not motivo:
            return jsonify({'error': 'Cuéntale a tu entrenador el motivo.'}), 400

        datos = {'aviso': aviso, 'aviso_motivo': motivo or None,
                 'aviso_en': ahora(), 'actualizado': ahora()}
        existente = db.one('fut_attendance', 'aviso', event_id=eid, player_id=current_user.id)
        if existente:
            db.update('fut_attendance', datos, 'aviso up',
                      id=existente['id'], obligatorio=True)
        else:
            #  `estado` a None a proposito: la columna tenia DEFAULT 'duda'
            #  y una fila creada solo con el aviso nacia con una asistencia
            #  que nadie habia marcado. El defecto ya se quito (v11b), y esto
            #  lo deja escrito por si alguien lo vuelve a poner.
            datos.update({'event_id': eid, 'player_id': current_user.id,
                          'estado': None,
                          'registrado_por': current_user.id, 'creado': ahora()})
            db.insert('fut_attendance', datos, 'aviso nuevo', obligatorio=True)
        return jsonify({'ok': True, 'aviso': aviso})

    # ─── El entrenador: la asistencia de verdad ─────────────────────────────
    estado = (d.get('estado') or '').strip()
    estado = {'asiste': 'presente', 'falta': 'ausente',
              'duda': 'pendiente'}.get(estado, estado)
    validos = {c for c, _, _, _ in ESTADOS_ASISTENCIA}
    if estado not in validos:
        return jsonify({'error': 'Datos incompletos.'}), 400

    pid = d.get('player_id')
    if not pid or not de_mi_plantilla(pid):
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    existente = db.one('fut_attendance', 'asist', event_id=eid, player_id=pid)
    if existente:
        db.update('fut_attendance',
                  {'estado': estado, 'motivo': (d.get('motivo') or '')[:200],
                   'actualizado': ahora()},
                  'asist up', id=existente['id'], obligatorio=True)
    else:
        db.insert('fut_attendance', {
            'event_id': eid, 'player_id': pid, 'estado': estado,
            'motivo': (d.get('motivo') or '')[:200],
            'registrado_por': current_user.id,
            'creado': ahora(), 'actualizado': ahora(),
        }, obligatorio=True)
    return jsonify({'ok': True, 'estado': estado})


# ═══════════════════════ EQUIPO Y PERFIL ═══════════════════════
@bp.route('/api/equipo', methods=['POST'])
@api
def api_equipo_guardar():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador edita el equipo.'}), 403
    d = body()
    uid = db.equipo_id(current_user.id)
    datos = {
        'nombre': (d.get('nombre') or 'Mi equipo')[:80],
        'codigo': db.codigo_equipo(uid),
    }
    # `categoria` es texto libre y ya no se edita desde la pantalla (la
    # categoría de verdad es `categoria_edad`, que se elige en «Nivel del
    # equipo»). Solo se toca si llega: si no, se conserva lo que hubiera.
    if 'categoria' in d:
        datos['categoria'] = (d.get('categoria') or '')[:60]

    existente = db.one('fut_teams', 'equipo', coach_id=uid)
    if existente:
        # El `coach_id` NO se toca al actualizar. Antes se reescribía con
        # `current_user.id`, así que un ASISTENTE que cambiara el nombre del
        # equipo se lo quedaba: el equipo pasaba a ser suyo y el principal lo
        # perdía de vista. El dueño solo se fija al crearlo.
        db.update('fut_teams', datos, 'equipo up', id=existente['id'], obligatorio=True)
    else:
        datos['coach_id'] = uid
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

    # Cómo se siente hoy. Lo pone EL JUGADOR y sí lo ve el entrenador (es el
    # «Estado físico promedio» de su tablero). No confundir con el check-in de
    # bienestar, cuyas respuestas son confidenciales.
    for campo in ('energia', 'motivacion', 'estado_fisico'):
        if campo in d:
            try:
                datos[campo] = max(0, min(100, int(d[campo])))
            except (TypeError, ValueError):
                pass
    if any(c in datos for c in ('energia', 'motivacion', 'estado_fisico')):
        datos['estado_actualizado'] = ahora()

    if not db.upsert('fut_player_profile', datos, 'perfil jug', on_conflict='user_id'):
        return jsonify({'error': 'No se pudo guardar la ficha.'}), 500
    return jsonify({'ok': True})


# ═══════════════════════ EVALUACIONES Y ATRIBUTOS ═══════════════════════
@bp.route('/api/evaluacion', methods=['POST'])
@api
def api_evaluacion():
    """Guarda el Perfil Dinámico (18 atributos) de un jugador con cuenta —
    templates/c_evaluar.html. Ver futbol/db.py:guardar_atributos.
    """
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador evalúa.'}), 403
    d = body()
    pid = d.get('player_id')
    if not pid:
        return jsonify({'error': 'Falta el jugador.'}), 400

    # Vale para los dos tipos de jugador: en un equipo de formación casi nadie
    # tiene cuenta, y sin esto no se podía guardar su evaluación.
    uid = db.equipo_id(current_user.id)
    if de_mi_plantilla(pid):
        dueno = db.dueno_filtro(player_id=pid)
    elif db.one('fut_manual_players', 'manual eval', id=pid, coach_id=uid):
        dueno = db.dueno_filtro(manual_player_id=pid)
    else:
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403
    es_manual = 'manual_player_id' in dueno

    campos_numericos = set(db.ATRIBUTOS_18) | {'potencial'}
    campos_texto = ('fortalezas', 'debilidades', 'evolucion_tecnica',
                    'lesiones_historial', 'posicion_secundaria')
    campos_perfil = {}
    for k in list(campos_numericos) + list(campos_texto):
        v = d.get(k)
        if v in (None, ''):
            continue
        if k in campos_numericos:
            try:
                campos_perfil[k] = max(1, min(100, int(v)))
            except (TypeError, ValueError):
                pass
        else:
            campos_perfil[k] = str(v)[:600]

    # La fatiga llega como bajo|medio|alto y se guarda como número (db.py).
    if d.get('fatiga') in db.FATIGA_A_NUMERO:
        campos_perfil['fatiga'] = db.FATIGA_A_NUMERO[d['fatiga']]
    if d.get('riesgo_sobrecarga') in ('bajo', 'medio', 'alto'):
        campos_perfil['riesgo_sobrecarga'] = d['riesgo_sobrecarga']

    fila = db.guardar_atributos(**dueno, **campos_perfil) if campos_perfil else None

    # Nota histórica: lo que el jugador lee en "Mi Ficha" y lo que ve el coach
    # en "Observaciones". La puntuación que se guarda aquí son los 3 de
    # siempre (recién recalculados) para no romper las pantallas que todavía
    # muestran ese resumen (no hay familia táctica en el modelo nuevo).
    #
    # Solo para quien tiene cuenta: fut_evaluations referencia `usuarios`, así
    # que la nota de un jugador sin cuenta no cabe ahí. La suya vive en los
    # campos de texto de su propia ficha.
    puntuaciones = {k: fila[k] for k in ('tecnica', 'fisico', 'mental')
                    if fila and fila.get(k) is not None}

    if not es_manual:
        db.insert('fut_evaluations', {
            'player_id': pid,
            'coach_id': db.equipo_id(current_user.id),
            'fecha': d.get('fecha') or db.hoy_iso(),
            'notas': (d.get('notas') or '')[:2000],
            'puntuaciones': puntuaciones,
            'creado': ahora(),
        }, obligatorio=True)

    destino = ('futbol.c_eval_jugador' if es_manual else 'futbol.c_jugador')
    return jsonify({'ok': True, 'redirect': url_for(destino, pid=pid)})


@bp.route('/api/equipo/recalcular', methods=['POST'])
@api
def api_equipo_recalcular():
    """Botón «⟳ Recalcular evolución del equipo» de la pantalla Equipo."""
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador puede recalcular la evolución.'}), 403
    tocados = db.recalcular_evolucion_equipo(current_user.id)
    if tocados == 0:
        return jsonify({'ok': True, 'tocados': 0,
                        'mensaje': 'Nadie tiene Perfil Dinámico todavía: evalúa a un jugador primero.'})
    return jsonify({'ok': True, 'tocados': tocados,
                    'mensaje': f'Evolución recalculada: {tocados} jugador{"" if tocados == 1 else "es"}.'})


# ═══════════════════════ PARTIDOS ═══════════════════════
@bp.route('/api/partido', methods=['POST'])
@api
def api_partido():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador registra partidos.'}), 403
    d = body()
    fila = db.insert('fut_matches', {
        'coach_id': db.equipo_id(current_user.id),
        'rival': (d.get('rival') or 'Rival')[:80],
        'fecha': d.get('fecha') or db.hoy_iso(),
        'local': bool(d.get('local', True)),
        'goles_favor': int(d.get('goles_favor') or 0),
        'goles_contra': int(d.get('goles_contra') or 0),
        'competicion': (d.get('competicion') or '')[:80],
        'event_id': d.get('event_id') or None,
        'creado': ahora(),
    })
    if not fila:
        return jsonify({'error': 'No se pudo guardar el partido.'}), 500
    return jsonify({'ok': True, 'partido': fila})


@bp.route('/api/partido/<mid>', methods=['POST', 'PATCH'])
@api
def api_partido_editar(mid):
    """El marcador, desde la propia hoja del partido.

    Se agenda el partido antes de jugarlo, asi que el resultado no se sabe
    hasta despues. Sin esto habia que volver a la lista de partidos a
    corregirlo por otro lado, y el que sale de la agenda nacia siempre 0-0.
    """
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador registra partidos.'}), 403
    if not db.one('fut_matches', 'partido mio', id=mid,
                  coach_id=db.equipo_id(current_user.id)):
        return jsonify({'error': 'Ese partido no es de tu equipo.'}), 404

    d = body()
    datos = {}
    for campo in ('goles_favor', 'goles_contra'):
        if campo in d:
            try:
                datos[campo] = max(0, int(d[campo] or 0))
            except (TypeError, ValueError):
                datos[campo] = 0
    for campo, tope in (('rival', 80), ('competicion', 80)):
        if campo in d:
            datos[campo] = (d[campo] or '')[:tope]
    if 'local' in d:
        datos['local'] = bool(d['local'])
    if not datos:
        return jsonify({'error': 'Nada que actualizar.'}), 400

    db.update('fut_matches', datos, 'partido up', id=mid, obligatorio=True)
    return jsonify({'ok': True})


@bp.route('/api/partido/<mid>/stats', methods=['POST'])
@api
def api_partido_stats(mid):
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador registra estadísticas.'}), 403
    d = body()
    pid = d.get('player_id')
    columna = quien_es_del_equipo(pid)
    if not columna:
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    #  Que la hoja sea de este equipo. Sin esto, con un id de partido ajeno se
    #  podian escribir estadisticas en el partido de otro entrenador.
    if not db.one('fut_matches', 'partido mio', id=mid,
                  coach_id=db.equipo_id(current_user.id)):
        return jsonify({'error': 'Ese partido no es de tu equipo.'}), 403

    datos = {'match_id': mid, columna: pid}
    for campo in ('minutos', 'goles', 'asistencias', 'jugadas_clave',
                  'tarjetas_a', 'tarjetas_r', 'valoracion'):
        if campo in d:
            try:
                datos[campo] = max(0, int(d[campo] or 0))
            except (TypeError, ValueError):
                datos[campo] = 0
    if 'titular' in d:
        datos['titular'] = bool(d['titular'])

    existente = db.one('fut_match_stats', 'stats', match_id=mid, **{columna: pid})
    if existente:
        db.update('fut_match_stats', datos, 'stats up', id=existente['id'],
                  obligatorio=True)
    else:
        db.insert('fut_match_stats', datos, 'stats nueva', obligatorio=True)
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
        'coach_id': db.equipo_id(current_user.id),
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
        db.update('fut_test_results', {'valor': valor}, 'res up', id=existente['id'], obligatorio=True)
    else:
        db.insert('fut_test_results', {
            'test_id': tid, 'player_id': pid, 'valor': valor, 'creado': ahora(),
        }, obligatorio=True)
    return jsonify({'ok': True})


# ═══════════════════════ TÁCTICA ═══════════════════════
@bp.route('/api/jugada', methods=['POST'])
@api
def api_jugada_guardar():
    if not es_coach():
        return jsonify({'error': 'Solo el entrenador guarda jugadas.'}), 403
    d = body()
    nombre = (d.get('nombre') or '').strip() or 'Jugada sin nombre'
    uid = db.equipo_id(current_user.id)
    datos = {
        'nombre': nombre[:80],
        'formacion': (d.get('formacion') or '')[:20],
        'datos': d.get('datos') or {},
    }
    jid = d.get('id')
    if jid:
        # Sin tocar el dueño: se filtraba por el equipo pero se reescribía el
        # `coach_id` con el del asistente, y la jugada desaparecía de la lista.
        if not db.update('fut_tactical_plays', datos, 'jugada up', id=jid, coach_id=uid):
            return jsonify({'error': 'Esa jugada no es de tu equipo o ya no existe.'}), 404
        return jsonify({'ok': True, 'id': jid})

    datos['coach_id'] = uid
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
    db.delete('fut_tactical_plays', 'jugada del', id=jid, coach_id=db.equipo_id(current_user.id), obligatorio=True)
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

    #  Se cierra DESPUES de guardar, no antes. Al reves, un fallo al guardar
    #  dejaba la asignacion como «respondido» sin respuesta detras: el jugador
    #  perdia lo que escribio y el entrenador lo veia como hecho.
    from .mental import cerrar_asignacion
    cerrar_asignacion(current_user.id)

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

    #  Sin obligatorio: el historial es un extra. Si no se puede guardar, la
    #  respuesta ya esta calculada y el jugador tiene que recibirla igual.
    db.insert('fut_ia_chat', {
        'user_id': current_user.id,
        'rol': getattr(current_user, 'role', 'paciente'),
        'pregunta': pregunta,
        'respuesta': respuesta,
        'creado': ahora(),
    })
    return jsonify({'ok': True, 'respuesta': respuesta,
                    'restantes': (restantes - 1) if restantes is not None else None})
