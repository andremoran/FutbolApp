# -*- coding: utf-8 -*-
"""
futbol/equipo.py — Jugadores sin cuenta y solicitudes de ingreso.

Dos huecos que dejaba el registro por código:

  1. Un chico de once años no tiene correo. El entrenador lo apunta a mano,
     lo evalúa y le pasa lista igual que a los demás; si algún día se
     registra, se le enchufa la ficha con todo el histórico.

  2. El código de equipo deja entrar a cualquiera que lo tenga. Con las
     solicitudes, el jugador pide y el entrenador acepta — que es lo que
     hace falta en cuanto el código circula por un grupo de WhatsApp.
"""
import logging
from datetime import datetime, timezone

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles

from . import bp, db

logger = logging.getLogger(__name__)

POSICIONES = ['Portero', 'Lateral derecho', 'Central', 'Lateral izquierdo',
              'Pivote', 'Interior', 'Mediapunta', 'Extremo derecho',
              'Extremo izquierdo', 'Delantero']


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _coach_o_fuera():
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.inicio'))
    return None


def _guardia_coach():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el entrenador gestiona la plantilla.'}), 403
    return None


def solicitudes_pendientes(coach_id):
    return db.rows('fut_join_requests', 'solicitudes',
                   coach_id=coach_id, estado='pendiente',
                   _order='creado', _desc=True) or []


# ═══════════════════════ JUGADORES SIN CUENTA ═══════════════════════
@bp.route('/coach/jugadores-manuales')
@login_required
def c_manuales():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = current_user.id
    lista = db.rows('fut_manual_players', 'manuales', coach_id=uid,
                    _order='nombre') or []
    activos = [m for m in lista if m.get('activo')]

    # Cuántas evaluaciones tiene cada uno: sin esto no se sabe a quién falta medir.
    conteo = {}
    for r in (db.rows('fut_eval_results', 'evals manual', coach_id=uid) or []):
        mid = r.get('manual_player_id')
        if mid:
            conteo[str(mid)] = conteo.get(str(mid), 0) + 1
    for m in lista:
        m['_evals'] = conteo.get(str(m['id']), 0)
        m['_alta'] = db.parse_fecha(m.get('creado'))

    return render_template('c_manuales.html',
                           tab_activa='equipo', hide_tabbar=True,
                           manuales=activos,
                           archivados=[m for m in lista if not m.get('activo')],
                           posiciones=POSICIONES,
                           n_plantilla=len(db.jugadores_del_entrenador(uid)))


@bp.route('/api/manual', methods=['POST'])
@login_required
def api_manual():
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = current_user.id
    nombre = (d.get('nombre') or '').strip()
    if len(nombre) < 2:
        return jsonify({'error': 'Escribe el nombre del jugador.'}), 400

    datos = {
        'nombre': nombre[:100],
        'posicion': (d.get('posicion') or '')[:40],
        'pie_habil': (d.get('pie_habil') or '')[:20],
        'telefono': (d.get('telefono') or '')[:30],
        'tutor': (d.get('tutor') or '')[:120],
        'notas': (d.get('notas') or '')[:600],
    }
    for campo, tipo in (('dorsal', int), ('anio_nacimiento', int),
                        ('estatura', float), ('peso', float)):
        v = d.get(campo)
        if v not in (None, ''):
            try:
                datos[campo] = tipo(v)
            except (TypeError, ValueError):
                pass

    mid = d.get('id')
    if mid:
        if not db.one('fut_manual_players', 'mio', id=mid, coach_id=uid):
            return jsonify({'error': 'Ese jugador no es de tu equipo.'}), 403
        db.update('fut_manual_players', datos, 'manual up', id=mid, coach_id=uid)
        return jsonify({'ok': True, 'id': mid, 'mensaje': 'Ficha actualizada.'})

    # Los apuntados a mano cuentan para el tope del plan gratuito: si no,
    # el límite de plantilla no serviría de nada.
    if not roles.es_pro(current_user):
        n = (len(db.jugadores_del_entrenador(uid))
             + len(db.rows('fut_manual_players', 'cuenta', coach_id=uid, activo=True) or []))
        if n >= roles.LIMITE_PLANTILLA_FREE:
            return jsonify({
                'error': f'El plan gratuito llega a {roles.LIMITE_PLANTILLA_FREE} '
                         'jugadores. Pásate a Pro para una plantilla sin límite.',
                'pro': True, 'url': url_for('futbol.planes')}), 402

    datos.update({'coach_id': uid, 'activo': True, 'creado': _ahora()})
    fila = db.insert('fut_manual_players', datos, 'manual nuevo')
    if not fila:
        return jsonify({'error': 'No se pudo guardar.'}), 500
    return jsonify({'ok': True, 'id': fila['id'],
                    'mensaje': f'{nombre} está en la plantilla.'})


