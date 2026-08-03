# -*- coding: utf-8 -*-
"""
crear_planes_paypal.py — Da de alta los planes de ProFoot en PayPal. Se corre UNA vez.

⚠️  Con PAYPAL_ENV=live esto crea planes de cobro REALES en la cuenta de PayPal
    configurada. Revisa los precios de pagos.PLANES antes de ejecutarlo.

Uso:
    python crear_planes_paypal.py            # muestra qué haría, sin crear nada
    python crear_planes_paypal.py --crear    # lo crea de verdad

Es idempotente: lo ya creado se conserva en planes_paypal.json y no se duplica.
"""
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pagos import API, ARCHIVO_PLANES, PAYPAL_ENV, PLANES, token_paypal, configurado  # noqa: E402

MONEDA = 'USD'


def cargar():
    try:
        with open(ARCHIVO_PLANES, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}


def guardar(datos):
    with open(ARCHIVO_PLANES, 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, indent=2, ensure_ascii=False)


def crear_producto(tok):
    r = requests.post(
        f'{API}/v1/catalogs/products',
        headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'},
        json={
            # Nombre propio: en el panel de PayPal (misma cuenta que la otra
            # plataforma del CEO) el producto "ProFoot Assistant" queda separado.
            'name': 'ProFoot Assistant',
            'description': 'Gestion de equipos y jugadores de futbol',
            'type': 'SERVICE',
            'category': 'SOFTWARE',
        }, timeout=30)
    r.raise_for_status()
    return r.json()['id']


def crear_plan(tok, producto_id, clave, meta):
    r = requests.post(
        f'{API}/v1/billing/plans',
        headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'},
        json={
            'product_id': producto_id,
            'name': f"ProFoot {meta['nombre']}",
            'description': meta['descripcion'][:127],
            'status': 'ACTIVE',
            'billing_cycles': [{
                'frequency': {'interval_unit': 'MONTH', 'interval_count': 1},
                'tenure_type': 'REGULAR',
                'sequence': 1,
                'total_cycles': 0,                       # indefinido
                'pricing_scheme': {'fixed_price': {'value': meta['precio'],
                                                   'currency_code': MONEDA}},
            }],
            'payment_preferences': {
                'auto_bill_outstanding': True,
                'setup_fee_failure_action': 'CONTINUE',
                'payment_failure_threshold': 2,
            },
        }, timeout=30)
    r.raise_for_status()
    return r.json()['id']


def main():
    de_verdad = '--crear' in sys.argv

    if not configurado():
        print('Faltan PAYPAL_CLIENT_ID / PAYPAL_SECRET en el .env.')
        return 1

    datos = cargar()
    entorno = datos.setdefault(PAYPAL_ENV, {})
    producto_id = datos.get(f'{PAYPAL_ENV}_producto')

    print(f'Entorno PayPal: {PAYPAL_ENV.upper()}   ({API})')
    print(f'Producto existente: {producto_id or "ninguno"}')
    print()
    pendientes = [(k, v) for k, v in PLANES.items() if k not in entorno]
    for clave, meta in PLANES.items():
        estado = entorno.get(clave, 'POR CREAR')
        print(f"  {meta['nombre']:18} ${meta['precio']:>6}/mes   {estado}")

    if not pendientes:
        print('\nTodo creado. No hay nada que hacer.')
        return 0

    if not de_verdad:
        print(f'\n{len(pendientes)} plan(es) por crear.')
        print('Esto es solo una vista previa. Para crearlos de verdad:')
        print('    python crear_planes_paypal.py --crear')
        if PAYPAL_ENV == 'live':
            print('\n⚠️  PAYPAL_ENV=live: se crearan planes de cobro REALES.')
        return 0

    tok = token_paypal()
    if not producto_id:
        producto_id = crear_producto(tok)
        datos[f'{PAYPAL_ENV}_producto'] = producto_id
        guardar(datos)
        print(f'\nProducto creado: {producto_id}')

    for clave, meta in pendientes:
        plan_id = crear_plan(tok, producto_id, clave, meta)
        entorno[clave] = plan_id
        guardar(datos)
        print(f"  creado {meta['nombre']}: {plan_id}")

    print(f'\nListo. IDs guardados en {ARCHIVO_PLANES}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
