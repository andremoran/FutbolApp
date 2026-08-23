# -*- coding: utf-8 -*-
"""
futbol/account.py — Perfil, planes y canje de códigos.

La pantalla de planes solo muestra; el cobro con tarjeta vive en pagos.py
(PayPal Subscriptions) y el cobro por transferencia también (DeUna), al que
enlaza el botón de cada plan.
"""
from flask import jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles
import suscripciones as subs

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
        datos['n_jugadores'] = db.tamano_plantilla(uid)
    else:
        datos['perfil'] = db.perfil_jugador(uid)
        datos['entrenador'] = db.entrenador_del_jugador(uid)
        datos['atributos'] = db.atributos(uid)
        datos['media'] = db.media_atributos(uid)
        #  `atributos()` devuelve 50 en todo cuando no hay fila, como punto de
        #  partida neutro. Vale para calcular, pero en la cabecera del perfil
        #  ese 50 se lee como una nota que alguien le ha puesto. Y su
        #  entrenador, sobre el mismo chaval, ve «sin evaluar»: el mismo dato
        #  contado de dos formas. Con esto la pantalla sabe cual es el caso.
        datos['evaluado'] = bool(db.fila_atributos(player_id=uid))
        datos['racha'] = db.racha_actual(uid)

    return render_template('perfil.html',
                           tab_activa='',
                           hide_tabbar=True,
                           es_coach=es_coach,
                           dias_pro=subs.dias_restantes(current_user),
                           caduca_pronto=subs.caduca_pronto(current_user),
                           **datos)


@bp.route('/planes')
@login_required
def planes():
    """Los planes con la piel de ProFoot.

    Los precios y el aviso salen de los ajustes del panel, no del código: el
    administrador tiene que poder montar una promoción sin redesplegar.
    """
    from admin import ajustes as ajustes_app
    import pagos

    cfg = ajustes_app()
    return render_template('planes.html',
                           tab_activa='',
                           hide_tabbar=True,
                           cuenta_activa=roles.es_pro(current_user),
                           dias_pro=subs.dias_restantes(current_user),
                           ajustes=cfg,
                           deuna_activo=bool(cfg.get('deuna_activo')
                                             and (cfg.get('deuna_telefono')
                                                  or cfg.get('deuna_qr'))),
                           tarjeta_activa=pagos.configurado(),
                           permisos=roles.PERMISOS_PRO)


@bp.route('/canjear')
@login_required
def canjear():
    """Pantalla para meter un código de suscripción."""
    uid = current_user.id
    previo = db.one('fut_promo_uses', 'mi canje', user_id=uid)
    if previo:
        previo['_hasta'] = db.parse_fecha(previo.get('pro_hasta'))
        previo['_fecha'] = db.parse_fecha(previo.get('creado'))
    return render_template('canjear.html',
                           tab_activa='', hide_tabbar=True,
                           canje=previo,
                           es_pro=roles.es_pro(current_user),
                           dias_pro=subs.dias_restantes(current_user))


@bp.route('/api/canjear', methods=['POST'])
@login_required
def api_canjear():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400

    codigo = ((request.get_json(silent=True) or {}).get('codigo') or '').strip()
    meses, error = subs.canjear(current_user, codigo)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'ok': True, 'meses': meses,
                    'mensaje': f'¡Listo! Tienes {meses} mes(es) de Pro.',
                    'redirect': url_for('futbol.home')})
