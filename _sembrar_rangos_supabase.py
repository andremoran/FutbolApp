# -*- coding: utf-8 -*-
"""Rellena `test_reference_ranges` para las 28 pruebas que hoy la tienen vacía.

QUÉ ARREGLA
───────────
La app nativa pinta «RANGOS ESPERADOS POR NIVEL» leyendo esa tabla. Hoy solo
12 de las 40 pruebas de la biblioteca tienen filas, así que las otras 28 abren
su ficha con la tabla en blanco. Los números ya están calculados en el catálogo
del web (`futbol/tests_catalogo.py`); esto los traduce al eje de la app y los
inserta.

DOS LÍMITES QUE IMPONE EL LECTOR, NO ESTE SCRIPT
────────────────────────────────────────────────
`components/TestDetailModal.tsx` se trae TODAS las filas de la plantilla
(`.eq('template_id', ...)`, sin filtrar por `field_key`) y las pinta en UNA
tabla, tomando además la dirección de `ranges[0]`. Por eso:

  1. Se escribe **un solo campo por prueba**, el principal. Meter también los
     secundarios pintaría 14 o 21 filas mezclando magnitudes distintas —metros
     con segundos— bajo un único «cuanto más alto, mejor». Las 12 que ya
     existían están hechas así: un campo, siete filas.
  2. Las siete filas llevan el **mismo `source`**, porque el modal enseña el de
     `ranges[0]` y sería una lotería cuál sale.

HONESTIDAD DE LA FUENTE
───────────────────────
El `source` se le muestra al entrenador debajo de la tabla. Se cita el estudio
publicado y se dice a continuación que los cortes por edad y nivel están
derivados: son valores generados, no medidos, y el entrenador tiene derecho a
saberlo antes de enseñarle un percentil al padre de un chaval.

USO
───
    .venv\\Scripts\\python.exe _sembrar_rangos_supabase.py            # simula
    .venv\\Scripts\\python.exe _sembrar_rangos_supabase.py --aplicar  # escribe
"""
import io
import json
import os
import sys

sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

from dotenv import load_dotenv  # noqa: E402

from futbol import tests_catalogo as cat  # noqa: E402

load_dotenv()
from supabase import create_client  # noqa: E402

APLICAR = '--aplicar' in sys.argv

#  Del eje del catálogo web (11 contextos) al de la app (7). Es el inverso del
#  MAPA_REAL con el que se generaron los baremos.
CONTEXTOS = [
    (('sub_15', 'general'),      'sub_15', 'juvenil_inicial'),
    (('sub_17', 'general'),      'sub_17', 'juvenil'),
    (('sub_18', 'general'),      'sub_19', 'juvenil_avanzado'),
    (('general', 'amateur'),     'adulto', 'amateur'),
    (('general', 'semipro'),     'adulto', 'semipro'),
    (('general', 'profesional'), 'adulto', 'profesional'),
    (('general', 'elite'),       'adulto', 'elite'),
]

#  Las 27 nuevas se dieron de alta con las claves de campo de la propia app, así
#  que no hace falta traducirlas. Estas cinco son de las que ya existían en el
#  catálogo web desde antes, con sus nombres viejos.
CAMPO_EN_LA_APP = {
    'illinois':  {'time_seconds': 'time_s'},
    'vo2max':    {'vo2': 'vo2max'},
    'test_505':  {'right': 'time_dom'},
}


#  Las 27 de la biblioteca traen los once contextos porque los generó
#  `_baremos_40.py`. Pero cinco de las 28 a rellenar son pruebas que ya estaban
#  en el catálogo web desde antes, y a esas les faltan entre uno y tres de los
#  siete que usa la app.
#
#  NO se inventan. Se probó a interpolarlos y salió mal: en esas cinco las filas
#  por edad y las filas por nivel del catálogo viejo no son consistentes entre
#  sí —el VO₂max le pide 60 a un sub-17 y 58 a un semiprofesional—, así que
#  interpolarlas en un mismo espacio dejaba al sub-19 por debajo del sub-17.
#  Se siembra solo lo que el catálogo define de verdad: la tabla de la app sale
#  con cuatro o cinco filas en vez de siete, y todas ciertas. El modal recorre
#  las que haya, y `getReferenceRange` ya cae hacia atrás cuando falta una.
MINIMO_FILAS = 4