@bp.route('/api/manual/<mid>', methods=['DELETE'])
@login_required
def api_manual_archivar(mid):
    """Se archiva en vez de borrar: si se borrara, sus evaluaciones quedarían
    huérfanas y el histórico del equipo se falsearía."""
    error = _guardia_coach()
    if error:
        return error
    db.update('fut_manual_players', {'activo': False}, 'archivar',
              id=mid, coach_id=current_user.id)
    return jsonify({'ok': True, 'mensaje': 'Jugador archivado. Su histórico se conserva.'})


@bp.route('/api/manual/<mid>/restaurar', methods=['POST'])
@login_required
def api_manual_restaurar(mid):
    error = _guardia_coach()
    if error:
        return error
    db.update('fut_manual_players', {'activo': True}, 'restaurar',
              id=mid, coach_id=current_user.id)
    return jsonify({'ok': True, 'mensaje': 'Jugador de vuelta en la plantilla.'})


@bp.route('/api/manual/<mid>/vincular', methods=['POST'])
@login_required
def api_manual_vincular(mid):
    """Enchufa la ficha manual a una cuenta que acaba de registrarse."""
    error = _guardia_coach()
    if error:
        return error

    uid = current_user.id
    d = request.get_json(silent=True) or {}
    pid = d.get('player_id')

    manual = db.one('fut_manual_players', 'manual', id=mid, coach_id=uid)
    if not manual:
        return jsonify({'error': 'Ese jugador no es de tu equipo.'}), 404
    if not any(str(j['id']) == str(pid) for j in db.jugadores_del_entrenador(uid)):
        return jsonify({'error': 'Esa cuenta no está en tu plantilla.'}), 403

    # Las evaluaciones pasan a la cuenta: es lo que hace que valga la pena
    # haberlo apuntado a mano durante meses.
    n = 0
    for r in (db.rows('fut_eval_results', 'evals manual',
                      coach_id=uid, manual_player_id=mid) or []):
        db.update('fut_eval_results',
                  {'player_id': pid, 'manual_player_id': None}, 'traspasar', id=r['id'])
        n += 1

    db.update('fut_manual_players', {'vinculado_a': pid, 'activo': False},
              'vincular', id=mid)
    return jsonify({'ok': True,
                    'mensaje': f'Vinculado. Se traspasaron {n} evaluación(es).'})


# ═══════════════════════ SOLICITUDES DE INGRESO ═══════════════════════
@bp.route('/coach/solicitudes')
@login_required
def c_solicitudes():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = current_user.id
    todas = db.rows('fut_join_requests', 'solicitudes todas', coach_id=uid,
                    _order='creado', _desc=True) or []
    ids = [s['player_id'] for s in todas if s.get('player_id')]
    personas = {}
    if ids:
        personas = {p['id']: p for p in db.q(
            lambda: db.sb().table('usuarios').select('*').in_('id', ids).execute().data or [],
            [], 'personas solicitud')}
    for s in todas:
        s['_jugador'] = db._normalizar_usuario(personas.get(s.get('player_id')))
        s['_fecha'] = db.parse_fecha(s.get('creado'))

    n = len(db.jugadores_del_entrenador(uid))
    return render_template('c_solicitudes.html',
                           tab_activa='equipo', hide_tabbar=True,
                           pendientes=[s for s in todas if s.get('estado') == 'pendiente'],
                           resueltas=[s for s in todas if s.get('estado') != 'pendiente'][:20],
                           codigo=db.codigo_equipo(uid),
                           n_plantilla=n,
                           llena=roles.plantilla_llena(current_user, n),
                           tope=roles.limite_plantilla(current_user))


