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

from flask import abort, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required

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

        # Marcar como leídos los personales
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
        'coach_id': current_user.id,
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
    db.delete('fut_messages', 'borrar mensaje', id=mid, coach_id=db.equipo_id(current_user.id))
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

    return render_template('c_observaciones.html',
                           tab_activa='agenda', hide_tabbar=True,
                           observaciones=lista,
                           jugadores=list(jugadores.values()),
                           hoy=db.hoy_iso())


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

    fila = db.insert('fut_observaciones', {
        'coach_id': current_user.id,
        'player_id': destino,
        'fecha': d.get('fecha') or db.hoy_iso(),
        'titulo': (d.get('titulo') or 'Sesión')[:120],
        'texto': texto[:4000],
        'creado': _ahora(),
    }, 'observacion')
    if not fila:
        return jsonify({'error': 'No se pudo guardar.'}), 500
    return jsonify({'ok': True})


@bp.route('/api/observacion/<oid>', methods=['DELETE'])
@login_required
def api_observacion_borrar(oid):
    from .api import api_guard

    err = api_guard(solo_coach=True)
    if err:
        return err
    db.delete('fut_observaciones', 'borrar obs', id=oid, coach_id=db.equipo_id(current_user.id))
    return jsonify({'ok': True})
