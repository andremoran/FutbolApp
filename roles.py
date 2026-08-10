# -*- coding: utf-8 -*-
"""
roles.py — Los cinco roles de ProFoot y qué puede hacer cada uno.

Un único sitio donde se decide quién ve qué. Si mañana el Jugador gratis puede
usar la IA, se cambia aquí y cambia en toda la app: en el menú, en las rutas y
en los botones.

Los cinco roles
───────────────
    Jugador          rol='paciente'     · tier='free'
    Jugador Pro      rol='paciente'     · tier='pro'
    Entrenador       rol='especialista' · tier='free'
    Coach Pro        rol='especialista' · tier='pro'
    Administrador    es_admin=true

Por qué rol y tier van separados: el rol no cambia nunca y el tier cambia con
cada cobro y con cada impago. Si fueran un solo campo, cada renovación tendría
que reescribir también qué es la persona, y un fallo de pago convertiría a un
entrenador en otra cosa.
"""
from functools import wraps

from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user

# ─── Claves ─────────────────────────────────────────────────────────────────
JUGADOR      = 'jugador'
JUGADOR_PRO  = 'jugador_pro'
ENTRENADOR   = 'entrenador'
COACH_PRO    = 'coach_pro'
ADMIN        = 'admin'

ROLES = {
    JUGADOR: {
        'etiqueta': 'Jugador',
        'emoji': '⚽',
        'descripcion': 'Tu progreso, tus hábitos y la agenda del equipo.',
        'base': 'paciente', 'tier': 'free',
    },
    JUGADOR_PRO: {
        'etiqueta': 'Jugador Pro',
        'emoji': '⭐',
        'descripcion': 'Todo lo del jugador más IA Coach, evaluaciones y evolución.',
        'base': 'paciente', 'tier': 'pro',
    },
    ENTRENADOR: {
        'etiqueta': 'Entrenador',
        'emoji': '📋',
        'descripcion': 'Hasta 12 jugadores, calendario y asistencia.',
        'base': 'especialista', 'tier': 'free',
    },
    COACH_PRO: {
        'etiqueta': 'Coach Pro',
        'emoji': '🏆',
        'descripcion': 'Plantilla sin límite, evaluaciones con baremos, táctica e IA.',
        'base': 'especialista', 'tier': 'pro',
    },
    ADMIN: {
        'etiqueta': 'Administrador',
        'emoji': '🛡️',
        'descripcion': 'Usuarios, cobros y códigos de suscripción.',
        'base': 'admin', 'tier': 'pro',
    },
}


# ─── Qué desbloquea el plan Pro ─────────────────────────────────────────────
#  Cada permiso lleva el nombre con el que se le explica al usuario cuando se
#  topa con el candado: sin eso, la pantalla de bloqueo dice «función Pro» y
#  nadie sabe qué está comprando.
PERMISOS_PRO = {
    'ia':            'Asistente de IA',
    'evaluaciones':  'Evaluaciones con baremos internacionales',
    'evolucion':     'Gráficas de evolución',
    'ranking':       'Ranking y comparación del equipo',
    'tactica':       'Pizarra táctica y biblioteca de jugadas',
    'planes':        'Planes de entrenamiento reutilizables',
    'informes':      'Informes y exportación',
    'medico':        'Ficha médica y control de lesiones',
}

# Lo que un entrenador gratis puede tener sin pagar. Doce entran en una
# convocatoria; a partir de ahí ya es un equipo de verdad.
LIMITE_PLANTILLA_FREE = 12
LIMITE_EVENTOS_FREE = 40        # eventos futuros en el calendario
LIMITE_TESTS_FREE = 3           # evaluaciones guardadas por jugador


def clave_de(usuario):
    """El rol efectivo del usuario, como una de las cinco claves."""
    if usuario is None or not getattr(usuario, 'is_authenticated', False):
        return None
    if getattr(usuario, 'is_admin', lambda: False)():
        return ADMIN
    pro = es_pro(usuario)
    if getattr(usuario, 'role', '') == 'especialista':
        return COACH_PRO if pro else ENTRENADOR
    return JUGADOR_PRO if pro else JUGADOR


def etiqueta_de(usuario):
    return ROLES.get(clave_de(usuario) or '', {}).get('etiqueta', 'Invitado')


def es_pro(usuario):
    """¿Tiene el plan de pago vigente?

    El administrador siempre lo tiene: si no, no podría ver lo que compran sus
    usuarios y no podría dar soporte.
    """
    if usuario is None or not getattr(usuario, 'is_authenticated', False):
        return False
    if getattr(usuario, 'is_admin', lambda: False)():
        return True
    if (getattr(usuario, 'tier', 'free') or 'free') != 'pro':
        return False
    return not _vencido(getattr(usuario, 'pro_hasta', None))


def _vencido(hasta):
    """¿Se pasó la fecha? Sin fecha = suscripción sin caducidad conocida."""
    if not hasta:
        return False
    from datetime import datetime, timezone
    try:
        f = datetime.fromisoformat(str(hasta).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return False
    if f.tzinfo is None:
        f = f.replace(tzinfo=timezone.utc)
    return f < datetime.now(timezone.utc)


def es_admin(usuario):
    return bool(usuario is not None
                and getattr(usuario, 'is_authenticated', False)
                and getattr(usuario, 'is_admin', lambda: False)())


def es_coach(usuario):
    return getattr(usuario, 'role', '') == 'especialista'


def puede(usuario, permiso):
    """¿Este usuario tiene acceso a esta función?"""
    if permiso not in PERMISOS_PRO:
        return True
    return es_pro(usuario)


# ─── Guardias de ruta ───────────────────────────────────────────────────────
def _respuesta_bloqueo(permiso):
    """Página de mejora, o JSON si quien llama es la API."""
    nombre = PERMISOS_PRO.get(permiso, 'Esta función')
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'error': f'{nombre} es del plan Pro.',
                        'pro': True,
                        'url': url_for('futbol.planes')}), 402
    return redirect(url_for('futbol.pro', f=permiso))


def solo_pro(permiso):
    """Cierra una ruta a los planes gratuitos.

        @bp.route('/coach/ia')
        @solo_pro('ia')
        def c_ia(): ...
    """
    def decorador(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if not getattr(current_user, 'is_authenticated', False):
                return redirect(url_for('auth.entrar'))
            if not puede(current_user, permiso):
                return _respuesta_bloqueo(permiso)
            return f(*a, **kw)
        return wrapper
    return decorador


def solo_admin(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not getattr(current_user, 'is_authenticated', False):
            return redirect(url_for('auth.entrar'))
        if not es_admin(current_user):
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Solo para administradores.'}), 403
            flash('Esa página es solo para administradores.', 'error')
            return redirect(url_for('futbol.home'))
        return f(*a, **kw)
    return wrapper


# ─── Límites del plan gratuito ──────────────────────────────────────────────
def limite_plantilla(usuario):
    """Cuántos jugadores admite la plantilla. None = sin límite."""
    return None if es_pro(usuario) else LIMITE_PLANTILLA_FREE


def plantilla_llena(usuario, n_actual):
    tope = limite_plantilla(usuario)
    return tope is not None and n_actual >= tope
