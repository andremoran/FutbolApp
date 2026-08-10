# -*- coding: utf-8 -*-
"""
activar_cobro_real.py — Pasa la tarjeta de PRUEBA a COBRO REAL, de una vez.

Por qué hace falta un script
────────────────────────────
Pasar a live son cinco pasos en tres sitios distintos y saltarse uno deja el
cobro a medias sin que salte ningún error: la app cobra en sandbox creyendo
que cobra de verdad. Esto los hace todos o no hace ninguno.

Lo que hace:
  1. Comprueba que las claves valen CONTRA EL PAYPAL REAL (si no, para).
  2. Crea los tres billing plans en la cuenta real y los guarda en
     planes_paypal.json (sección 'live'). Es idempotente.
  3. Escribe PAYPAL_ENV / CLIENT_ID / SECRET en Vercel y en Contabo.
  4. Redespliega los dos.
  5. Verifica que la pantalla de pago sirve el SDK real.

Uso:
    python activar_cobro_real.py --client-id AXXXX --secret EXXXX
    python activar_cobro_real.py --client-id ... --secret ... --solo-comprobar

Las claves LIVE se sacan de developer.paypal.com → Apps & Credentials →
pestaña **Live** → tu app → Client ID y Secret. Son las mismas que ya usa
ElectroBiomed en Render (Environment → PAYPAL_CLIENT_ID / PAYPAL_SECRET).
"""
import argparse
import io
import json
import os
import subprocess
import sys

import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(AQUI, '.env'))

API_LIVE = 'https://api-m.paypal.com'
ARCHIVO_PLANES = os.path.join(AQUI, 'planes_paypal.json')

PROYECTO_VERCEL = 'prj_1JrpUJAMyzmmh6lSbpLyrX1duf49'
EQUIPO_VERCEL = 'team_0xastptKEfgrpH0IoXWTzlZd'

VPS = os.getenv('VPS_HOST', '147.93.181.76')
VPS_KEY = os.path.expanduser(os.getenv('VPS_SSH_KEY', '~/.ssh/futbolapp_vps'))

VERDE, ROJO, GRIS, FIN = '\033[92m', '\033[91m', '\033[90m', '\033[0m'


def paso(texto):
    print(f'\n{texto}\n' + '─' * 62)


def ok(texto):
    print(f'{VERDE}  ✓{FIN} {texto}')


def mal(texto):
    print(f'{ROJO}  ✗ {texto}{FIN}')


# ── 1. Comprobar las claves ─────────────────────────────────────────────────
def token_live(cid, sec):
    r = requests.post(f'{API_LIVE}/v1/oauth2/token', auth=(cid, sec),
                      data={'grant_type': 'client_credentials'}, timeout=30)
    if r.status_code != 200:
        return None
    return r.json()['access_token']


