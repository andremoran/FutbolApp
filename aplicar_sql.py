# -*- coding: utf-8 -*-
"""
aplicar_sql.py — Ejecuta un .sql contra el Supabase de FutbolApp.

Por qué existe: la clave `service_role` NO puede hacer DDL por PostgREST, y el
string de conexión directo `db.<ref>.supabase.co` es solo IPv6. La vía que sí
funciona desde Windows es la Management API con un Personal Access Token.

    python aplicar_sql.py                 # aplica sql/schema_v2.sql
    python aplicar_sql.py sql/schema.sql  # aplica otro archivo
    python aplicar_sql.py --tablas        # solo lista las tablas que hay
"""
import os
import re
import sys

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

PAT = (os.getenv('SUPABASE_PAT') or '').strip()
URL = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
REF = re.sub(r'^https?://', '', URL).split('.')[0]

API = f'https://api.supabase.com/v1/projects/{REF}/database/query'


def ejecutar(sql: str):
    r = requests.post(API,
                      headers={'Authorization': f'Bearer {PAT}',
                               'Content-Type': 'application/json'},
                      json={'query': sql}, timeout=180)
    if r.status_code >= 400:
        raise RuntimeError(f'HTTP {r.status_code}: {r.text[:900]}')
    try:
        return r.json()
    except ValueError:
        return r.text


def main():
    if not PAT or not REF:
        print('Faltan SUPABASE_PAT / SUPABASE_URL en el .env')
        return 1
    print(f'Proyecto: {REF}')

    if '--tablas' in sys.argv:
        filas = ejecutar("select table_name from information_schema.tables "
                         "where table_schema='public' order by 1")
        nombres = [f['table_name'] for f in filas]
        print(f'{len(nombres)} tablas:')
        for n in nombres:
            print('  ', n)
        return 0

    ruta = next((a for a in sys.argv[1:] if not a.startswith('--')), 'sql/schema_v2.sql')
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)
    with open(ruta, encoding='utf-8') as fh:
        sql = fh.read()

    print(f'Aplicando {os.path.basename(ruta)} ({len(sql):,} caracteres)…')
    try:
        ejecutar(sql)
    except RuntimeError as e:
        print('ERROR:', e)
        return 1
    print('Aplicado.')

    filas = ejecutar("select table_name from information_schema.tables "
                     "where table_schema='public' and table_name like 'fut\\_%' order by 1")
    print(f'Tablas fut_*: {len(filas)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
