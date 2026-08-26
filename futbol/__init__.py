# -*- coding: utf-8 -*-
"""
futbol/ — Las pantallas de ProFoot Assistant.

Blueprint montado en la raíz: la app de fútbol ES el producto, no una sección
de otra cosa.
"""
from flask import Blueprint

from . import db as futdb

bp = Blueprint('futbol', __name__)


def registrar_futbol(app, supabase):
    futdb.init(supabase)

    # Import diferido: los módulos de rutas importan `bp` de aquí.
    from . import (auth, player, coach, api, account, mental, social,   # noqa: F401
                   evaluaciones, calendario, equipo, salud,             # noqa: F401
                   microciclos)                                         # noqa: F401

    app.register_blueprint(bp)
    return bp
