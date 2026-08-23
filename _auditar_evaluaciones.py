# -*- coding: utf-8 -*-
"""Revisa las 58 pruebas del catalogo una por una.

No comprueba que la aplicacion arranque —de eso ya hay otros scripts— sino que
los DATOS de cada prueba sean coherentes entre si. Un baremo al reves o un
tope mal puesto no rompe nada: simplemente le dice al entrenador que un chaval
va bien cuando va mal, y eso no se nota hasta que alguien lo mira.

    .venv\\Scripts\\python.exe _auditar_evaluaciones.py
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

import futbol.tests_catalogo as cat

fallos, avisos = [], []


def fallo(clave, texto):
    fallos.append('%-24s %s' % (clave, texto))


def aviso(clave, texto):
    avisos.append('%-24s %s' % (clave, texto))


#  El orden en que se leen los cuatro cortes de un baremo.
NIVELES = ['elite', 'bueno', 'promedio', 'debil']

#  Cuanto mas joven, mas margen: una marca de sub-12 no puede exigir mas que
#  la de sub-14. El orden va de menos a mas exigente.
#
#  Con una excepcion de verdad: la FLEXIBILIDAD baja con la edad. Un nino de
#  sub-15 llega mas lejos en el sit and reach que un adulto, y eso no es un
#  error del baremo sino como funciona el cuerpo — el estiron reduce la
#  flexibilidad relativa y ya no se recupera sola. Estas pruebas se saltan la
#  comprobacion de cruces por edad.
EDADES_ORDEN = ['sub_10', 'sub_12', 'sub_14', 'sub_15', 'sub_16', 'sub_17',
                'sub_18', 'sub_20', 'adulto']

#  De menos a mas nivel competitivo.
NIVELES_ORDEN = ['escuela', 'formativo', 'juvenil', 'amateur', 'semipro',
                 'profesional', 'elite']

#  Pruebas donde ir a menos con la edad es lo esperado.
SE_PIERDE_CON_LA_EDAD = {'sit_and_reach'}


def revisar_una(clave, t):
    campos = t.get('campos') or []
    baremos = t.get('baremos') or {}

    # ── 1. Estructura minima ────────────────────────────────────────────────
    for obligatorio in ('nombre', 'categoria', 'campos'):
        if not t.get(obligatorio):
            fallo(clave, 'sin %s' % obligatorio)

    claves_campo = {c.get('clave') for c in campos}
    if not claves_campo:
        fallo(clave, 'no mide nada: campos vacio')
        return

    principales = [c for c in campos if c.get('principal')]
    if len(principales) > 1:
        fallo(clave, 'tiene %d campos marcados como principal' % len(principales))

    # ── 2. Cada campo, coherente consigo mismo ──────────────────────────────
    for c in campos:
        k = c.get('clave', '?')
        mn, mx = c.get('min'), c.get('max')
        if mn is not None and mx is not None and mn >= mx:
            fallo(clave, '%s: min %s no es menor que max %s' % (k, mn, mx))
        if c.get('direccion') not in (cat.MENOR, cat.MAYOR, None):
            fallo(clave, '%s: direccion rara (%r)' % (k, c.get('direccion')))
        if c.get('tipo', 'numero') == 'numero' and not c.get('unidad'):
            aviso(clave, '%s: sin unidad' % k)
        ej = c.get('ejemplo')
        if ej is not None:
            try:
                v = float(str(ej).replace(',', '.'))
                if mn is not None and v < mn:
                    fallo(clave, '%s: el ejemplo %s esta por debajo del minimo %s' % (k, ej, mn))
                if mx is not None and v > mx:
                    fallo(clave, '%s: el ejemplo %s pasa del maximo %s' % (k, ej, mx))
            except ValueError:
                pass

    # ── 3. Los baremos apuntan a campos que existen ─────────────────────────
    for k in baremos:
        if k not in claves_campo:
            fallo(clave, 'baremo de "%s", que no es un campo de la prueba' % k)

    # ── 4. Cada baremo, en el sentido correcto y sin saltos ─────────────────
    for k, tabla in baremos.items():
        campo = next((c for c in campos if c.get('clave') == k), None)
        if not campo:
            continue
        menor = campo.get('direccion') == cat.MENOR
        mn, mx = campo.get('min'), campo.get('max')

        for ctx, cortes in tabla.items():
            etiqueta = '%s/%s' % ctx if isinstance(ctx, tuple) else str(ctx)
            if len(cortes) != 4:
                fallo(clave, '%s %s: %d cortes en vez de 4' % (k, etiqueta, len(cortes)))
                continue
            if any(v is None for v in cortes):
                fallo(clave, '%s %s: algun corte vacio' % (k, etiqueta))
                continue

            #  Con «menor mejor» los cortes suben (4.02 < 4.14 < …); con «mayor
            #  mejor» bajan. Al reves, la app diria «elite» a la peor marca.
            ordenados = (sorted(cortes) == list(cortes) if menor
                         else sorted(cortes, reverse=True) == list(cortes))
            if not ordenados:
                fallo(clave, '%s %s: cortes en el orden equivocado para %s → %s'
                      % (k, etiqueta, 'menor_mejor' if menor else 'mayor_mejor', cortes))

            if len(set(cortes)) != 4:
                aviso(clave, '%s %s: hay cortes repetidos → %s' % (k, etiqueta, cortes))

            for v in cortes:
                if mn is not None and v < mn:
                    fallo(clave, '%s %s: el corte %s cae por debajo del minimo '
                                 'que admite el formulario (%s)' % (k, etiqueta, v, mn))
                if mx is not None and v > mx:
                    fallo(clave, '%s %s: el corte %s pasa del maximo que admite '
                                 'el formulario (%s)' % (k, etiqueta, v, mx))

    # ── 5. Que no se crucen las categorias ──────────────────────────────────
    #  Un sub-16 no puede tener que correr mas rapido que un sub-17.
    for k, tabla in baremos.items():
        campo = next((c for c in campos if c.get('clave') == k), None)
        if not campo:
            continue
        menor = campo.get('direccion') == cat.MENOR

        def cruces(orden, saca):
            previo, previa_et = None, None
            for et in orden:
                cortes = saca(et)
                if not cortes:
                    continue
                if previo is not None:
                    for i, nivel in enumerate(NIVELES):
                        a, b = previo[i], cortes[i]
                        peor = (b > a) if menor else (b < a)
                        if peor:
                            fallo(clave, '%s: %s exige MENOS que %s en "%s" (%s vs %s)'
                                  % (k, et, previa_et, nivel, b, a))
                            break
                previo, previa_et = cortes, et

        if clave not in SE_PIERDE_CON_LA_EDAD:
            cruces(EDADES_ORDEN, lambda e: tabla.get((e, 'general')))
        cruces(NIVELES_ORDEN, lambda n: tabla.get(('general', n)))

    # ── 6. Lo que la prueba promete y lo que de verdad guarda ───────────────
    #  La ficha describe variables («T10 m, T20 m, T30 m») que muchas veces la
    #  prueba no recoge: solo guarda una. No es un error, pero conviene saber
    #  cuales prometen mas de lo que apuntan, porque el entrenador mide tres
    #  cosas en el campo y luego solo puede escribir una.
    variables = (t.get('variables') or '')
    if variables and len(campos) == 1:
        trozos = [x for x in re.split(r'[,;]', variables) if x.strip()]
        if len(trozos) >= 3:
            aviso(clave, 'la ficha describe %d variables y el formulario solo '
                         'recoge una (%s)' % (len(trozos), campos[0].get('etiqueta')))

    # ── 7. Que no falte lo que la ficha necesita para explicarse ────────────
    ricos = ('objetivo', 'material', 'protocolo_detallado', 'variables')
    vacios = [c for c in ricos if not (t.get(c) or '').strip()]
    if vacios and t.get('avalado'):
        fallo(clave, 'avalada pero sin %s' % ', '.join(vacios))
    elif vacios:
        aviso(clave, 'ficha incompleta: falta %s' % ', '.join(vacios))


for clave in sorted(cat.CATALOGO):
    revisar_una(clave, cat.CATALOGO[clave])


def revisar_el_conjunto():
    """Lo que solo se ve mirando el catalogo entero."""
    from collections import Counter

    nombres = Counter((t.get('nombre') or '').strip().lower()
                      for t in cat.CATALOGO.values())
    for n, veces in nombres.items():
        if veces > 1 and n:
            fallo('(catalogo)', 'hay %d pruebas que se llaman igual: "%s"' % (veces, n))

    ordenes = Counter(t.get('orden') for t in cat.CATALOGO.values()
                      if t.get('orden') is not None)
    repes = [o for o, v in ordenes.items() if v > 1]
    if repes:
        aviso('(catalogo)', 'mismo numero de orden en %d casos: %s'
              % (len(repes), sorted(repes)[:6]))

    for lista, etiqueta in ((getattr(cat, 'CLAVES_AVALADAS', ()), 'CLAVES_AVALADAS'),
                            (getattr(cat, 'CLAVES_MVP', ()), 'CLAVES_MVP')):
        for k in lista:
            if k not in cat.CATALOGO:
                fallo('(catalogo)', '%s nombra "%s", que no existe' % (etiqueta, k))

    sin_baremo = [k for k, t in cat.CATALOGO.items() if not (t.get('baremos') or {})]
    if sin_baremo:
        aviso('(catalogo)', '%d pruebas sin ningun baremo, asi que la marca no se '
                            'puede interpretar: %s'
              % (len(sin_baremo), ', '.join(sorted(sin_baremo)[:8])))



def revisar_las_tablas():
    """Que la tabla de rangos no enseñe la misma fila varias veces.

    Ocho campos miden una diferencia o una asimetria —el desfase entre conducir
    y esprintar, los centimetros de descompensacion entre una pierna y la
    otra— y su baremo es el mismo para todas las edades y niveles, porque 3 cm
    son 3 cm a los 12 y a los 30. La tabla los colapsa en una sola fila; si
    alguna vez vuelve a enseñar once identicas, salta aqui.
    """
    for clave, t in cat.CATALOGO.items():
        for campo in (t.get('baremos') or {}):
            filas = cat.tabla_baremos(clave, campo, 'sub_17', 'juvenil')
            vistos = {tuple(f['cortes']) for f in filas}
            #  Solo cuando TODAS son iguales. Que dos coincidan por casualidad
            #  es normal —el corte de un sub-16 puede caer donde el de un
            #  amateur— y eso no hay que colapsarlo ni avisarlo.
            if len(filas) > 1 and len(vistos) == 1:
                fallo(clave, '%s: la tabla de rangos enseña %d filas identicas; '
                             'deberia colapsarse en una' % (campo, len(filas)))


revisar_las_tablas()
revisar_el_conjunto()

print('Auditoría de las %d pruebas de evaluación' % len(cat.CATALOGO))
print('=' * 70)
if fallos:
    print()
    print('FALLOS (%d) — datos incoherentes:' % len(fallos))
    for f in fallos:
        print('  ·', f)
if avisos:
    print()
    print('PARA MIRAR (%d) — puede estar bien, pero conviene comprobarlo:' % len(avisos))
    for a in avisos:
        print('  ·', a)
if not fallos and not avisos:
    print('Sin nada que señalar.')
print()
sys.exit(1 if fallos else 0)
