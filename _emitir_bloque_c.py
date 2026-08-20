# -*- coding: utf-8 -*-
"""Fase 2, paso final — escribe el código.

Salen dos cosas:

  · `futbol/tests_biblioteca.py`  La ficha larga de las 40 (objetivo, material,
    protocolo detallado, variables, valores normativos y bibliografía). Son
    38 KB de texto: metidos en `tests_catalogo.py` lo doblarían y taparían los
    baremos, que es lo que de verdad hay que poder leer ahí.

  · El bloque C para `tests_catalogo.py`, con las 27 pruebas nuevas: nombre,
    familia, orden, icono, campos y baremos. Lo estructural y nada más.
"""
import io
import re
import sys

sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

import _baremos_40 as g  # noqa: E402

CABECERA_BIB = '''# -*- coding: utf-8 -*-
"""
futbol/tests_biblioteca.py — La ficha larga de las 40 pruebas avaladas.

ESTE ARCHIVO ESTÁ GENERADO. No editar a mano: sale de `_emitir_bloque_c.py`,
que lee las 40 plantillas de `evaluation_templates` (las mismas que muestra la
app nativa en «Biblioteca de tests»).

`tests_catalogo.py` fusiona esto con `setdefault`, así que lo que una prueba ya
traía del MVP NO se pisa: la descripción y el protocolo que el entrenador ya
conoce siguen literales, y solo se le añaden los campos que antes no existían.

De las 40, trece ya estaban en el catálogo midiendo lo mismo y se enriquecen en
su sitio; las otras veintisiete se dan de alta en el bloque C del catálogo.
"""

BIBLIOTECA = {
'''


def texto(v):
    """Literal de Python legible: comillas simples, y triple comilla si es largo."""
    if v is None:
        return "''"
    v = re.sub(r'\s+', ' ', str(v)).strip()
    if not v:
        return "''"
    esc = v.replace('\\', '\\\\').replace("'", "\\'")
    if len(esc) <= 62:
        return "'%s'" % esc
    #  Troceado en líneas de ~68 para que se lea en el editor sin scroll.
    partes, linea = [], ''
    for palabra in esc.split(' '):
        if len(linea) + len(palabra) + 1 > 68 and linea:
            partes.append(linea)
            linea = palabra
        else:
            linea = (linea + ' ' + palabra).strip()
    if linea:
        partes.append(linea)
    sangria = ' ' * 8
    return ('\n' + sangria).join("'%s '" % p if i < len(partes) - 1 else "'%s'" % p
                                 for i, p in enumerate(partes))


def fuente_corta(bibliografia):
    """La cita, sin la coletilla de «▸ Usado por: ...» que trae la biblioteca."""
    if not bibliografia:
        return ''
    return re.sub(r'\s+', ' ', bibliografia.split('▸')[0]).strip().rstrip('.')


