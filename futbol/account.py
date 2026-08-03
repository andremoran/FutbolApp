# -*- coding: utf-8 -*-
"""
futbol/account.py — Perfil y planes.

La pantalla de planes solo muestra; el cobro con tarjeta vive en pagos.py
(PayPal Subscriptions), al que enlaza el botón de cada plan.
"""
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user

from . import bp, db


@bp.route('/perfil')
@login_required
def perfil():
    uid = current_user.id
    es_coach = getattr(current_user, 'role', '') == 'especialista'

    datos = {}
    if es_coach:
        datos['equipo'] = db.equipo_del_entrenador(uid)
        datos['codigo'] = db.codigo_equipo(uid)
        datos['n_jugadores'] = len(db.jugadores_del_entrenador(uid))
    else:
        datos['perfil'] = db.perfil_jugador(uid)
        datos['entrenador'] = db.entrenador_del_jugador(uid)
        datos['atributos'] = db.atributos(uid)
        datos['media'] = db.media_atributos(uid)
        datos['racha'] = db.racha_actual(uid)

    return render_template('perfil.html',
                           tab_activa='',
                           hide_tabbar=True,
                           es_coach=es_coach,
                           **datos)


@bp.route('/planes')
@login_required
def planes():
    """Pantalla de planes (screens/PremiumScreen.tsx) con la piel de ProFoot.

    Los tres planes son los de ProFoot; el botón lleva al checkout real de la
    plataforma, que resuelve el cobro y la activación de la cuenta.
    """
    activo = bool(getattr(current_user, 'activo', False))
    return render_template('planes.html',
                           tab_activa='',
                           hide_tabbar=True,
                           cuenta_activa=activo)
