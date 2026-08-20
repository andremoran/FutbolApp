# -*- coding: utf-8 -*-
"""Fase 4 — renderiza el home, el asistente y el índice de rankings.

Con las mismas variables que arman las rutas reales, para que falle aquí y no
en producción si una plantilla pide algo que no le llega.
"""
import datetime
import sys

sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

from flask import render_template  # noqa: E402

import app as aplicacion  # noqa: E402
from futbol import evaluaciones as ev  # noqa: E402
from futbol import tests_catalogo as cat  # noqa: E402

app = aplicacion.app
fallos = []

JUGADORES = [{'id': 'j1', 'name': 'Paul Velasco',
              'fut': {'posicion': 'Delantero', 'dorsal': 9}}]
MANUALES = [{'id': 'm1', 'nombre': 'Lionel Messi',
             'posicion': 'Delantero', 'dorsal': 10}]
EDAD, NIVEL = 'sub_17', 'general'


def et_nivel(n):
    return next((e for c, e, _ in cat.NIVELES_COMPETITIVOS if c == n), 'General')


with app.test_request_context('/coach/evaluaciones/asistente'):
    pruebas = cat.tests_por_categoria()
    detalle = {}
    for t in pruebas:
        detalle[t['clave']] = {
            'nombre': t['nombre'], 'categoria': t['categoria'],
            'protocolo': ev._recordatorio_protocolo(t.get('protocolo')),
            'campos': [{'clave': c['clave'], 'etiqueta': c['etiqueta'],
                        'unidad': c.get('unidad') or '',
                        'decimales': c.get('decimales', 2),
                        'min': c.get('min'), 'max': c.get('max'),
                        'ejemplo': c.get('ejemplo') or ''}
                       for c in (t.get('campos') or [])],
            'baremos': [{'etiqueta': c['etiqueta'],
                         'resumen': cat.resumen_baremo(t['clave'], c['clave'], EDAD, NIVEL)}
                        for c in (t.get('campos') or [])
                        if cat.resumen_baremo(t['clave'], c['clave'], EDAD, NIVEL)],
        }

    #  Con jugadores y sin ellos: el estado vacío es la mitad de la pantalla y
    #  se rompe igual de fácil.
    for etiqueta, jugs, mans in (('con jugadores', JUGADORES, MANUALES),
                                 ('sin jugadores', [], [])):
        try:
            html = render_template(
                'c_eval_asistente.html', tab_activa='equipo', hide_tabbar=True,
                jugadores=jugs, manuales=mans, pruebas=pruebas, detalle=detalle,
                contexto_edad=EDAD, contexto_nivel=NIVEL,
                etiqueta_edad=dict(cat.CATEGORIAS_EDAD).get(EDAD),
                etiqueta_nivel=et_nivel(NIVEL), es_pro=True, hoy='2026-08-17')
        except Exception as e:
            fallos.append('asistente (%s): %s' % (etiqueta, e))
            continue
        if jugs or mans:
            n_ops = html.count('class="as-op"')
            esperadas = len(jugs) + len(mans) + len(pruebas)
            if n_ops != esperadas:
                fallos.append('asistente: %d filas elegibles, esperaba %d'
                              % (n_ops, esperadas))
            if 'as-guardar' not in html:
                fallos.append('asistente: falta el botón de guardar')
        else:
            if 'Todavía no tienes jugadores' not in html:
                fallos.append('asistente: sin jugadores no sale el estado vacío')
            #  Sin jugadores no debe colarse el script: sus getElementById
            #  darían null y reventaría la consola nada más abrir.
            if 'as-guardar' in html:
                fallos.append('asistente: sin jugadores no debería llevar el formulario')
        print('Asistente %-15s %d KB' % (etiqueta, len(html) / 1024))

with app.test_request_context('/coach/evaluaciones/rankings'):
    filas = [{'test': cat.test('sprint_30m'), 'n': 14,
              'ultima': datetime.date(2026, 8, 12)},
             {'test': cat.test('squat_1rm'), 'n': 1, 'ultima': None}]
    for etiqueta, datos in (('con marcas', filas), ('sin marcas', [])):
        try:
            html = render_template('c_eval_rankings.html', tab_activa='equipo',
                                   hide_tabbar=True, filas=datos, es_pro=True)
        except Exception as e:
            fallos.append('rankings (%s): %s' % (etiqueta, e))
            continue
        if datos and 'Sprint 30m' not in html:
            fallos.append('rankings: no sale la prueba')
        if not datos and 'Sin marcas todavía' not in html:
            fallos.append('rankings: falta el estado vacío')
        print('Rankings  %-15s %d KB' % (etiqueta, len(html) / 1024))

with app.test_request_context('/coach/evaluaciones'):
    try:
        html = render_template(
            'c_evaluaciones.html', tab_activa='equipo', hide_tabbar=True,
            jugadores=JUGADORES, manuales=MANUALES, resultados=[],
            este_mes=0, evaluados=0, puntaje_medio=None, pendientes=[],
            categorias=cat.CATEGORIAS, contexto_edad=EDAD, contexto_nivel=NIVEL,
            etiqueta_edad=dict(cat.CATEGORIAS_EDAD).get(EDAD),
            etiqueta_nivel=et_nivel(NIVEL),
            edades=cat.CATEGORIAS_EDAD, niveles=cat.NIVELES_COMPETITIVOS,
            descripciones_nivel={c: d for c, _, d in cat.NIVELES_COMPETITIVOS},
            n_pruebas=len(cat.CATALOGO), destacadas=[])
        print('Home                      %d KB' % (len(html) / 1024))
        for texto in ('Cada marca, comparada con su baremo',
                      'Elige jugador → prueba → marcas',
                      'Ranking del equipo por prueba',
                      'Ver las %d pruebas' % len(cat.CATALOGO)):
            if texto not in html:
                fallos.append('home: falta «%s»' % texto)
    except Exception as e:
        fallos.append('home: %s' % e)

print()
if fallos:
    print('FALLOS (%d):' % len(fallos))
    for f in fallos[:20]:
        print('  ·', f)
    sys.exit(1)
print('Sin fallos.')