def main():
    res = g.main()
    plantillas = {}
    import json
    datos = json.load(io.open('sql/_sb_evaluaciones.json', encoding='utf-8'))
    for t in datos['templates']:
        plantillas[t['name']] = t

    #  clave del catálogo → plantilla de la biblioteca, para las 40.
    mapa = dict(g.DUPLICADOS)
    for clave, spec in g.NUEVAS.items():
        mapa[clave] = spec['plantilla']

    # ─── 1. La ficha larga ──────────────────────────────────────────────────
    out = [CABECERA_BIB]
    for clave in sorted(mapa):
        p = plantillas[mapa[clave]]
        out.append("    '%s': {\n" % clave)
        out.append("        'nombre_biblioteca': %s,\n" % texto(p['name']))
        for destino, origen in (('objetivo', 'objective'), ('material', 'materials'),
                                ('protocolo_detallado', 'protocol'),
                                ('variables', 'variables'), ('normativa', 'norms'),
                                ('bibliografia', 'bibliography')):
            out.append("        '%s': %s,\n" % (destino, texto(p.get(origen))))
        #  Solo las 27 nuevas necesitan que la fusión les ponga descripción y
        #  protocolo; las 13 que ya estaban traen los suyos del MVP y mandan.
        if clave in g.NUEVAS:
            out.append("        'descripcion': %s,\n" % texto(p.get('description')))
            out.append("        'protocolo': %s,\n" % texto(p.get('protocol')))
        out.append('    },\n\n')
    out.append('}\n')
    io.open('futbol/tests_biblioteca.py', 'w', encoding='utf-8').write(''.join(out))
    print('futbol/tests_biblioteca.py — %d fichas' % len(mapa))

    # ─── 2. El bloque C ─────────────────────────────────────────────────────
    sys.path.insert(0, '.')
    from futbol import tests_catalogo as cat
    orden = {}
    for fam in ('fisico', 'tecnico'):
        maximo = max((t.get('orden', 0) for t in cat.CATALOGO.values()
                      if t['categoria'] == fam), default=0)
        orden[fam] = ((maximo // 10) + 1) * 10

    filas = []
    for clave, v in sorted(res.items(),
                           key=lambda kv: (kv[1]['plantilla']['category'] != 'fisico',
                                           kv[1]['plantilla']['name'])):
        p, spec = v['plantilla'], v['spec']
        fam = p['category']
        filas.append("    '%s': {\n" % clave)
        filas.append("        'nombre': %s,\n" % texto(p['name']))
        filas.append("        'categoria': '%s',\n" % fam)
        filas.append("        'orden': %d,\n" % orden[fam])
        filas.append("        'icono': '%s',\n" % (p.get('icon') or 'activity'))
        filas.append("        'fuente': %s,\n" % texto(fuente_corta(p.get('bibliography'))))
        orden[fam] += 10

        filas.append("        'campos': [\n")
        for (ck, etq, uni, mn, mx, dec, ej, dirn, principal) in spec['campos']:
            filas.append("            _campo('%s', %s, %s, %s, %s, %d, '%s', %s%s),\n"
                         % (ck, texto(etq), texto(uni), mn, mx, dec, ej,
                            'MENOR' if dirn == g.MENOR else 'MAYOR',
                            '' if principal else ', False'))
        filas.append("        ],\n")

        filas.append("        'baremos': {\n")
        for campo in [c[0] for c in spec['campos']]:
            tabla = v['baremos'].get(campo)
            if not tabla:
                continue
            filas.append("            '%s': {\n" % campo)
            for ctx in g.ORDEN_CONTEXTOS:
                par = "('%s', '%s'):" % ctx
                filas.append("                %-28s %s,\n" % (par, tabla[ctx]))
            filas.append("            },\n")
        filas.append("        },\n")
        filas.append("    },\n\n")

    bloque = ''.join(filas)

    # ─── 3. Metido en su sitio dentro del catálogo ──────────────────────────
    #  Se reemplaza entre marcas en vez de dejar un .txt aparte: tener una
    #  segunda copia de 50 KB de baremos es pedir que las dos se separen.
    ruta = 'futbol/tests_catalogo.py'
    cat_src = io.open(ruta, encoding='utf-8').read()
    abre, cierra = '_BIBLIOTECA_TESTS = {\n', '\n}\n\n\n# El catálogo que ve la app'
    i, j = cat_src.find(abre), cat_src.find(cierra)
    if i < 0 or j < 0 or j < i:
        raise SystemExit('No encuentro el bloque C en %s' % ruta)
    nuevo = cat_src[:i + len(abre)] + '\n' + bloque.rstrip('\n ,') + cat_src[j:]
    io.open(ruta, 'w', encoding='utf-8').write(nuevo)
    print('%s — bloque C reescrito (%d pruebas, %.1f KB)'
          % (ruta, len(res), len(bloque) / 1024))


if __name__ == '__main__':
    main()
