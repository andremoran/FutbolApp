# -*- coding: utf-8 -*-
"""
pagos.py — Cobro con tarjeta en FutbolApp (PayPal Subscriptions).

PayPal cobra con tarjeta sin que el usuario necesite cuenta de PayPal, y el
número de la tarjeta nunca pasa por nuestro servidor: lo captura el SDK de
PayPal. Nosotros solo verificamos la suscripción contra su API y activamos.

Los Billing Plans se crean UNA vez con `python crear_planes_paypal.py`; sus IDs
quedan en planes_paypal.json.
"""
import json
import logging
import os
from datetime import datetime, timezone

import requests
from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

logger = logging.getLogger(__name__)
bp = Blueprint('pagos', __name__, url_prefix='/pagos')

PAYPAL_ENV = (os.getenv('PAYPAL_ENV', 'live') or 'live').lower()
PAYPAL_CLIENT_ID = (os.getenv('PAYPAL_CLIENT_ID') or '').strip()
PAYPAL_SECRET = (os.getenv('PAYPAL_SECRET') or '').strip()
API = ('https://api-m.paypal.com' if PAYPAL_ENV == 'live'
       else 'https://api-m.sandbox.paypal.com')

ARCHIVO_PLANES = os.path.join(os.path.dirname(__file__), 'planes_paypal.json')


# ─── Catálogo (los planes de ProFoot) ────────────────────────────────────────
PLANES = {
    'jugador_pro': {
        'nombre': 'Jugador Pro',
        'precio': '4.99',
        'rol': 'paciente',
        'descripcion': 'Todo tu progreso, IA Coach y pruebas físicas.',
    },
    'entrenador_pro': {
        'nombre': 'Entrenador Pro',
        'precio': '14.99',
        'rol': 'especialista',
        'descripcion': 'Plantilla ilimitada, táctica, evaluaciones e IA.',
    },
    'club': {
        'nombre': 'Club',
        'precio': '49.00',
        'rol': 'especialista',
        'descripcion': 'Varios entrenadores y categorías.',
    },
}


def plan_para(rol):
    """El plan que le toca a cada rol."""
    return 'entrenador_pro' if rol == 'especialista' else 'jugador_pro'


def ids_planes():
    """IDs de los Billing Plans creados en PayPal. Vacío si aún no se crearon."""
    try:
        with open(ARCHIVO_PLANES, encoding='utf-8') as fh:
            return json.load(fh).get(PAYPAL_ENV, {})
    except Exception:
        return {}


def configurado():
    return bool(PAYPAL_CLIENT_ID and PAYPAL_SECRET)


# ─── API de PayPal ───────────────────────────────────────────────────────────
def token_paypal():
    r = requests.post(f'{API}/v1/oauth2/token',
                      auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
                      data={'grant_type': 'client_credentials'},
                      timeout=25)
    r.raise_for_status()
    return r.json()['access_token']


def ver_suscripcion(sub_id):
    tok = token_paypal()
    r = requests.get(f'{API}/v1/billing/subscriptions/{sub_id}',
                     headers={'Authorization': f'Bearer {tok}'}, timeout=25)
    r.raise_for_status()
    return r.json()


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def activar_usuario(user_id, plan_clave, sub):
    """Marca la cuenta como activa y guarda el comprobante."""
    from futbol import db
    db.update('usuarios', {
        'activo': True,
        'plan': plan_clave,
        'suscripcion_id': sub.get('id'),
        'suscripcion_estado': sub.get('status'),
        'suscripcion_desde': _ahora(),
    }, 'activar', id=user_id)
    db.insert('fut_pagos', {
        'user_id': user_id,
        'plan': plan_clave,
        'suscripcion_id': sub.get('id'),
        'estado': sub.get('status'),
        'proveedor': 'paypal',
        'bruto': json.dumps(sub)[:8000],
        'creado': _ahora(),
    }, 'registro pago')
    logger.info('Cuenta %s activada con %s (%s)', user_id, plan_clave, sub.get('id'))


def desactivar_por_suscripcion(sub_id, estado):
    from futbol import db
    fila = db.one('usuarios', 'por suscripcion', suscripcion_id=sub_id)
    if not fila:
        return
    db.update('usuarios', {'activo': False, 'suscripcion_estado': estado},
              'desactivar', id=fila['id'])
    logger.info('Cuenta %s desactivada (%s)', fila['id'], estado)