@bp.route('/api/solicitud/<sid>', methods=['POST'])
@login_required
def api_solicitud(sid):
    error = _guardia_coach()
    if error:
        return error

    uid = current_user.id
    d = request.get_json(silent=True) or {}
    accion = d.get('accion')
    sol = db.one('fut_join_requests', 'solicitud', id=sid, coach_id=uid)
    if not sol:
        return jsonify({'error': 'Esa solicitud no existe.'}), 404
    if sol.get('estado') != 'pendiente':
        return jsonify({'error': 'Esa solicitud ya estaba resuelta.'}), 400

    if accion == 'aceptar':
        n = len(db.jugadores_del_entrenador(uid))
        if roles.plantilla_llena(current_user, n):
            return jsonify({
                'error': f'Tu plantilla llegó a {roles.LIMITE_PLANTILLA_FREE} '
                         'jugadores. Pásate a Pro para aceptar más.',
                'pro': True, 'url': url_for('futbol.planes')}), 402

        # Un jugador pertenece a un equipo a la vez: si ya estaba en otro, se
        # cambia de equipo en vez de duplicarse.
        previo = db.one('fut_plantilla', 'vinculo previo', player_id=sol['player_id'])
        if previo:
            db.update('fut_plantilla', {'coach_id': uid, 'activo': True},
                      'cambiar equipo', id=previo['id'])
        else:
            db.insert('fut_plantilla', {
                'coach_id': uid, 'player_id': sol['player_id'],
                'activo': True, 'creado': _ahora()}, 'aceptar solicitud')

        db.update('fut_join_requests', {'estado': 'aceptada', 'resuelto': _ahora()},
                  'aceptar', id=sid)
        return jsonify({'ok': True, 'mensaje': 'Jugador aceptado en el equipo.'})

    if accion == 'rechazar':
        db.update('fut_join_requests', {'estado': 'rechazada', 'resuelto': _ahora()},
                  'rechazar', id=sid)
        return jsonify({'ok': True, 'mensaje': 'Solicitud rechazada.'})

    return jsonify({'error': 'Acción desconocida.'}), 400


@bp.route('/coach/jugador/<pid>/sacar', methods=['POST'])
@login_required
def c_sacar_jugador(pid):
    error = _guardia_coach()
    if error:
        return error
    uid = current_user.id
    v = db.one('fut_plantilla', 'vinculo', player_id=pid, coach_id=uid)
    if not v:
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 404
    db.delete('fut_plantilla', 'sacar', id=v['id'])
    return jsonify({'ok': True, 'mensaje': 'Jugador fuera de la plantilla. '
                                           'Su cuenta y su histórico siguen ahí.'})


# ═══════════════════════ LADO DEL JUGADOR ═══════════════════════
@bp.route('/unirme')
@login_required
def p_unirme():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_equipo'))

    uid = current_user.id
    mia = db.one('fut_join_requests', 'mi solicitud', player_id=uid)
    if mia:
        mia['_fecha'] = db.parse_fecha(mia.get('creado'))
        if mia.get('coach_id'):
            mia['_coach'] = db._normalizar_usuario(
                db.one('usuarios', 'coach sol', id=mia['coach_id']))

    return render_template('p_unirme.html',
                           tab_activa='', hide_tabbar=True,
                           entrenador=db.entrenador_del_jugador(uid),
                           solicitud=mia,
                           posiciones=POSICIONES)


@bp.route('/api/unirme', methods=['POST'])
@login_required
def api_unirme():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') == 'especialista':
        return jsonify({'error': 'Los entrenadores no se unen a equipos.'}), 403

    uid = current_user.id
    d = request.get_json(silent=True) or {}
    codigo = (d.get('codigo') or '').strip().upper()
    if not codigo:
        return jsonify({'error': 'Escribe el código que te dio tu entrenador.'}), 400

    coach = db.one('usuarios', 'coach por codigo',
                   codigo_equipo=codigo, rol='especialista')
    if not coach:
        return jsonify({'error': 'Ese código no existe. Pídeselo otra vez a tu '
                                 'entrenador y revisa mayúsculas y números.'}), 404

    actual = db.entrenador_del_jugador(uid)
    if actual and str(actual['id']) == str(coach['id']):
        return jsonify({'error': f'Ya estás en el equipo de {coach["nombre"]}.'}), 400

    datos = {
        'coach_id': coach['id'], 'player_id': uid,
        'mensaje': (d.get('mensaje') or '')[:400],
        'posicion': (d.get('posicion') or '')[:40],
        'estado': 'pendiente', 'resuelto': None, 'creado': _ahora(),
    }
    previa = db.one('fut_join_requests', 'previa', player_id=uid, coach_id=coach['id'])
    if previa:
        db.update('fut_join_requests', datos, 'resolicitar', id=previa['id'])
    else:
        db.insert('fut_join_requests', datos, 'solicitar')

    return jsonify({'ok': True,
                    'mensaje': f'Solicitud enviada a {coach["nombre"]}. '
                               'Te avisará cuando la acepte.',
                    'redirect': url_for('futbol.p_unirme')})
