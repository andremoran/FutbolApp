# -*- coding: utf-8 -*-
"""Fase 3 — renderiza la biblioteca y la ficha con los datos que pasa la vista.

La vista previa de `_previsualizar.py` sirve para mirarlas, pero no comprueba
nada. Esto sí: monta las mismas variables que arma la ruta real y falla si la
plantilla pide algo que no le llega.
"""
import sys

sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

from flask import render_template  # noqa: E402

import app as aplicacion  # noqa: E402
from futbol import tests_catalogo as cat  # noqa: E402

app = aplicacion.app
fallos = []

with app.test_request_context('/coach/evaluaciones/catalogo'):
    pruebas = cat.tests_por_categoria()
    for t in pruebas:
        t['_usos'] = 0
    conteos = {}
    for t in pruebas:
        conteos[t['categoria']] = conteos.get(t['categoria'], 0) + 1

    html = render_template('c_eval_catalogo.html',
                           tab_activa='equipo', hide_tabbar=True,
                           categorias=cat.CATEGORIAS, pruebas=pruebas,
                           conteos=conteos, filtro='', n_pruebas=len(pruebas),
                           n_avaladas=sum(1 for t in pruebas if t.get('avalado')))
    n_tarjetas = html.count('class="bi-card"')
    print('Biblioteca      %d KB · %d tarjetas · %d avaladas'
          % (len(html) / 1024, n_tarjetas, html.count('Avalada</span>')))
    if n_tarjetas != len(pruebas):
        fallos.append('La biblioteca pinta %d tarjetas de %d' % (n_tarjetas, len(pruebas)))

#  La ficha se renderiza para LAS 58, no para una de muestra: el problema de
#  estas pantallas es siempre la prueba rara —la que no tiene baremo, la que no
#  trae ficha larga, la propia del entrenador— y esas solo salen probándolas
#  todas.
with app.test_request_context('/coach/evaluaciones/ficha/x'):
    sin_baremo = con_varias = 0
    for clave in cat.CATALOGO:
        t = cat.test(clave)
        edad, nivel = 'sub_17', 'general'
        tablas = []
        for campo in cat.campos_con_baremo(t):
            filas = cat.tabla_baremos(clave, campo['clave'], edad, nivel)
            if filas:
                tablas.append({'campo': campo, 'filas': filas,
                               'menor_mejor': campo.get('direccion') == cat.MENOR})
        if not tablas:
            sin_baremo += 1
        if len(tablas) > 1:
            con_varias += 1
        try:
            html = render_template(
                'c_eval_ficha.html', tab_activa='equipo', hide_tabbar=True,
                test=t, tablas=tablas, usos=0,
                contexto_edad=edad, contexto_nivel=nivel,
                etiqueta_edad=dict(cat.CATEGORIAS_EDAD).get(edad),
                etiqueta_nivel=next((e for c, e, _ in cat.NIVELES_COMPETITIVOS
                                     if c == nivel), 'General'),
                categoria_meta=cat.CATEGORIA_META.get(t['categoria'], {}))
        except Exception as e:
            fallos.append('%s: %s' % (clave, e))
            continue
        if t['nombre'] not in html:
            fallos.append('%s: la ficha no enseña el nombre' % clave)
        #  Cada tabla tiene que marcar la fila del equipo, si no el entrenador
        #  no sabe cuál de las once le aplica. Se cuenta la clase ya
        #  renderizada y no el nombre suelto: «fi-actual» sale también en el
        #  bloque de estilos y daba dos de más en todas.
        marcadas = html.count('class="fi-actual"')
        if tablas and marcadas != len(tablas):
            fallos.append('%s: %d tablas pero %d filas marcadas'
                          % (clave, len(tablas), marcadas))

print('Fichas          %d renderizadas · %d sin baremo · %d con varias tablas'
      % (len(cat.CATALOGO), sin_baremo, con_varias))

print()
if fallos:
    print('FALLOS (%d):' % len(fallos))
    for f in fallos[:30]:
        print('  ·', f)
    sys.exit(1)
print('Sin fallos.')