# ═══════════════════════ PANTALLAS ═══════════════════════
@bp.route('/planes')
@login_required
def planes_checkout():
    return redirect(url_for('futbol.planes'))


@bp.route('/checkout/<plan>')
@login_required
def checkout(plan):
    meta = PLANES.get(plan)
    if not meta:
        flash('Ese plan no existe.', 'error')
        return redirect(url_for('futbol.planes'))

    if not configurado():
        flash('El cobro con tarjeta todavía no está configurado. '
              'Escríbenos y lo activamos.', 'warning')
        return redirect(url_for('futbol.planes'))

    plan_id = ids_planes().get(plan)
    if not plan_id:
        flash('Ese plan aún no está dado de alta en la pasarela de pago.', 'warning')
        return redirect(url_for('futbol.planes'))

    return render_template('pago_checkout.html',
                           hide_tabbar=True,
                           plan=plan,
                           plan_id=plan_id,
                           meta=meta,
                           client_id=PAYPAL_CLIENT_ID)


@bp.route('/listo')
@login_required
def listo():
    return render_template('pago_listo.html', hide_tabbar=True)


# ═══════════════════════ API ═══════════════════════
@bp.route('/api/activar', methods=['POST'])
@login_required
def api_activar():
    """Tras aprobar en el recuadro de PayPal, verificamos contra su API.

    Nunca confiamos en lo que manda el navegador: se consulta la suscripción
    del lado del servidor antes de activar nada.
    """
    from app import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400

    datos = request.get_json(silent=True) or {}
    sub_id = (datos.get('subscription_id') or '').strip()
    plan = (datos.get('plan') or '').strip()
    if not sub_id or plan not in PLANES:
        return jsonify({'error': 'Datos incompletos.'}), 400

    try:
        sub = ver_suscripcion(sub_id)
    except requests.HTTPError as e:
        logger.error('PayPal activar: %s', getattr(e.response, 'text', e))
        return jsonify({'error': 'No pudimos verificar el pago con PayPal.'}), 502
    except Exception as e:
        logger.error('PayPal activar: %s', e)
        return jsonify({'error': 'No pudimos verificar el pago.'}), 502

    if sub.get('status') not in ('ACTIVE', 'APPROVED'):
        return jsonify({'error': f'El pago quedó en estado {sub.get("status")}.'}), 400

    # El plan_id que devuelve PayPal debe ser el que pedimos: evita que alguien
    # active el plan caro pagando el barato.
    esperado = ids_planes().get(plan)
    if esperado and sub.get('plan_id') != esperado:
        logger.warning('plan_id no coincide: %s != %s', sub.get('plan_id'), esperado)
        return jsonify({'error': 'El plan cobrado no coincide.'}), 400

    activar_usuario(current_user.id, plan, sub)
    return jsonify({'ok': True, 'redirect': url_for('pagos.listo')})


@bp.route('/webhook', methods=['POST'])
def webhook():
    """Avisos de PayPal: cancelaciones, suspensiones e impagos."""
    evento = request.get_json(silent=True) or {}
    tipo = evento.get('event_type', '')
    recurso = evento.get('resource', {}) or {}
    sub_id = recurso.get('id') or recurso.get('billing_agreement_id')

    logger.info('Webhook PayPal: %s (%s)', tipo, sub_id)

    if sub_id and tipo in ('BILLING.SUBSCRIPTION.CANCELLED',
                           'BILLING.SUBSCRIPTION.SUSPENDED',
                           'BILLING.SUBSCRIPTION.EXPIRED',
                           'BILLING.SUBSCRIPTION.PAYMENT.FAILED'):
        desactivar_por_suscripcion(sub_id, tipo.rsplit('.', 1)[-1])

    elif sub_id and tipo in ('BILLING.SUBSCRIPTION.ACTIVATED',
                             'BILLING.SUBSCRIPTION.RE-ACTIVATED'):
        from futbol import db
        fila = db.one('usuarios', 'por suscripcion', suscripcion_id=sub_id)
        if fila:
            db.update('usuarios', {'activo': True, 'suscripcion_estado': 'ACTIVE'},
                      'reactivar', id=fila['id'])

    return Response(status=200)
