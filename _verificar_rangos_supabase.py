# -*- coding: utf-8 -*-
"""Comprueba, contra Supabase, que la tabla de rangos quedó como debe.

Se lee de la base, no del JSON que se envió: lo que importa es lo que la app
nativa se va a encontrar al abrir la ficha de una prueba.
"""
import io
import json
import os
import sys

sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

from dotenv import load_dotenv  # noqa: E402

load_dotenv()
from supabase import create_client  # noqa: E402

ORDEN = ['juvenil_inicial', 'juvenil', 'juvenil_avanzado',
         'amateur', 'semipro', 'profesional', 'elite']
#  Las dos escaleras van por separado: la juntura entre un sub-19 de academia y
#  un adulto amateur puede cruzarse con razón.
ESCALERAS = [ORDEN[:3], ORDEN[3:]]
UMBRALES = ['elite_threshold', 'good_threshold', 'average_threshold', 'poor_threshold']

fallos = []
sb = create_client(os.environ['SUPABASE_URL'],
                   os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])

plantillas = sb.table('evaluation_templates').select('id,name,category,fields_schema').execute().data
rangos = sb.table('test_reference_ranges').select('*').execute().data
antes = json.load(io.open('sql/_rangos_antes.json', encoding='utf-8'))

por_plantilla = {}
for r in rangos:
    por_plantilla.setdefault(r['template_id'], []).append(r)

# ─── 1. Las 12 de antes siguen intactas ────────────────────────────────────
ahora = {r['id']: r for r in rangos}
for r in antes:
    actual = ahora.get(r['id'])
    if not actual:
        fallos.append('Se perdió una fila original: %s' % r['id'])
        continue
    for k in UMBRALES + ['field_key', 'direction', 'age_category',
                         'competitive_level', 'source']:
        if actual.get(k) != r.get(k):
            fallos.append('Fila original modificada (%s): %s' % (r['id'], k))

# ─── 2. Las 40 tienen rangos ───────────────────────────────────────────────
sin = [p['name'] for p in plantillas if p['id'] not in por_plantilla]
if sin:
    fallos.append('Sin rangos todavía: %s' % sin)

# ─── 3. Un solo campo por plantilla, y que exista en su fields_schema ──────
for p in plantillas:
    filas = por_plantilla.get(p['id']) or []
    if not filas:
        continue
    campos = {f['field_key'] for f in filas}
    if len(campos) > 1:
        fallos.append('%s: %d campos (el modal los mezclaría en una tabla)'
                      % (p['name'], len(campos)))
    claves = {f.get('key') for f in (p.get('fields_schema') or [])}
    for c in campos:
        if c not in claves:
            fallos.append('%s: el campo «%s» no está en su fields_schema' % (p['name'], c))
    if len({f['direction'] for f in filas}) > 1:
        fallos.append('%s: direcciones distintas en la misma tabla' % p['name'])
    if len({f['source'] for f in filas}) > 1:
        fallos.append('%s: fuentes distintas (el modal enseña la de la 1ª fila)'
                      % p['name'])
    duplicadas = len(filas) - len({(f['age_category'], f['competitive_level']) for f in filas})
    if duplicadas:
        fallos.append('%s: %d contextos repetidos' % (p['name'], duplicadas))

# ─── 4. Sin cruces dentro de cada escalera ─────────────────────────────────
for p in plantillas:
    filas = {f['competitive_level']: f for f in (por_plantilla.get(p['id']) or [])}
    for escalera in ESCALERAS:
        pasos = [filas[n] for n in escalera if n in filas]
        for a, b in zip(pasos, pasos[1:]):
            for k in UMBRALES:
                ok = (a[k] <= b[k] if a['direction'] == 'higher_is_better'
                      else a[k] >= b[k])
                if not ok:
                    fallos.append('%s: %s va al revés entre %s y %s'
                                  % (p['name'], k, a['competitive_level'],
                                     b['competitive_level']))

# ─── 5. Las cuatro bandas de cada fila, en orden y distintas ───────────────
for p in plantillas:
    for f in (por_plantilla.get(p['id']) or []):
        cortes = [f[k] for k in UMBRALES]
        orden = cortes if f['direction'] == 'lower_is_better' else cortes[::-1]
        if list(orden) != sorted(orden):
            fallos.append('%s/%s: las cuatro bandas están desordenadas'
                          % (p['name'], f['competitive_level']))
        if len(set(cortes)) < 4:
            fallos.append('%s/%s: bandas repetidas %s'
                          % (p['name'], f['competitive_level'], cortes))

# ─── Informe ────────────────────────────────────────────────────────────────
from collections import Counter  # noqa: E402
print('Plantillas:            %d' % len(plantillas))
print('Con rangos:            %d' % len(por_plantilla))
print('Filas totales:         %d  (antes %d)' % (len(rangos), len(antes)))
print('Filas por plantilla:   %s'
      % dict(sorted(Counter(len(v) for v in por_plantilla.values()).items())))
print('Campos por plantilla:  %s'
      % sorted({len({f["field_key"] for f in v}) for v in por_plantilla.values()}))
print()
if fallos:
    print('FALLOS (%d):' % len(fallos))
    for f in fallos[:25]:
        print('  ·', f)
    sys.exit(1)
print('Sin fallos. Las 40 pruebas enseñan su tabla de rangos.')
