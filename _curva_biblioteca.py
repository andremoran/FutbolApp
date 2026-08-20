# -*- coding: utf-8 -*-
"""Fase 2, paso 1 — la curva de escalado MEDIDA SOBRE LA PROPIA BIBLIOTECA.

La Fase 1 midió la curva sobre las 31 pruebas del catálogo web y salió muy
plana entre niveles: un profesional rendía un 1% mejor que un sub-18. Eso no
se sostiene contra los datos de la biblioteca, donde 12 de las 40 pruebas ya
traen baremo real en `test_reference_ranges` y la distancia sub-18 → profesional
va del 6% (T-Test) al 17% (LSPT).

Usar la curva plana para generar las 28 restantes metería un sesgo enorme, así
que la curva se vuelve a medir aquí, sobre esos 12 baremos reales: misma
población de pruebas, mismo eje, y son datos publicados/adaptados, no una
extrapolación de otra tabla.

Eje de la biblioteca (7 contextos, los que usa la app nativa):
    sub_15/juvenil_inicial · sub_17/juvenil · sub_19/juvenil_avanzado
    adulto/{amateur, semipro, profesional, elite}

Se toma `profesional` como referencia porque es el contexto con el corte mejor
documentado en las fuentes originales (Bangsbo, Ali, Haugen).
"""
import io
import json
import statistics

REFERENCIA = 'profesional'
NIVELES = ['juvenil_inicial', 'juvenil', 'juvenil_avanzado',
           'amateur', 'semipro', 'profesional', 'elite']

#  Igual que en la Fase 1: se mide el umbral «bueno» (índice 1), el más
#  estable. El de élite se topa contra el récord y el de débil contra el suelo.
UMBRAL = 1

datos = json.load(io.open('sql/_sb_evaluaciones.json', encoding='utf-8'))
nombre = {t['id']: t['name'] for t in datos['templates']}

#  (test, campo, dirección) → {nivel: [elite, bueno, promedio, debil]}
tablas = {}
for r in datos['ranges']:
    clave = (nombre[r['template_id']], r['field_key'], r['direction'])
    tablas.setdefault(clave, {})[r['competitive_level']] = [
        r['elite_threshold'], r['good_threshold'],
        r['average_threshold'], r['poor_threshold'],
    ]

#  HAY QUE SEPARAR POR DIRECCIÓN, igual que en la Fase 1: en un sprint menos
#  es mejor y en el Yo-Yo más es mejor. Mezclándolos los factores se anulan.
razones = {'menor_mejor': {n: [] for n in NIVELES},
           'mayor_mejor': {n: [] for n in NIVELES}}

for (test, campo, direccion), filas in tablas.items():
    d = 'menor_mejor' if direccion == 'lower_is_better' else 'mayor_mejor'
    base = filas.get(REFERENCIA)
    if not base or not base[UMBRAL]:
        continue
    for niv in NIVELES:
        v = filas.get(niv)
        if v and v[UMBRAL]:
            razones[d][niv].append(v[UMBRAL] / base[UMBRAL])

CURVA = {}
for d in ('menor_mejor', 'mayor_mejor'):
    n_campos = sum(1 for (_, _, dd) in tablas
                   if ('menor_mejor' if dd == 'lower_is_better' else 'mayor_mejor') == d)
    print(f'\n═══ {d.upper().replace("_", " ")}  ({n_campos} campos) ═══')
    print(f'{"NIVEL":20} {"FACTOR":>7} {"DESV":>7} {"CASOS":>6}')
    print('─' * 45)
    for niv in NIVELES:
        r = razones[d][niv]
        if not r:
            continue
        media = statistics.median(r)
        desv = statistics.pstdev(r) if len(r) > 1 else 0
        CURVA[f'{d}|{niv}'] = round(media, 4)
        aviso = '  ← disperso' if desv > 0.08 else ''
        print(f'{niv:20} {media:7.3f} {desv:7.3f} {len(r):6}{aviso}')

print('\n# Comparación con la curva de la Fase 1 (medida sobre las 31 del web):')
print('#   menor_mejor  sub_18→profesional:  Fase 1 = 1.0032 → 0.9933  (−1.0%)')
if 'menor_mejor|juvenil_avanzado' in CURVA:
    ja = CURVA['menor_mejor|juvenil_avanzado']
    print(f'#   menor_mejor  sub_19→profesional:  biblioteca = {ja:.4f} → 1.0000  '
          f'({(1 / ja - 1) * 100:+.1f}%)')

print('\nCURVA =', json.dumps(CURVA, indent=1))
