# -*- coding: utf-8 -*-
"""
futbol/mental.py — Salud mental y emocional.

Regla que gobierna todo el módulo: **el entrenador NUNCA ve las respuestas**.
Solo ve un semáforo (verde/ámbar/rojo) y la fecha. Si esa frontera se rompe,
los jugadores dejan de responder con honestidad y el módulo deja de servir.
Por eso las consultas del lado del coach seleccionan columnas explícitas y
jamás `respuestas`.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from functools import wraps

from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from . import bp, db

logger = logging.getLogger(__name__)

# Semanas sin check-in a partir de las cuales se avisa al entrenador
SEMANAS_SILENCIO = 2


def solo_entrenador(f):
    from flask import redirect, url_for

    @wraps(f)
    @login_required
    def wrapper(*a, **kw):
        if getattr(current_user, 'role', '') != 'especialista':
            return redirect(url_for('futbol.inicio'))
        return f(*a, **kw)
    return wrapper


def _ahora():
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════ VISTA DEL ENTRENADOR ═══════════════════════
@bp.route('/coach/mental')
@solo_entrenador
def c_mental():
    uid = db.equipo_id(current_user.id)
    jugadores = db.jugadores_del_entrenador(uid)

    ultimos = {}
    if jugadores:
        ids = [j['id'] for j in jugadores]
        # OJO: se piden columnas EXPLÍCITAS. Nunca `respuestas`.
        filas = db.q(
            lambda: db.sb().table('fut_checkins')
            .select('player_id, fecha, semaforo, puntaje')
            .in_('player_id', ids).order('fecha', desc=True).execute().data or [],
            [], 'semaforos')
        for f in filas:
            pid = f['player_id']
            if pid not in ultimos:          # ya vienen ordenados: el primero es el último
                ultimos[pid] = f

    hoy = date.today()
    limite = hoy - timedelta(weeks=SEMANAS_SILENCIO)
    conteo = {'verde': 0, 'ambar': 0, 'rojo': 0, 'sin_datos': 0}

    for j in jugadores:
        c = ultimos.get(j['id'])
        j['_checkin'] = c
        if not c:
            j['_estado'] = 'sin_datos'
        else:
            f = db.parse_fecha(c.get('fecha'))
            j['_fecha'] = f
            j['_atrasado'] = bool(f and f < limite)
            j['_estado'] = c.get('semaforo') or 'verde'
        conteo[j['_estado'] if j['_estado'] in conteo else 'sin_datos'] += 1

    # Los que peor están, primero: es lo que el entrenador necesita ver.
    orden = {'rojo': 0, 'ambar': 1, 'sin_datos': 2, 'verde': 3}
    jugadores.sort(key=lambda j: (orden.get(j['_estado'], 9), j.get('name') or ''))

    asignaciones = db.rows('fut_mental_asignaciones', 'asignaciones',
                           coach_id=uid, _order='creado', _desc=True, _limit=10)
    for a in asignaciones:
        a['_fecha'] = db.parse_fecha(a.get('creado'))

    return render_template('c_mental.html',
                           tab_activa='equipo',
                           hide_tabbar=True,
                           jugadores=jugadores,
                           conteo=conteo,
                           total=len(jugadores),
                           asignaciones=asignaciones,
                           semanas=SEMANAS_SILENCIO)


@bp.route('/coach/mental/asignar')
@solo_entrenador
def c_asignar_checkin():
    return render_template('c_asignar_checkin.html',
                           tab_activa='equipo',
                           hide_tabbar=True,
                           jugadores=db.jugadores_del_entrenador(db.equipo_id(current_user.id)))


# ═══════════════════════ API ═══════════════════════
@bp.route('/api/mental/asignar', methods=['POST'])
@login_required
def api_mental_asignar():
    from .api import api_guard, cuerpo

    err = api_guard(solo_coach=True)
    if err:
        return err

    d = cuerpo()
    destinos = d.get('players') or []
    mensaje = (d.get('mensaje') or '').strip()[:400]
    limite = d.get('fecha_limite') or None

    mios = {str(j['id']) for j in db.jugadores_del_entrenador(db.equipo_id(current_user.id))}
    destinos = [p for p in destinos if str(p) in mios]
    if not destinos:
        return jsonify({'error': 'Elige al menos un jugador de tu plantilla.'}), 400

    creadas = 0
    for pid in destinos:
        fila = db.insert('fut_mental_asignaciones', {
            'coach_id': current_user.id,
            'player_id': pid,
            'mensaje': mensaje,
            'fecha_limite': limite,
            'estado': 'pendiente',
            'creado': _ahora(),
        }, 'asignar checkin')
        if fila:
            creadas += 1

    if not creadas:
        return jsonify({'error': 'No se pudo asignar. Revisa la base de datos.'}), 500
    return jsonify({'ok': True, 'creadas': creadas})


# ═══════════════════════ AYUDAS PARA EL JUGADOR ═══════════════════════
def asignacion_pendiente(player_id):
    """Check-in que el entrenador asignó y el jugador aún no respondió."""
    filas = db.rows('fut_mental_asignaciones', 'pendiente',
                    player_id=player_id, estado='pendiente',
                    _order='creado', _desc=True, _limit=1)
    if not filas:
        return None
    a = filas[0]
    a['_limite'] = db.parse_fecha(a.get('fecha_limite'))
    return a


def cerrar_asignacion(player_id):
    """Al responder, se cierra la asignación pendiente si la había."""
    a = asignacion_pendiente(player_id)
    if a:
        db.update('fut_mental_asignaciones',
                  {'estado': 'respondido', 'respondido': _ahora()},
                  'cerrar asignacion', id=a['id'])


# ═══════════════════════ RECURSOS DE APOYO ═══════════════════════
# Se muestran cuando el semáforo sale rojo. No sustituyen ayuda profesional y
# el texto lo dice claramente.
RECURSOS = [
    ('🗣️', 'Habla con alguien de confianza',
     'Tu entrenador, un familiar o un compañero. Poner en palabras lo que pasa '
     'ya baja la carga.'),
    ('😴', 'Protege tu descanso',
     'Dormir mal amplifica todo lo demás. Intenta 8 horas y evita pantallas la '
     'hora antes de acostarte.'),
    ('🏃', 'Muévete aunque no tengas ganas',
     'Veinte minutos de actividad suave cambian el ánimo más rápido que quedarse quieto.'),
    ('🧑‍⚕️', 'Busca ayuda profesional si esto se sostiene',
     'Si llevas semanas así, habla con un psicólogo del deporte o con tu médico. '
     'Es lo mismo que ir al fisio por una lesión.'),
]
