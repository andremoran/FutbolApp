# -*- coding: utf-8 -*-
"""
pagos.py — Cobrar en FutbolApp: tarjeta (PayPal) y transferencia (DeUna).

Dos vías porque el público es de Ecuador y no todo el mundo tiene tarjeta:

  TARJETA · PayPal Subscriptions
    Cobra con tarjeta sin que el usuario necesite cuenta de PayPal, y el
    número nunca pasa por nuestro servidor: lo captura el SDK de PayPal.
    Nosotros verificamos la suscripción contra su API y activamos. Es
    automático y se renueva solo, pero PayPal se queda una comisión.

  TRANSFERENCIA · DeUna
    El usuario paga desde su banco al número de la cuenta y sube el
    comprobante. No hay comisión, pero un administrador tiene que mirarlo:
    hasta que lo apruebe, la cuenta NO se activa. Nunca se activa sola con
    lo que diga el navegador.

Los Billing Plans de PayPal se crean UNA vez con `python crear_planes_paypal.py`;
sus IDs quedan en planes_paypal.json.
"""
import json
import logging
import os
from datetime import datetime, timezone

import requests
from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import avisos
import suscripciones as subs

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
    """Marca la cuenta como Pro, guarda el comprobante y avisa a los admins."""
    from futbol import db

    meta = PLANES.get(plan_clave, {})
    subs.activar(user_id, meses=1, origen='paypal', plan=plan_clave,
                 suscripcion_id=sub.get('id'), estado=sub.get('status'))
    db.insert('fut_pagos', {
        'user_id': user_id,
        'plan': plan_clave,
        'suscripcion_id': sub.get('id'),
        'estado': sub.get('status'),
        'proveedor': 'paypal',
        'importe': meta.get('precio'),
        'moneda': 'USD',
        'meses': 1,
        'referencia': sub.get('id'),
        'bruto': json.dumps(sub)[:8000],
        'creado': _ahora(),
    }, 'registro pago')

    usuario = db.one('usuarios', 'pagador', id=user_id) or {}
    avisos.aviso_pago(
        type('U', (), {'name': usuario.get('nombre', '?'),
                       'correo': usuario.get('correo', ''), 'id': user_id})(),
        meta.get('nombre', plan_clave), meta.get('precio', ''), 'PayPal (tarjeta)',
        sub.get('id', ''))
    logger.info('Cuenta %s activada con %s (%s)', user_id, plan_clave, sub.get('id'))


def desactivar_por_suscripcion(sub_id, estado):
    from futbol import db
    fila = db.one('usuarios', 'por suscripcion', suscripcion_id=sub_id)
    if not fila:
        return
    subs.desactivar(fila['id'], estado)
    avisos.aviso_baja(fila, estado)
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


# ═══════════════════════ DEUNA (transferencia) ═══════════════════════
def deuna_disponible():
    """DeUna solo se ofrece si el administrador puso los datos de la cuenta."""
    from admin import ajustes
    cfg = ajustes()
    return bool(cfg.get('deuna_activo')
                and (cfg.get('deuna_telefono') or cfg.get('deuna_qr'))), cfg


@bp.route('/deuna/<plan>')
@login_required
def deuna(plan):
    meta = PLANES.get(plan)
    if not meta:
        flash('Ese plan no existe.', 'error')
        return redirect(url_for('futbol.planes'))

    activo, cfg = deuna_disponible()
    if not activo:
        flash('El pago por transferencia todavía no está disponible. '
              'Puedes pagar con tarjeta.', 'warning')
        return redirect(url_for('futbol.planes'))

    from futbol import db
    precio = {'jugador_pro': cfg.get('precio_jugador'),
              'entrenador_pro': cfg.get('precio_entrenador'),
              'club': cfg.get('precio_club')}.get(plan) or meta['precio']

    pendiente = None
    for p in (db.rows('fut_pagos', 'pendiente deuna', user_id=current_user.id,
                      _order='creado', _desc=True, _limit=5) or []):
        if (p.get('estado') or '').lower() == 'pendiente':
            pendiente = p
            pendiente['_fecha'] = db.parse_fecha(p.get('creado'))
            break

    return render_template('pago_deuna.html',
                           hide_tabbar=True,
                           plan=plan, meta=meta, precio=precio,
                           cfg=cfg, pendiente=pendiente)


@bp.route('/api/deuna', methods=['POST'])
@login_required
def api_deuna():
    """Registra el comprobante. NO activa: eso lo hace un administrador.

    Es la diferencia entera con la tarjeta. Aquí lo único que se sabe es que
    alguien dice haber pagado; hasta que un humano mire el movimiento, la
    cuenta sigue en el plan gratuito.
    """
    from app import csrf_ok
    from futbol import db

    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400

    activo, cfg = deuna_disponible()
    if not activo:
        return jsonify({'error': 'El pago por transferencia no está disponible.'}), 400

    d = request.get_json(silent=True) or {}
    plan = (d.get('plan') or '').strip()
    meta = PLANES.get(plan)
    if not meta:
        return jsonify({'error': 'Ese plan no existe.'}), 400

    referencia = (d.get('referencia') or '').strip()
    comprobante = (d.get('comprobante') or '').strip()
    if not referencia and not comprobante:
        return jsonify({'error': 'Pon el número del comprobante o sube la captura.'}), 400

    ya = [p for p in (db.rows('fut_pagos', 'pendientes', user_id=current_user.id) or [])
          if (p.get('estado') or '').lower() == 'pendiente']
    if ya:
        return jsonify({'error': 'Ya tienes un comprobante esperando revisión. '
                                 'Te avisaremos en cuanto lo verifiquemos.'}), 400

    precio = {'jugador_pro': cfg.get('precio_jugador'),
              'entrenador_pro': cfg.get('precio_entrenador'),
              'club': cfg.get('precio_club')}.get(plan) or meta['precio']
    meses = max(1, min(24, int(d.get('meses') or 1)))

    fila = db.insert('fut_pagos', {
        'user_id': current_user.id,
        'plan': plan,
        'estado': 'pendiente',
        'proveedor': 'deuna',
        'importe': str(precio),
        'moneda': 'USD',
        'meses': meses,
        'referencia': referencia[:80],
        # La imagen se guarda como data URI: sin bucket que configurar ni
        # permisos que revisar, y el comprobante rara vez pasa de 200 kB.
        'comprobante': comprobante[:600000],
        'creado': _ahora(),
    }, 'pago deuna')

    if not fila:
        return jsonify({'error': 'No se pudo registrar el comprobante.'}), 500

    avisos.aviso_deuna_pendiente(current_user, meta['nombre'], precio, referencia)
    return jsonify({'ok': True,
                    'mensaje': 'Comprobante recibido. Lo revisamos y activamos '
                               'tu cuenta; suele tardar unas horas.',
                    'redirect': url_for('pagos.listo', pendiente=1)})


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
