# -*- coding: utf-8 -*-
"""
_medir_pantallas.py — Cuántas consultas hace cada pantalla del entrenador.

No mide la app: mide cuántas veces habla con Supabase para pintar una pantalla,
que es lo que decide si abre en medio segundo o en ocho. Cada consulta cuesta
unos 150 ms desde un móvil con datos, así que una pantalla que pregunta
cuarenta veces tarda seis segundos por mucho que el HTML sea ligero.

Levanta una plantilla de 19 jugadores evaluados —el tamaño de un equipo de
verdad— en la cuenta de pruebas, abre cada pantalla contando consultas y borra
lo que creó. Falla si alguna pasa de TOPE.

    python _medir_pantallas.py

El fallo que buscaba cuando se escribió: la pantalla Equipo pedía la ficha y el
histórico de CADA jugador por separado (42 consultas, 8 segundos). Ahora son
cuatro consultas para toda la plantilla.
"""
import collections
import logging
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.getLogger('httpx').setLevel(logging.WARNING)

import app as aplicacion                                    # noqa: E402
from _probar import CUENTAS, entrar, preparar               # noqa: E402
from futbol import db                                       # noqa: E402

VERDE, ROJO, AMARILLO, GRIS, FIN = (
    '\033[92m', '\033[91m', '\033[93m', '\033[90m', '\033[0m')

#  Con veinte jugadores, más de esto es que se está preguntando por cada uno.
TOPE = 25
JUGADORES = 19


def crear_plantilla(uid):
    creados = []
    for i in range(JUGADORES):
        fila = db.insert('fut_manual_players', {
            'coach_id': uid, 'nombre': 'Medida %02d' % i, 'dorsal': i + 1,
            'posicion': 'Centrocampista', 'activo': True,
            'anio_nacimiento': 2009}, 'medida')
        if fila:
            creados.append(fila['id'])
            db.guardar_atributos(manual_player_id=fila['id'],
                                 **{k: 50 + (i % 30) for k in db.ATRIBUTOS_18})
    return creados


def borrar_plantilla(creados):
    for mid in creados:
        for tabla in ('fut_attribute_history', 'fut_attributes', 'fut_player_alerts'):
            db.delete(tabla, 'limpiar medida', manual_player_id=mid)
        db.delete('fut_manual_players', 'limpiar medida', id=mid)


def main():
    ids = preparar()
    uid = db.equipo_id(ids['coach_pro'])
    creados = crear_plantilla(uid)
    if not creados:
        raise SystemExit('No se pudo crear la plantilla de medida.')

    rutas = ['/coach', '/coach/plantilla', '/coach/evaluaciones', '/coach/evolucion',
             '/coach/medico', '/coach/calendario', '/coach/asistencia', '/coach/mental',
             '/coach/partidos', '/coach/observaciones', '/coach/planes',
             '/coach/microciclos',
             '/coach/jugador/%s/progreso' % creados[0],
             '/coach/jugador/%s/evaluar' % creados[0]]

    cuenta = collections.Counter()
    real_q = db.q

    def q_contada(fn, default=None, ctx=''):
        cuenta[ctx or '?'] += 1
        return real_q(fn, default, ctx)

    cliente = aplicacion.app.test_client()
    if not entrar(cliente, CUENTAS['coach_pro']['correo']):
        borrar_plantilla(creados)
        raise SystemExit('No se pudo entrar como coach_pro.')

    print('%-34s %6s %7s   %s' % ('pantalla', 'segs', 'consultas',
                                  'lo que más se repite'))
    pasados = []
    db.q = q_contada
    try:
        for ruta in rutas:
            cuenta.clear()
            t0 = time.time()
            r = cliente.get(ruta)
            tardo = time.time() - t0
            total = sum(cuenta.values())
            top = cuenta.most_common(1)
            color = ROJO if total > TOPE else (AMARILLO if total > TOPE * 0.8 else VERDE)
            nombre = ruta if len(ruta) <= 34 else ruta[:31] + '...'
            print('%s%-34s %6.2f %7d%s   %s%s%s' % (
                color, nombre, tardo, total, FIN, GRIS,
                '%s ×%d' % (top[0][0], top[0][1]) if top else '', FIN)
                + ('' if r.status_code == 200 else '  [%s]' % r.status_code))
            if total > TOPE:
                pasados.append((ruta, total))
    finally:
        db.q = real_q
        borrar_plantilla(creados)

    print()
    if pasados:
        print(ROJO + 'Pantallas que preguntan de más (tope %d con %d jugadores):' % (
            TOPE, JUGADORES) + FIN)
        for ruta, n in pasados:
            print('  - %s: %d consultas' % (ruta, n))
        return 1
    print(VERDE + 'Ninguna pantalla pasa de %d consultas con %d jugadores.' % (
        TOPE, JUGADORES) + FIN)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
