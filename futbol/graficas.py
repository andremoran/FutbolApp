# -*- coding: utf-8 -*-
"""
futbol/graficas.py — Calcular lineas para dibujarlas en SVG.

Sin libreria de graficas: son decenas de kB para pintar ocho puntos, y aqui
manda que la app abra rapido en un movil de gama baja con datos moviles. Lo
que si hace falta es que el calculo NO viva en la plantilla: en Jinja sale
ilegible, no se puede probar y acaba con un `* 10` que nadie ve.

Asi que aqui se hacen las cuentas y la plantilla solo pinta coordenadas.
"""
from datetime import date, datetime


#  Medidas del lienzo, en unidades del viewBox. El margen izquierdo es para
#  los numeros del eje y el de abajo para las fechas.
ANCHO, ALTO = 340.0, 200.0
IZQ, DER, ARRIBA, ABAJO = 30.0, 10.0, 12.0, 34.0


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _dia(v):
    """Convierte a fecha lo que venga: date, datetime o texto ISO."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date(int(v[0:4]), int(v[5:7]), int(v[8:10]))
        except ValueError:
            return None
    return None


def _paso_redondo(bruto, paso_min=0.0):
    """El salto entre marcas del eje, redondeado a algo que se lea bien.

    Un eje con marcas en 3,7 · 7,4 · 11,1 es tecnicamente correcto y no lo
    entiende nadie. Se busca el 1, 2, 5 o 10 mas cercano por arriba.

    Y el salto tiene que ser MULTIPLO de lo que la etiqueta puede escribir.
    Sin eso, un salto de 2,5 con etiquetas sin decimales daba un eje
    «-10 · -8 · -5 · -2 · 0»: las marcas estan bien repartidas pero los
    numeros que se leen no, y parece que la grafica esta mal hecha.
    """
    if bruto <= 0:
        return max(1.0, paso_min)
    bruto = max(bruto, paso_min)

    escala = 1.0
    while bruto >= 10:
        bruto /= 10.0
        escala *= 10.0
    while bruto < 1:
        bruto *= 10.0
        escala /= 10.0

    def _sirve(cand):
        if not paso_min:
            return True
        veces = cand / paso_min
        return abs(veces - round(veces)) < 1e-9

    for tope in (1, 2, 2.5, 5, 10):
        cand = tope * escala
        if bruto <= tope and _sirve(cand):
            return cand
    return 10 * escala


def _rango(lo, hi, marcas=4, paso_min=1.0):
    """Un rango redondo que contenga a los datos, y sus marcas.

    No arranca en cero a proposito: entre 44 y 56 puntos de overall hay una
    diferencia que importa, y con el eje desde cero se ve una linea plana.
    """
    if hi == lo:
        lo, hi = lo - 1, hi + 1
    #  Nunca por debajo de lo que el propio numero puede distinguir, ni un
    #  salto que la etiqueta no sepa escribir entero.
    paso = _paso_redondo((hi - lo) / float(marcas), paso_min)
    base = paso * int(lo / paso) - (paso if lo < 0 and lo % paso else 0)
    while base > lo:
        base -= paso
    techo = base
    while techo < hi:
        techo += paso
    valores = []
    v = base
    while v <= techo + paso / 1000.0:
        valores.append(round(v, 4))
        v += paso
    return base, techo, valores


def multi(series, ancho=ANCHO, alto=ALTO, marcas_y=4, decimales=0):
    """Prepara varias lineas para pintarlas juntas en el mismo eje.

    `series` es una lista de {nombre, color, puntos:[{fecha, valor}]}. Las
    fechas mandan sobre el eje X: si un jugador tiene una evaluacion en enero
    y tres en agosto, el hueco tiene que verse: repartir los puntos a
    distancias iguales cuenta una historia que no paso.

    Devuelve None si no hay al menos una linea con dos puntos — con un punto
    suelto no hay evolucion que dibujar y quien llama debe decirlo con
    palabras, no con una grafica vacia.
    """
    limpias = []
    for s in series or []:
        puntos = [(_dia(p.get('fecha')), p.get('valor'))
                  for p in (s.get('puntos') or [])]
        puntos = [(f, v) for f, v in puntos if f and _num(v)]
        puntos.sort(key=lambda p: p[0])
        if puntos:
            limpias.append(dict(s, _puntos=puntos))

    if not any(len(s['_puntos']) >= 2 for s in limpias):
        return None

    fechas = [f for s in limpias for f, _ in s['_puntos']]
    valores = [v for s in limpias for _, v in s['_puntos']]
    f0, f1 = min(fechas), max(fechas)
    dias = max((f1 - f0).days, 1)
    lo, hi, marcas = _rango(min(valores), max(valores), marcas_y,
                            paso_min=10.0 ** -decimales)

    x0, x1 = IZQ, ancho - DER
    y0, y1 = ARRIBA, alto - ABAJO

    def px(f):
        return round(x0 + (x1 - x0) * ((f - f0).days / float(dias)), 2)

    def py(v):
        return round(y1 - (y1 - y0) * ((v - lo) / float(hi - lo)), 2)

    lineas = []
    for s in limpias:
        pts = s['_puntos']
        d = ' '.join(('M' if i == 0 else 'L') + '%s,%s' % (px(f), py(v))
                     for i, (f, v) in enumerate(pts))
        lineas.append({
            #  De quien es esta linea. Lo necesita quien quiera encenderla y
            #  apagarla desde una leyenda; el resto de pantallas lo ignoran.
            'clave': s.get('clave') or '',
            'nombre': s.get('nombre') or '',
            'color': s.get('color') or 'var(--primary)',
            'grosor': s.get('grosor') or 2,
            'd': d,
            'puntos': [{'x': px(f), 'y': py(v)} for f, v in pts],
            'ultimo': {'x': px(pts[-1][0]), 'y': py(pts[-1][1]),
                       'valor': pts[-1][1]},
            'solo_uno': len(pts) < 2,
        })

    #  Las fechas de abajo: la primera, la ultima y una en medio si caben.
    xt = [(f0, px(f0)), (f1, px(f1))]
    if dias > 60:
        medio = f0 + (f1 - f0) / 2
        xt.insert(1, (medio, px(medio)))

    return {
        'ancho': ancho, 'alto': alto,
        'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1,
        'lineas': lineas,
        'yticks': [{'y': py(v), 'etiqueta': ('%%.%df' % decimales) % v}
                   for v in marcas if lo <= v <= hi],
        'xticks': [{'x': x, 'etiqueta': f.strftime('%d/%m/%y')} for f, x in xt],
        'desde': f0, 'hasta': f1,
    }
