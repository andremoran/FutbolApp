# -*- coding: utf-8 -*-
"""
futbol/auth.py — Reparto según el rol.

El registro y el acceso viven en auth.py (raíz de la app); aquí solo está la
puerta que manda a cada quien a su pestaña Inicio.
"""
from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import bp


@bp.route('/app')
@login_required
def home():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_inicio'))
    return redirect(url_for('futbol.inicio'))


@bp.route('/pro')
@login_required
def pro():
    """Dónde acaba quien toca una función de pago con el plan gratuito.

    No es la pantalla de planes: aquí se explica QUÉ función pedía y por qué
    está en Pro. Mandarlo directo a la lista de precios deja a la persona sin
    saber qué acaba de intentar hacer.
    """
    import roles
    permiso = request.args.get('f') or ''
    return render_template(
        'pro.html',
        hide_tabbar=True,
        funcion=roles.PERMISOS_PRO.get(permiso, 'Esta función'),
        permiso=permiso,
        es_coach=getattr(current_user, 'role', '') == 'especialista',
        permisos=roles.PERMISOS_PRO)
