"""Fase 1 — ¿cómo escalan los baremos entre niveles y edades?

Las 31 pruebas del catálogo tienen baremos con fuente (Haugen, Bangsbo,
Buchheit...). Cada una define, para el mismo campo, los cuatro umbrales en
once contextos: cuatro niveles competitivos y siete categorías de edad.

Si se mide cuánto se aparta cada contexto del de referencia —y sale parecido
en las 31— entonces esa proporción no es una invención: es la forma que tiene
el rendimiento de escalar con la edad y el nivel, medida sobre datos ya
publicados. Con ella se pueden generar baremos coherentes para las pruebas
nuevas anclándolos en su valor normativo, en vez de inventar once filas.
"""
import statistics
import sys

sys.path.insert(0, r"C:\MisApps\FutbolAppWeb")

from futbol import tests_catalogo as cat  # noqa: E402

REFERENCIA = ('general', 'general')
CONTEXTOS = [
    ('general', 'elite'), ('general', 'profesional'),
    ('general', 'semipro'), ('general', 'amateur'),
    ('sub_18', 'general'), ('sub_17', 'general'), ('sub_16', 'general'),
    ('sub_15', 'general'), ('sub_14', 'general'), ('sub_12', 'general'),
]

#  Se mide el umbral «bueno» (el segundo), que es el más estable: el de élite
#  se topa contra el récord y el de débil contra el suelo.
UMBRAL = 1

#  HAY QUE SEPARAR POR DIRECCIÓN. En un sprint menos es mejor: un sub-12 tarda
#  MÁS, factor > 1. En el Yo-Yo más es mejor: un sub-12 corre MENOS, factor < 1.
#  Metiéndolos en el mismo saco se anulan y todo sale pegado a 1.0, que fue lo
#  que pasó en el primer intento.
razones = {'menor_mejor': {c: [] for c in CONTEXTOS},
           'mayor_mejor': {c: [] for c in CONTEXTOS}}
n_campos = {'menor_mejor': 0, 'mayor_mejor': 0}

for clave, test in cat.CATALOGO.items():
    direcciones = {c['clave']: c.get('direccion', 'mayor_mejor')
                   for c in (test.get('campos') or [])}
    for campo, contextos in (test.get('baremos') or {}).items():
        d = direcciones.get(campo, 'mayor_mejor')
        base = contextos.get(REFERENCIA)
        if not base or len(base) <= UMBRAL or not base[UMBRAL]:
            continue
        n_campos[d] += 1
        for ctx in CONTEXTOS:
            v = contextos.get(ctx)
            if v and len(v) > UMBRAL and v[UMBRAL]:
                razones[d][ctx].append(v[UMBRAL] / base[UMBRAL])

FACTORES = {}
for d in ('menor_mejor', 'mayor_mejor'):
    print(f'\n═══ {d.upper().replace("_", " ")}  ({n_campos[d]} campos) ═══')
    print(f'{"CONTEXTO":26} {"FACTOR":>7} {"DESV":>7} {"CASOS":>6}')
    print('─' * 50)
    for ctx in CONTEXTOS:
        r = razones[d][ctx]
        if not r:
            continue
        media = statistics.median(r)
        desv = statistics.pstdev(r) if len(r) > 1 else 0
        FACTORES[f'{d}|{ctx[0]}|{ctx[1]}'] = round(media, 4)
        aviso = '  ← disperso' if desv > 0.08 else ''
        print(f'{str(ctx):26} {media:7.3f} {desv:7.3f} {len(r):6}{aviso}')

print('\n# Para la Fase 2:')
print('FACTORES =', FACTORES)