def fuente_visible(t):
    """Lo que el entrenador lee debajo de la tabla.

    No se le puede colgar al estudio original una estratificación que no
    publicó, así que se cita la fuente y se dice a continuación de dónde sale
    el reparto por edad y nivel.
    """
    cita = (t.get('fuente') or '').strip().rstrip('.')
    if not cita:
        cita = 'Sin fuente publicada'
    return cita + ' · Estratificación por edad y nivel del catálogo ProFoot (ago 2026)'


NOTA = ('Sembrado desde futbol/tests_catalogo.py por _sembrar_rangos_supabase.py '
        '(ago 2026). Un solo campo por plantilla: el modal de la app pinta en una '
        'misma tabla todas las filas de la plantilla, sin filtrar por field_key.')


def main():
    sb = create_client(os.environ['SUPABASE_URL'],
                       os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])

    plantillas = sb.table('evaluation_templates').select(
        'id,name,category,fields_schema').execute().data
    por_nombre = {p['name']: p for p in plantillas}
    existentes = sb.table('test_reference_ranges').select('*').execute().data

    #  Copia de seguridad ANTES de tocar nada.
    io.open('sql/_rangos_antes.json', 'w', encoding='utf-8').write(
        json.dumps(existentes, ensure_ascii=False, indent=1))
    print('Copia de las %d filas actuales → sql/_rangos_antes.json\n' % len(existentes))

    con_rangos = {r['template_id'] for r in existentes}

    #  clave del catálogo web → nombre de la plantilla en la app.
    import _baremos_40 as g
    mapa = dict(g.DUPLICADOS)
    for clave, spec in g.NUEVAS.items():
        mapa[clave] = spec['plantilla']

    filas, saltadas, problemas, parciales = [], [], [], []

    for clave, nombre in sorted(mapa.items(), key=lambda kv: kv[1]):
        p = por_nombre.get(nombre)
        if not p:
            problemas.append('%s: no existe la plantilla «%s»' % (clave, nombre))
            continue
        if p['id'] in con_rangos:
            saltadas.append(nombre)
            continue

        t = cat.CATALOGO[clave]
        campo = cat.campo_principal(t)
        if not campo:
            problemas.append('%s: sin campo principal' % clave)
            continue

        tabla = (t.get('baremos') or {}).get(campo['clave'])
        if not tabla:
            problemas.append('%s: el campo principal (%s) no tiene baremo'
                             % (clave, campo['clave']))
            continue

        destino = CAMPO_EN_LA_APP.get(clave, {}).get(campo['clave'], campo['clave'])
        claves_app = {f.get('key') for f in (p.get('fields_schema') or [])}
        if destino not in claves_app:
            problemas.append('%s: el campo «%s» no existe en la app (tiene %s)'
                             % (clave, destino, sorted(claves_app)))
            continue

        dir_cat = cat.direccion_de(clave, campo['clave'])
        direccion = 'lower_is_better' if dir_cat == cat.MENOR else 'higher_is_better'
        fuente = fuente_visible(t)

        propias = [c for c in CONTEXTOS if tabla.get(c[0])]
        if len(propias) < MINIMO_FILAS:
            problemas.append('%s: solo define %d de los 7 contextos'
                             % (clave, len(propias)))
            continue
        if len(propias) < len(CONTEXTOS):
            parciales.append((nombre, len(propias),
                              [c[2] for c in CONTEXTOS if not tabla.get(c[0])]))

        for ctx_web, edad_app, nivel_app in propias:
            cortes = tabla[ctx_web]
            filas.append({
                'template_id': p['id'], 'age_category': edad_app,
                'competitive_level': nivel_app, 'gender': 'mixed',
                'position_group': None, 'field_key': destino,
                'direction': direccion,
                'elite_threshold': float(cortes[0]), 'good_threshold': float(cortes[1]),
                'average_threshold': float(cortes[2]), 'poor_threshold': float(cortes[3]),
                'source': fuente, 'notes': NOTA,
            })

    # ─── Informe ────────────────────────────────────────────────────────────
    plantillas_nuevas = sorted({f['template_id'] for f in filas})
    nombre_de = {p['id']: p['name'] for p in plantillas}
    print('Ya tenían rangos y NO se tocan: %d' % len(saltadas))
    for n in sorted(saltadas):
        print('   ·', n)
    print()
    print('Se van a rellenar: %d pruebas × 7 filas = %d filas'
          % (len(plantillas_nuevas), len(filas)))
    vistos = set()
    for f in filas:
        if f['template_id'] in vistos:
            continue
        vistos.add(f['template_id'])
        print('   %-46s %-16s %s' % (nombre_de[f['template_id']][:46],
                                     f['field_key'], f['direction']))

    if parciales:
        print('\nCon menos de 7 filas, porque el catálogo no define más '
              '(no se inventan):')
        for nombre, n, faltan in parciales:
            print('   %-46s %d filas · faltan %s' % (nombre[:46], n, ', '.join(faltan)))

    #  Las dos escaleras se comprueban POR SEPARADO. Encadenadas darían falsos
    #  positivos en la juntura: un sub-19 de academia rinde más que un adulto
    #  amateur, y los baremos ya publicados tienen esa misma forma.
    ESCALERAS = [['juvenil_inicial', 'juvenil', 'juvenil_avanzado'],
                 ['amateur', 'semipro', 'profesional', 'elite']]
    UMBRALES = ['elite_threshold', 'good_threshold',
                'average_threshold', 'poor_threshold']
    por_plantilla = {}
    for f in filas:
        por_plantilla.setdefault(f['template_id'], {})[f['competitive_level']] = f

    for tid, niveles in por_plantilla.items():
        for escalera in ESCALERAS:
            pasos = [niveles[n] for n in escalera if n in niveles]
            for a, b in zip(pasos, pasos[1:]):
                for k in UMBRALES:
                    peor = (a[k] <= b[k] if a['direction'] == 'higher_is_better'
                            else a[k] >= b[k])
                    if not peor:
                        problemas.append(
                            '%s (%s): %s de %s (%s) contra %s (%s) va al revés'
                            % (nombre_de[tid], a['field_key'], k, a['competitive_level'],
                               a[k], b['competitive_level'], b[k]))

    #  Un campo por plantilla: es lo único que el modal sabe pintar.
    for tid, niveles in por_plantilla.items():
        if len({f['field_key'] for f in niveles.values()}) > 1:
            problemas.append('%s: llevaría más de un campo' % nombre_de[tid])

    if problemas:
        print('\nPROBLEMAS (%d) — no se escribe nada:' % len(problemas))
        for x in problemas[:25]:
            print('   ·', x)
        return 1

    if not APLICAR:
        print('\nSIMULACIÓN. Nada escrito. Repite con --aplicar.')
        io.open('sql/_rangos_a_insertar.json', 'w', encoding='utf-8').write(
            json.dumps(filas, ensure_ascii=False, indent=1))
        print('Lo que se insertaría → sql/_rangos_a_insertar.json')
        return 0

    print('\nInsertando…')
    for i in range(0, len(filas), 50):
        sb.table('test_reference_ranges').insert(filas[i:i + 50]).execute()
        print('   %d/%d' % (min(i + 50, len(filas)), len(filas)))

    total = sb.table('test_reference_ranges').select('id', count='exact').limit(1).execute()
    print('\nHecho. La tabla tiene ahora %d filas (antes %d).'
          % (total.count, len(existentes)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
