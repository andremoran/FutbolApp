# -*- coding: utf-8 -*-
"""
hacer_admin.py — Nombra (o quita) administradores desde la consola.

El primer administrador es el problema del huevo y la gallina: para nombrar a
alguien desde el panel hay que poder entrar al panel. Esto lo resuelve.

    python hacer_admin.py                       # lista quién es administrador
    python hacer_admin.py correo@ejemplo.com    # lo nombra
    python hacer_admin.py correo@ejemplo.com --quitar
"""
import sys

# La consola de Windows viene en cp1252 y se atraganta con los emoji.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import app  # noqa: E402,F401  — configura Supabase al importarse
from futbol import db  # noqa: E402


def listar():
    filas = db.rows('usuarios', 'admins', _order='nombre') or []
    admins = [f for f in filas if f.get('es_admin')]
    print(f'\n{len(admins)} administrador(es) de 3:')
    for a in admins:
        print(f'  🛡️  {a.get("nombre")}  <{a.get("correo")}>')
    if not admins:
        print('  (ninguno)')

    import avisos
    if avisos.ADMIN_EMAILS_ENV:
        print(f'\nArranque en frío desde ADMIN_EMAILS del .env: '
              f'{", ".join(avisos.ADMIN_EMAILS_ENV)}')
        for correo in avisos.ADMIN_EMAILS_ENV:
            if not db.one('usuarios', 'existe', correo=correo):
                print(f'  ⚠️  {correo} NO tiene cuenta en la app: ese correo no '
                      f'puede entrar al panel hasta que se registre.')

    print(f'\n{len(filas)} cuentas en total.')
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    quitar = '--quitar' in sys.argv

    if not args:
        return listar()

    correo = args[0].strip().lower()
    fila = db.one('usuarios', 'buscar', correo=correo)
    if not fila:
        print(f'No hay ninguna cuenta con el correo {correo}.')
        print('Tiene que registrarse primero en la app.')
        return 1

    actuales = [f for f in (db.rows('usuarios', 'admins', es_admin=True) or [])]
    if not quitar and len(actuales) >= 3 and not fila.get('es_admin'):
        print('Ya hay tres administradores. Quita a uno primero:')
        for a in actuales:
            print(f'  python hacer_admin.py {a.get("correo")} --quitar')
        return 1

    db.update('usuarios', {'es_admin': not quitar}, 'admin cli', id=fila['id'])
    from usuarios import olvidar_cache_admins
    olvidar_cache_admins()
    verbo = 'ya NO es' if quitar else 'ahora es'
    print(f'{fila.get("nombre")} <{correo}> {verbo} administrador.')
    if not quitar:
        print('Entra al panel en /admin')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