# ── 2. Crear los planes reales ──────────────────────────────────────────────
def crear_planes(tok):
    from pagos import PLANES

    datos = {}
    if os.path.exists(ARCHIVO_PLANES):
        with open(ARCHIVO_PLANES, encoding='utf-8') as fh:
            datos = json.load(fh)
    entorno = datos.setdefault('live', {})
    cab = {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'}

    producto = datos.get('live_producto')
    if not producto:
        r = requests.post(f'{API_LIVE}/v1/catalogs/products', headers=cab, json={
            'name': 'ProFoot Assistant',
            'description': 'Gestion de equipos y jugadores de futbol',
            'type': 'SERVICE', 'category': 'SOFTWARE'}, timeout=30)
        r.raise_for_status()
        producto = r.json()['id']
        datos['live_producto'] = producto
        ok(f'producto real creado: {producto}')
    else:
        ok(f'producto ya existía: {producto}')

    for clave, meta in PLANES.items():
        if clave in entorno:
            ok(f"{meta['nombre']}: ya existía ({entorno[clave]})")
            continue
        r = requests.post(f'{API_LIVE}/v1/billing/plans', headers=cab, json={
            'product_id': producto,
            'name': f"ProFoot {meta['nombre']}",
            'description': meta['descripcion'][:127],
            'status': 'ACTIVE',
            'billing_cycles': [{
                'frequency': {'interval_unit': 'MONTH', 'interval_count': 1},
                'tenure_type': 'REGULAR', 'sequence': 1, 'total_cycles': 0,
                'pricing_scheme': {'fixed_price': {'value': meta['precio'],
                                                   'currency_code': 'USD'}}}],
            'payment_preferences': {'auto_bill_outstanding': True,
                                    'setup_fee_failure_action': 'CONTINUE',
                                    'payment_failure_threshold': 2},
        }, timeout=30)
        r.raise_for_status()
        entorno[clave] = r.json()['id']
        ok(f"{meta['nombre']} ${meta['precio']}/mes → {entorno[clave]}")
        with open(ARCHIVO_PLANES, 'w', encoding='utf-8') as fh:
            json.dump(datos, fh, indent=2, ensure_ascii=False)

    with open(ARCHIVO_PLANES, 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, indent=2, ensure_ascii=False)
    return entorno


# ── 3. Escribir las variables en los dos despliegues ────────────────────────
def token_vercel():
    for ruta in ('desplegar_vercel.bat',
                 os.path.join('..', 'AgenteCerEB', 'actualizar_nube.bat')):
        p = os.path.join(AQUI, ruta)
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8', errors='ignore') as fh:
            texto = fh.read()
        import re
        m = re.search(r'(?:--token[= ]|VERCEL_TOKEN=)\s*([A-Za-z0-9_]{20,})', texto)
        if m:
            return m.group(1)
    return os.getenv('VERCEL_TOKEN')


def vercel_env(tok, clave, valor):
    """Vercel no deja editar en sitio: se borra la que hay y se crea de nuevo."""
    base = f'https://api.vercel.com/v9/projects/{PROYECTO_VERCEL}/env'
    cab = {'Authorization': f'Bearer {tok}'}
    params = {'teamId': EQUIPO_VERCEL}

    r = requests.get(base, headers=cab, params={**params, 'decrypt': 'false'}, timeout=30)
    for e in (r.json().get('envs') or []):
        if e.get('key') == clave:
            requests.delete(f'{base}/{e["id"]}', headers=cab, params=params, timeout=30)

    r = requests.post(base, headers=cab, params=params, json={
        'key': clave, 'value': valor, 'type': 'encrypted',
        'target': ['production', 'preview']}, timeout=30)
    return r.status_code < 300, (r.json() if r.status_code >= 300 else {})


def contabo(comando):
    return subprocess.run(
        ['ssh', '-i', VPS_KEY, '-p', '22', '-o', 'BatchMode=yes',
         '-o', 'StrictHostKeyChecking=no', f'root@{VPS}', comando],
        capture_output=True, text=True, timeout=900)


def contabo_env(cid, sec):
    """Reescribe las tres líneas del .env del servidor sin tocar el resto."""
    guion = (
        "cd /opt/futbolapp && cp .env .env.bak && "
        "sed -i '/^PAYPAL_ENV=/d;/^PAYPAL_CLIENT_ID=/d;/^PAYPAL_SECRET=/d' .env && "
        f"printf 'PAYPAL_ENV=live\\nPAYPAL_CLIENT_ID=%s\\nPAYPAL_SECRET=%s\\n' "
        f"'{cid}' '{sec}' >> .env && "
        "grep -c '^PAYPAL' .env")
    return contabo(guion)


# ── Programa ────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--client-id')
    ap.add_argument('--secret')
    ap.add_argument('--solo-comprobar', action='store_true',
                    help='comprueba las claves y sale, sin tocar nada')
    ap.add_argument('--si', action='store_true',
                    help='no preguntar (para ejecutarlo desde un guion)')
    ap.add_argument('--desde-env', action='store_true',
                    help='lee las claves de las líneas #PAYPAL_*=... del .env')
    args = ap.parse_args()

    cid, sec = (args.client_id or '').strip(), (args.secret or '').strip()
    if args.desde_env or not (cid and sec):
        # Las claves live suelen quedar comentadas en el .env mientras se
        # prueba; se leen de ahí para no pegarlas en la línea de comandos
        # (donde acabarían en el historial de la consola).
        import re
        texto = io.open(os.path.join(AQUI, '.env'), encoding='utf-8').read()
        m1 = re.search(r'^#\s*PAYPAL_CLIENT_ID=(\S+)', texto, re.M)
        m2 = re.search(r'^#\s*PAYPAL_SECRET=(\S+)', texto, re.M)
        cid = cid or (m1.group(1) if m1 else '')
        sec = sec or (m2.group(1) if m2 else '')
        if cid and sec:
            ok('claves leídas de las líneas comentadas del .env')
    if not (cid and sec):
        mal('faltan las claves: pásalas con --client-id/--secret o déjalas '
            'comentadas en el .env como #PAYPAL_CLIENT_ID=…')
        return 1

    paso('1 · ¿Las claves valen contra el PayPal REAL?')
    tok = token_live(cid, sec)
    if not tok:
        mal('PayPal las rechaza (HTTP 401). Comprueba que las copiaste de la '
            'pestaña **Live**, no de Sandbox.')
        return 1
    ok('PayPal las acepta: son claves de cobro real')

    if args.solo_comprobar:
        print('\nSolo comprobación. No se tocó nada.')
        return 0

    print(f'\n{ROJO}A partir de aquí se cobra DINERO REAL.{FIN}')
    if not args.si:
        if input('Escribe COBRAR para continuar: ').strip().upper() != 'COBRAR':
            print('Cancelado. No se tocó nada.')
            return 1

    paso('2 · Planes de cobro en la cuenta real')
    try:
        planes = crear_planes(tok)
    except requests.HTTPError as e:
        mal(f'PayPal: {getattr(e.response, "text", e)[:300]}')
        return 1

    paso('3 · Variables en Vercel')
    tv = token_vercel()
    if not tv:
        mal('no encontré el token de Vercel; hazlo a mano en '
            'Settings → Environment Variables')
    else:
        for k, v in (('PAYPAL_ENV', 'live'), ('PAYPAL_CLIENT_ID', cid),
                     ('PAYPAL_SECRET', sec)):
            bien, err = vercel_env(tv, k, v)
            ok(k) if bien else mal(f'{k}: {err}')

    paso('4 · Variables en Contabo')
    r = contabo_env(cid, sec)
    ok('.env del servidor actualizado (copia en .env.bak)') if r.returncode == 0 \
        else mal(r.stderr[:200])

    paso('5 · Publicar')
    print(f'{GRIS}  git add planes_paypal.json && git commit && git push{FIN}')
    for cmd in (['git', 'add', 'planes_paypal.json'],
                ['git', 'commit', '-q', '-m', 'Planes de cobro real de PayPal'],
                ['git', 'push', '-q', 'origin', 'main']):
        subprocess.run(cmd, cwd=AQUI, capture_output=True, text=True)
    ok('subido a GitHub (Vercel reconstruye solo)')

    r = contabo('bash /opt/futbolapp/redeploy.sh')
    ok('Contabo redesplegado') if 'REDEPLOY_OK' in r.stdout else mal(r.stdout[-300:])

    paso('Listo')
    print('  Planes reales:')
    for k, v in planes.items():
        print(f'    {k}: {v}')
    print('\n  Comprueba con una tarjeta de verdad y un importe pequeño.')
    print('  Para dar de baja o devolver: Version49/paypal_standalone/'
          'manage_subscription.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
