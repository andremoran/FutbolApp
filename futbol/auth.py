# -*- coding: utf-8 -*-
"""
futbol/auth.py — Reparto según el rol.

El registro y el acceso viven en auth.py (raíz de la app); aquí solo está la
puerta que manda a cada quien a su pestaña Inicio.
"""
from flask import redirect, url_for
from flask_login import current_user, login_required

from . import bp


@bp.route('/app')
@login_required
def home():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_inicio'))
    return redirect(url_for('futbol.inicio'))
