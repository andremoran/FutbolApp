# -*- coding: utf-8 -*-
"""
configurar_pagos.py — Deja los ajustes de cobro listos en la base.

Escribe en `fut_settings` lo que el panel deja editar a mano, para no tener que
teclearlo la primera vez. Los datos de DeUna son los MISMOS que usa
ElectroBiomed: el QR es el mismo archivo y el número el mismo.

    python configurar_pagos.py            # muestra lo que hay
    python configurar_pagos.py --aplicar  # lo escribe
"""
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import app  # noqa: E402,F401  — configura Supabase al importarse
from admin import ajustes, guardar_ajustes  # noqa: E402

# Los mismos datos de cobro de ElectroBiomed. El QR se copió de
# Version49/static/images/de_una_qr.jpg a FutbolApp/static/de_una_qr.jpg.
DEUNA = {
    'deuna_activo': True,
    'deuna_qr': '/static/de_una_qr.jpg',
    'deuna_telefono': '0987553634',
    'deuna_banco': 'DeUna · Banco Pichincha',
    'deuna_instrucciones': (
        'Abre la app DeUna, escanea el código y envía el importe exacto. '
        'Luego sube aquí la captura del comprobante: en cuanto lo verifiquemos '
        'se activa tu cuenta. Si prefieres, también puedes mandárnoslo por '
        'WhatsApp al 098 755 3634.'),
    # Titular y cédula se dejan vacíos a propósito: el nombre que se enseña
    # tiene que coincidir LETRA POR LETRA con el de la cuenta del banco, y
    # ponerlo a ojo genera transferencias devueltas. Se rellenan desde
    # /admin/ajustes. La transferencia funciona igual: va por el QR.
}

PRECIOS = {
    'precio_jugador': '4.99',
    'precio_entrenador': '14.99',
    # El de Club es un precio DE PARTIDA («desde»), no una tarifa: cada club
    # se cotiza según categorías y personalización. No hay botón de pago para
    # él, así que este número solo ancla la conversación.
    'precio_club': '199',
}

CONTACTO = {
    'contacto_whatsapp': '0987553634',
    'contacto_correo': '',
}


def main():
    actual = ajustes()
    nuevos = {**DEUNA, **PRECIOS, **CONTACTO}

    print('Ajustes de cobro')
    print('─' * 60)
    for k, v in nuevos.items():
        antes = actual.get(k)
        marca = '  =' if str(antes) == str(v) else '  →'
        print(f'  {k:22} {str(antes)[:28]:30}{marca} {str(v)[:40]}')

    if '--aplicar' not in sys.argv:
        print('\nVista previa. Para escribirlo:  python configurar_pagos.py --aplicar')
        return 0

    guardar_ajustes(nuevos)
    print('\nEscrito en fut_settings.')

    import pagos
    print(f'\nTarjeta (PayPal): entorno {pagos.PAYPAL_ENV.upper()}')
    ids = pagos.ids_planes()
    if ids:
        for k, v in ids.items():
            print(f'   {k}: {v}')
    else:
        print('   sin planes dados de alta en este entorno')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
