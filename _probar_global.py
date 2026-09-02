# -*- coding: utf-8 -*-
"""
_probar_global.py — El GLOBAL de un jugador a lo largo de una temporada.

Las otras pruebas abren pantallas y hacen recorridos de un día. Esto simula
DOCE SEMANAS de un sub-17 —pretemporada, mejora, lesión y vuelta— y comprueba
que el número que resume al jugador (su OVR) se mueve como debe y que todas
las pantallas cuentan la MISMA historia: la tarjeta de Equipo, la pantalla de
Progreso, la de Evaluación, el informe y lo que ve el propio jugador.

Cada semana se guarda por el camino de verdad (`db.guardar_atributos`), solo
que con el reloj movido hacia atrás: así el histórico queda exactamente como
habría quedado evaluando cada lunes durante tres meses.

    python _probar_global.py

Usa las cuentas *@prueba.profoot de _probar.py y borra al terminar el jugador
que crea (atributos, histórico, alertas y marcas incluidos).
"""
import logging
import sys
from datetime import date, datetime, timedelta, timezone

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.getLogger('httpx').setLevel(logging.WARNING)

import app as aplicacion                                    # noqa: E402
from _probar import CUENTAS, entrar, preparar               # noqa: E402
from futbol import coach as pantallas                       # noqa: E402
from futbol import db, evaluaciones as ev                   # noqa: E402

VERDE, ROJO, AMARILLO, GRIS, FIN = (
    '\033[92m', '\033[91m', '\033[93m', '\033[90m', '\033[0m')

_ok = _mal = 0
_fallos = []


#  Esto habla con el Supabase de verdad cientos de veces seguidas, asi que un
#  corte de red se cuela como una fila que «no existe» —`db.q()` se traga los
#  errores de lectura a proposito— y sale por pantalla como un fallo de la app.
#  Paso de verdad: media prueba en rojo por un getaddrinfo que fallo. Se
#  cuentan aparte para poder decirlo al final, en vez de mandar a nadie a
#  buscar en el codigo un fallo que estaba en el wifi.
class _FallosDeRed(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.n = 0

    def emit(self, record):
        self.n += 1


_red = _FallosDeRed()
logging.getLogger('futbol.db').addHandler(_red)


def comprobar(texto, condicion, detalle=''):
    global _ok, _mal
    if condicion:
        _ok += 1
        print(VERDE + '  OK' + FIN + ' ' + texto + (' ' + GRIS + detalle + FIN if detalle else ''))
    else:
        _mal += 1
        _fallos.append((texto, detalle))
        print(ROJO + '  XX ' + texto + FIN + ('  ' + GRIS + detalle + FIN if detalle else ''))
    return bool(condicion)


def titulo(t):
    print('\n' + AMARILLO + '-- ' + t + ' ' + '-' * max(0, 54 - len(t)) + FIN)


# ===========================================================================
#  EL RELOJ
# ===========================================================================
#  `db._foto_de_esta_semana()` pregunta qué lunes es hoy. Moviendo esa única
#  función se puede evaluar «hace once semanas» sin tocar nada más y sin
#  escribir el histórico a mano: lo escribe el mismo código que en producción.
class Reloj:
    def __init__(self):
        self._real = db._lunes_de_esta_semana

    def en(self, lunes):
        db._lunes_de_esta_semana = lambda: lunes.isoformat()

    def restaurar(self):
        db._lunes_de_esta_semana = self._real


def lunes_de(hace_semanas=0):
    hoy = date.today()
    return hoy - timedelta(days=hoy.weekday()) - timedelta(weeks=hace_semanas)


# ===========================================================================
#  EL JUGADOR Y SU TEMPORADA
# ===========================================================================
#  Un extremo de sub-17: rápido y con buen regate, corto de fondo y flojo de
#  definición. Los números son los que pondría un entrenador en la primera
#  evaluación de agosto, no una fila de cincuentas.
SEMANA_1 = {
    'pase': 64, 'control': 62, 'regate': 71, 'tiro': 55, 'definicion': 52,
    'centros': 66, 'vision_juego': 57,
    'velocidad': 75, 'resistencia': 51, 'fuerza': 47, 'agilidad': 68,
    'aceleracion': 73,
    'liderazgo': 45, 'disciplina': 66, 'concentracion': 57, 'confianza': 61,
    'trabajo_equipo': 68, 'mentalidad': 60,
}

#  Qué pasa cada semana, en cambios sobre la anterior. Es la temporada de
#  verdad de un chico de 16 años: se empieza con carga, se mejora despacio, se
#  para tres semanas por un esguince —y ahí lo primero que cae es el fondo, no
#  el pase— y se vuelve un poco por encima de donde se estaba.
TEMPORADA = [
    ('Pretemporada, mucho volumen',    {'resistencia': +4, 'fuerza': +2, 'disciplina': +1}),
    ('Sigue la carga, entra en ritmo', {'resistencia': +3, 'fuerza': +2, 'aceleracion': +1,
                                        'concentracion': +1}),
    ('Primer amistoso, buen partido',  {'confianza': +3, 'definicion': +2, 'tiro': +1,
                                        'resistencia': +2}),
    ('Semana de tecnica individual',   {'control': +2, 'pase': +2, 'centros': +1,
                                        'resistencia': +1}),
    ('Arranca la liga, titular',       {'vision_juego': +2, 'trabajo_equipo': +1,
                                        'confianza': +2, 'fuerza': +1}),
    ('Esguince de tobillo, se para',   {'velocidad': -6, 'aceleracion': -6,
                                        'resistencia': -9, 'agilidad': -7,
                                        'confianza': -5, 'mentalidad': -2}),
    ('Sigue de baja, solo gimnasio',   {'resistencia': -3, 'fuerza': +1, 'confianza': -2}),
    ('Vuelve a correr, sin balon',     {'resistencia': +3, 'velocidad': +2,
                                        'aceleracion': +2, 'confianza': +1}),
    ('Vuelve al grupo',                {'resistencia': +4, 'agilidad': +4, 'velocidad': +3,
                                        'aceleracion': +3, 'confianza': +3}),
    ('Primeros minutos tras la baja',  {'resistencia': +3, 'agilidad': +3,
                                        'confianza': +2, 'mentalidad': +2}),
    ('Ya esta entero, y con hambre',   {'resistencia': +3, 'velocidad': +1,
                                        'definicion': +2, 'tiro': +2, 'liderazgo': +2}),
]


def semanas_del_jugador():
    """Las doce fotos, de la más vieja a la de esta semana."""
    actual = dict(SEMANA_1)
    fotos = [('Primera evaluacion de agosto', dict(actual))]
    for nota, cambios in TEMPORADA:
        for k, v in cambios.items():
            actual[k] = max(1, min(100, actual[k] + v))
        fotos.append((nota, dict(actual)))
    return fotos


def media18(valores):
    vs = [valores[k] for k in db.ATRIBUTOS_18 if valores.get(k) is not None]
    return round(sum(vs) / len(vs))


# ===========================================================================
#  PREPARAR Y LIMPIAR
# ===========================================================================
def crear_jugador(coach_id):
    """Un jugador sin cuenta, que es el caso normal en formación."""
    viejo = db.one('fut_manual_players', 'sim', coach_id=coach_id,
                   nombre='Simulacion Temporada')
    if viejo:
        borrar_jugador(viejo['id'])
    fila = db.insert('fut_manual_players', {
        'coach_id': coach_id, 'nombre': 'Simulacion Temporada', 'dorsal': 77,
        'posicion': 'Extremo derecho', 'activo': True,
        'anio_nacimiento': date.today().year - 16,
    }, 'sim alta')
    if not fila:
        raise SystemExit('No se pudo crear el jugador de simulacion.')
    return fila['id']


def limpiar_jugador(pid):
    """Deja al jugador CON CUENTA de la prueba como si no hubiera pasado nada.

    Incluye sus marcas (`fut_eval_results`): ver el comentario de `main()`.
    """
    dueno = db.dueno_filtro(player_id=pid)
    for tabla in ('fut_attribute_history', 'fut_attributes', 'fut_player_alerts',
                  'fut_eval_results'):
        db.delete(tabla, 'limpiar jugador', **dueno)


def borrar_jugador(mid):
    for tabla in ('fut_attribute_history', 'fut_attributes', 'fut_player_alerts',
                  'fut_eval_results'):
        db.delete(tabla, 'limpiar sim', manual_player_id=mid)
    db.delete('fut_manual_players', 'limpiar sim', id=mid)


# ===========================================================================
#  1. LA TEMPORADA, SEMANA A SEMANA
# ===========================================================================
def simular(mid, fotos, reloj):
    esperados = []
    for i, (nota, valores) in enumerate(fotos):
        lunes = lunes_de(len(fotos) - 1 - i)
        reloj.en(lunes)
        db.guardar_atributos(manual_player_id=mid, **valores)
        fila = db.fila_atributos(manual_player_id=mid) or {}
        esperados.append({'lunes': lunes.isoformat(), 'nota': nota,
                          'valores': valores, 'overall': media18(valores),
                          'guardado': fila.get('overall')})
    reloj.restaurar()
    return db.dueno_filtro(manual_player_id=mid), esperados


def probar_la_curva(mid, dueno, esperados):
    titulo('La temporada: doce evaluaciones, doce semanas')
    for e in esperados:
        marca = ' ' if e['overall'] == e['guardado'] else '!'
        print(GRIS + '   %s  OVR %s %s %s' % (e['lunes'], e['guardado'], marca, e['nota']) + FIN)

    comprobar('El overall guardado es la media de los 18, semana a semana',
              all(e['overall'] == e['guardado'] for e in esperados),
              '%d desviados' % sum(1 for e in esperados if e['overall'] != e['guardado']))

    hist = db.rows('fut_attribute_history', 'sim hist', _order='semana', **dueno)
    comprobar('Hay una foto por semana y ninguna repetida',
              len(hist) == len(esperados) == len({h['semana'] for h in hist}),
              '%d fotos de %d semanas' % (len(hist), len(esperados)))

    comprobar('Cada foto guarda el overall que le tocaba',
              [h['overall'] for h in hist] == [e['overall'] for e in esperados],
              str([h['overall'] for h in hist]))

    comprobar('Cada foto guarda los 18 atributos, no solo el resumen',
              all(len([v for v in (h.get('atributos') or {}).values()
                       if v is not None]) == 18 for h in hist))

    curva = [h['overall'] for h in hist]
    pico, fondo = max(curva[:6]), min(curva[5:9])
    comprobar('La lesion se ve en la curva (baja y luego recupera)',
              fondo < pico and curva[-1] > fondo,
              'pico %s - fondo %s - hoy %s' % (pico, fondo, curva[-1]))

    # Evaluar dos veces la misma semana corrige la foto, no crea otra.
    antes = len(hist)
    valores = dict(esperados[-1]['valores'])
    valores['definicion'] = min(100, valores['definicion'] + 3)
    db.guardar_atributos(manual_player_id=mid, **valores)
    despues = db.rows('fut_attribute_history', 'sim hist', _order='semana', **dueno)
    comprobar('Reevaluar el mismo lunes corrige la foto, no crea otra',
              len(despues) == antes, '%d -> %d' % (antes, len(despues)))
    comprobar('Y la foto de esta semana queda con el numero nuevo',
              despues[-1]['overall'] == media18(valores),
              '%s vs %s' % (despues[-1]['overall'], media18(valores)))
    esperados[-1]['valores'] = valores
    esperados[-1]['overall'] = media18(valores)


# ===========================================================================
#  2. LO QUE DICE CADA PANTALLA
# ===========================================================================
def probar_pantalla_progreso(uid, mid, esperados):
    titulo('Pantalla de Progreso: hoy contra entonces')
    jugador = {'id': mid, 'nombre': 'Simulacion Temporada', 'es_manual': True}
    hoy = esperados[-1]['overall']

    for clave, dias in (('7', 7), ('30', 30), ('90', 90), ('365', 365)):
        datos = pantallas.datos_de_progreso(uid, jugador, clave)
        corte = (date.today() - timedelta(days=dias)).isoformat()
        previas = [e for e in esperados if e['lunes'] < corte]
        dentro = [e for e in esperados if e['lunes'] >= corte]
        ref = previas[-1] if previas else (dentro[0] if dentro else None)

        comprobar('Periodo %s: la referencia es la ultima foto anterior' % clave,
                  datos['resumen']['desde'] == (ref['lunes'] if ref else None),
                  'dice %s, toca %s' % (datos['resumen']['desde'],
                                        ref['lunes'] if ref else None))
        toca = (hoy - ref['overall']) if ref else None
        comprobar('Periodo %s: el delta es el cambio real de overall' % clave,
                  datos['resumen']['delta'] == toca,
                  'dice %s, toca %s' % (datos['resumen']['delta'], toca))
        comprobar('Periodo %s: cuenta bien las fotos del periodo' % clave,
                  datos['resumen']['en_periodo'] == len(dentro),
                  '%s vs %s' % (datos['resumen']['en_periodo'], len(dentro)))

    datos = pantallas.datos_de_progreso(uid, jugador, '90')
    linea = next((l for l in (datos['grafica'] or {}).get('lineas', [])
                  if l['clave'] == 'overall'), None)
    corte90 = (date.today() - timedelta(days=90)).isoformat()
    dentro90 = [e for e in esperados if e['lunes'] >= corte90]
    #  Los puntos son las fotos del periodo mas la de referencia, y esa solo
    #  existe si el jugador ya tenia historico ANTES del periodo.
    tocan = len(dentro90) + (1 if any(e['lunes'] < corte90 for e in esperados) else 0)
    comprobar('La grafica de 90 dias dibuja la referencia y todo el periodo',
              linea is not None and len(linea['puntos']) == tocan,
              '%s puntos, tocan %s' % (len(linea['puntos']) if linea else 0, tocan))
    comprobar('El ultimo punto de la grafica es el overall de hoy',
              bool(linea) and linea['ultimo']['valor'] == esperados[-1]['overall'],
              '%s vs %s' % (linea['ultimo']['valor'] if linea else '-',
                            esperados[-1]['overall']))

    movidos = [a['clave'] for a in datos['movidos']]
    comprobar('Los atributos que mas se movieron salen los primeros',
              'resistencia' in movidos[:3], ', '.join(movidos[:4]))

    cuadro = next((c for c in datos['cuadros'] if c['clave'] == 'overall'), None)
    comprobar('El cuadro del informe y el resumen dicen lo mismo',
              bool(cuadro) and cuadro['valor'] == datos['resumen']['overall'],
              '%s vs %s' % (cuadro['valor'] if cuadro else '-',
                            datos['resumen']['overall']))


def probar_tarjeta_equipo(uid, mid, esperados):
    titulo('Tarjeta de Equipo: el cambio de la semana')
    ficha = pantallas._ficha_equipo(
        uid, lunes_de(0).isoformat(), {},
        manual_player_id=mid, nombre='Simulacion Temporada',
        posicion='Extremo derecho', dorsal=77,
        anio_nacimiento=date.today().year - 16)

    toca = esperados[-1]['overall'] - esperados[-2]['overall']
    comprobar('La tarjeta ensena el overall de hoy',
              ficha['overall'] == esperados[-1]['overall'],
              '%s vs %s' % (ficha['overall'], esperados[-1]['overall']))
    comprobar('El delta de la tarjeta es contra la SEMANA PASADA',
              ficha['_delta'] == toca,
              'dice %s, toca %s' % (ficha['_delta'], toca))
    comprobar('Las tres barras son las medias de familia de hoy',
              ficha['media_fisica'] == db._media_familia(
                  esperados[-1]['valores'], db.ATRIBUTOS_FISICOS),
              str(ficha['media_fisica']))

    #  El panel verde de arriba: «cambio medio» tiene que ser una MEDIA. Con la
    #  suma, un equipo de diecinueve donde todos suben uno enseñaba «+19» al
    #  lado del overall promedio, y ese numero crecia solo con fichar gente.
    cliente = aplicacion.app.test_client()
    if entrar(cliente, CUENTAS['coach_pro']['correo']):
        html = cliente.get('/coach/plantilla').get_data(as_text=True)
        comprobar('El panel del equipo habla de cambio MEDIO, no de la suma',
                  'Cambio medio' in html and 'Cambio semanal' not in html,
                  '')


def probar_pantalla_evaluar(mid, esperados):
    titulo('Pantalla de Evaluacion: la linea y los deltas')
    dueno = db.dueno_filtro(manual_player_id=mid)
    filas = db.rows('fut_attribute_history', 'sim eval', _order='semana', **dueno)
    historial = [h['overall'] for h in filas if h.get('overall') is not None][-8:]
    comprobar('La minigrafica de evaluacion usa las ultimas 8 semanas',
              len(historial) == 8, '%d puntos' % len(historial))
    comprobar('Su delta es el de las dos ultimas fotos',
              historial[-1] - historial[-2] ==
              esperados[-1]['overall'] - esperados[-2]['overall'],
              '%s' % (historial[-1] - historial[-2]))

    #  Los deltas por atributo que pinta c_evaluar salen de la foto anterior
    #  contra la ficha de hoy. Con la definicion subida a mano en la ultima
    #  evaluacion, ese es el atributo que tiene que aparecer movido.
    ficha = db.ficha_atributos(manual_player_id=mid)
    previa = filas[-2].get('atributos') or {}
    deltas = {k: ficha[k] - previa[k] for k in db.ATRIBUTOS_18
              if previa.get(k) is not None and ficha.get(k) != previa.get(k)}
    comprobar('Los deltas por atributo cuadran con la foto de la semana pasada',
              deltas.get('definicion') == (esperados[-1]['valores']['definicion']
                                           - esperados[-2]['valores']['definicion']),
              str(deltas))


# ===========================================================================
#  3. EL MISMO JUGADOR, DOS GLOBALES DISTINTOS
# ===========================================================================
def probar_coherencia_global(ids):
    titulo('El global que ve el coach y el que ve el jugador')
    pid = ids['jugador']
    db.guardar_atributos(player_id=pid, **dict(SEMANA_1))

    ficha = db.ficha_atributos(player_id=pid)
    media_jugador = db.media_atributos(pid)   # lo que pinta /ficha (p_ficha.html)
    comprobar('Mi Ficha (jugador) y la tarjeta del coach dan el mismo global',
              media_jugador == ficha['overall'],
              'el jugador lee %s, el coach %s' % (media_jugador, ficha['overall']))

    #  El radar de «Mi Ficha» son cuatro familias. Las cuatro tienen que salir
    #  de los 18 que sí se evalúan, no de columnas que nadie escribe.
    cuatro = db.atributos(pid)
    comprobar('El radar del jugador sale de los 18, no de columnas muertas',
              cuatro['tecnica'] == ficha['media_tecnica']
              and cuatro['fisico'] == ficha['media_fisica']
              and cuatro['mental'] == ficha['media_mental'],
              str(cuatro))
    tactico = db._media_familia(SEMANA_1, db.ATRIBUTOS_TACTICOS)
    comprobar('El tactico se calcula (leer el juego), no se queda en 50',
              cuatro['tactico'] == tactico,
              'dice %s, toca %s' % (cuatro['tactico'], tactico))


# ===========================================================================
#  4. UNA PRUEBA FISICA, ¿MUEVE EL GLOBAL?
# ===========================================================================
#  Una jornada de pruebas de verdad: cuatro tests en la misma tarde, cada uno
#  midiendo una cosa distinta. Una sola marca mueve un atributo dos puntos y
#  eso en una media de dieciocho no se ve (+0,1); lo que tiene que verse es la
#  tarde entera.
JORNADA = (
    ('cooper', 'distance_meters', 3000, 'resistencia'),
    ('sprint_30m', 'time_seconds', 3.95, 'velocidad'),
    ('cmj', 'height_cm', 58, 'fuerza'),
    ('illinois', 'time_seconds', 14.8, 'agilidad'),
)

#  Y el mes siguiente, jornada a jornada, con el chaval mejorando de VERDAD.
#  Repetir la misma marca cuatro semanas ya no suma nada —y hace bien—, asi
#  que la simulacion tiene que traer el progreso que traeria un sub-17 en
#  pretemporada: el fondo sube deprisa, el sprint casi nada (es lo que mas
#  cuesta mover), el salto y la agilidad algo.
MES_DE_PRUEBAS = (
    {'cooper': 3060, 'sprint_30m': 3.93, 'cmj': 59, 'illinois': 14.65},
    {'cooper': 3140, 'sprint_30m': 3.91, 'cmj': 60, 'illinois': 14.50},
    {'cooper': 3220, 'sprint_30m': 3.89, 'cmj': 61, 'illinois': 14.35},
    {'cooper': 3300, 'sprint_30m': 3.87, 'cmj': 62, 'illinois': 14.20},
)


def probar_prueba_fisica(uid, ids, reloj):
    titulo('Una tarde de pruebas fisicas, todas de nivel elite')
    pid = ids['jugador']
    jugador = db.one('usuarios', 'jugador sim', id=pid)

    antes = db.fila_atributos(player_id=pid) or {}
    ovr_antes = antes.get('overall')
    creados = []

    for clave, campo, valor, atributo in JORNADA:
        fila, error = ev.guardar_resultado(uid, jugador, clave, {campo: valor},
                                           registrado_por=uid)
        if not comprobar('Se anota la marca de %s' % clave,
                         bool(fila) and not error, error or ''):
            continue
        creados.append(fila['id'])
        cambios = fila.get('_cambios') or []
        movidos = {c['atributo'] for c in cambios}
        comprobar('%s mueve el atributo que mide (%s)' % (clave, atributo),
                  atributo in movidos, str(sorted(movidos)) or 'no movio nada')

    despues = db.fila_atributos(player_id=pid) or {}
    comprobar('La tarde de pruebas sube el fisico, que es lo que se midio',
              (despues.get('fisico') or 0) > (antes.get('fisico') or 0),
              '%s -> %s' % (antes.get('fisico'), despues.get('fisico')))
    #  Y el global no puede BAJAR por hacerlo todo bien. Que suba poco es
    #  correcto: cinco atributos fisicos entre dieciocho mueven la media medio
    #  punto, y el overall es un numero entero.
    comprobar('El global no baja por una tarde de pruebas de elite',
              (despues.get('overall') or 0) >= (ovr_antes or 0),
              'overall %s -> %s' % (ovr_antes, despues.get('overall')))

    #  Y queda en la foto de la semana: si no, la pantalla de progreso seguiria
    #  dibujando la linea de antes de las pruebas.
    foto = db.one('fut_attribute_history', 'foto', player_id=pid,
                  semana=lunes_de(0).isoformat()) or {}
    comprobar('La foto de esta semana recoge lo que movieron las pruebas',
              (foto.get('atributos') or {}).get('resistencia') ==
              despues.get('resistencia'),
              'foto %s vs ficha %s' % ((foto.get('atributos') or {}).get('resistencia'),
                                       despues.get('resistencia')))

    #  Una evaluacion posterior que NO toca lo fisico no puede borrar lo que
    #  las pruebas subieron: era el fallo de las columnas derivadas.
    subido = despues.get('resistencia')
    db.guardar_atributos(player_id=pid, liderazgo=70, confianza=70)
    final = db.fila_atributos(player_id=pid) or {}
    comprobar('Evaluar otra cosa NO borra lo que movieron las pruebas',
              final.get('resistencia') == subido,
              '%s -> %s' % (subido, final.get('resistencia')))

    #  Un mes de pruebas: cuatro jornadas, una por semana. Eso SÍ tiene que
    #  verse en el numero de arriba — es la pregunta del entrenador, «¿esto que
    #  estamos haciendo sirve?».
    ovr_mes = (db.fila_atributos(player_id=pid) or {}).get('overall')
    for i, semanas_atras in enumerate((3, 2, 1, 0)):
        reloj.en(lunes_de(semanas_atras))
        fecha = (lunes_de(semanas_atras) + timedelta(days=3)).isoformat()
        for clave, campo, _v, _a in JORNADA:
            f, _e = ev.guardar_resultado(uid, jugador, clave,
                                         {campo: MES_DE_PRUEBAS[i][clave]},
                                         fecha=fecha, registrado_por=uid)
            if f:
                creados.append(f['id'])
    reloj.restaurar()
    final_mes = db.fila_atributos(player_id=pid) or {}
    comprobar('Un mes de pruebas semanales SI mueve el global',
              (final_mes.get('overall') or 0) > (ovr_mes or 0),
              'overall %s -> %s' % (ovr_mes, final_mes.get('overall')))
    semanas = {h['semana'] for h in db.rows('fut_attribute_history', 'h', player_id=pid)}
    comprobar('Cada jornada deja su foto en la semana que le toca',
              len(semanas) >= 4, '%d semanas con foto' % len(semanas))

    for rid in creados:
        db.delete('fut_eval_results', 'limpiar', id=rid)


# ===========================================================================
#  4 ter. REPETIR LA MISMA PRUEBA NO ES MEJORAR
# ===========================================================================
#  El entrenador que pasa el Cooper todos los lunes es el caso normal, no el
#  raro. Si cada marca de nivel elite volviera a sumar, en diez semanas le
#  habria subido veinte puntos de resistencia a un chaval que corre exactamente
#  lo mismo que en agosto.
def probar_repetir_prueba(uid, ids):
    titulo('Repetir la misma marca no regala puntos')
    pid = ids['jugador']
    jugador = db.one('usuarios', 'jugador sim', id=pid)
    creados = []

    def cooper(metros):
        fila, error = ev.guardar_resultado(uid, jugador, 'cooper',
                                           {'distance_meters': metros},
                                           registrado_por=uid)
        if fila:
            creados.append(fila['id'])
        return fila, error

    def resistencia():
        return (db.fila_atributos(player_id=pid) or {}).get('resistencia')

    antes = resistencia()
    fila, _e = cooper(3000)
    primera = resistencia()
    comprobar('La PRIMERA marca coloca al jugador donde le toca',
              primera > antes, '%s -> %s' % (antes, primera))

    fila, _e = cooper(3000)
    comprobar('La misma marca la semana siguiente no suma nada',
              resistencia() == primera and not (fila or {}).get('_cambios'),
              'resistencia %s, cambios %s' % (resistencia(), (fila or {}).get('_cambios')))

    fila, _e = cooper(3150)   # +5% sobre su mejor marca
    mejorada = resistencia()
    comprobar('Mejorar SU marca si sube la ficha',
              mejorada > primera, '%s -> %s' % (primera, mejorada))

    fila, _e = cooper(2800)   # -11% sobre su mejor marca
    comprobar('Y una caida clara la baja',
              resistencia() < mejorada, '%s -> %s' % (mejorada, resistencia()))

    fila, _e = cooper(3140)   # a 0,3% de su mejor marca: un dia normal
    vuelta = resistencia()
    fila, _e = cooper(3145)
    comprobar('Un dia normal, dentro del margen de medicion, no mueve nada',
              resistencia() == vuelta, '%s -> %s' % (vuelta, resistencia()))

    for rid in creados:
        db.delete('fut_eval_results', 'limpiar', id=rid)


# ===========================================================================
#  4 bis. EL EQUIPO DE FORMACION: NADIE TIENE CUENTA
# ===========================================================================
#  No es un caso raro, es EL caso: en el equipo real de la cuenta de pruebas
#  hay 19 jugadores y ninguno tiene cuenta. Si las pruebas y la evolucion solo
#  funcionan con los registrados, para ese entrenador no funcionan.
def probar_equipo_de_formacion(uid, mid):
    titulo('Un equipo donde nadie tiene cuenta')
    manual = db.one('fut_manual_players', 'sim', id=mid)
    antes = db.fila_atributos(manual_player_id=mid) or {}

    jugador = {'id': None, 'nombre': manual['nombre'],
               'anio_nacimiento': manual.get('anio_nacimiento')}
    fila, error = ev.guardar_resultado(uid, jugador, 'cooper',
                                       {'distance_meters': 3000},
                                       manual_id=mid, registrado_por=uid)
    comprobar('Se le puede anotar la marca a un jugador sin cuenta',
              bool(fila) and not error, error or '')
    comprobar('Y esa marca tambien mueve SU ficha',
              bool((fila or {}).get('_cambios')),
              str((fila or {}).get('_cambios')))
    despues = db.fila_atributos(manual_player_id=mid) or {}
    comprobar('Su fisico se mueve como el de un jugador con cuenta',
              (despues.get('fisico') or 0) > (antes.get('fisico') or 0),
              '%s -> %s' % (antes.get('fisico'), despues.get('fisico')))

    cliente = aplicacion.app.test_client()
    if entrar(cliente, CUENTAS['coach_pro']['correo']):
        html = cliente.get('/coach/evolucion').get_data(as_text=True)
        comprobar('«Evolucion del equipo» cuenta a los jugadores sin cuenta',
                  manual['nombre'] in html,
                  '')
    if fila:
        db.delete('fut_eval_results', 'limpiar', id=fila['id'])


# ===========================================================================
#  5. LAS ALERTAS DE LA CAIDA
# ===========================================================================
def probar_alertas(uid, mid, esperados, reloj):
    titulo('Un jugador que cae: ¿avisa la app?')
    dueno = db.dueno_filtro(manual_player_id=mid)
    db.delete('fut_player_alerts', 'limpiar alertas', **dueno)

    hundido = {k: max(1, v - 5) for k, v in esperados[-1]['valores'].items()}
    reloj.en(lunes_de(0))
    db.guardar_atributos(manual_player_id=mid, **hundido)
    reloj.restaurar()

    activas = db.rows('fut_player_alerts', 'alertas', activa=True, **dueno)
    comprobar('Evaluar a la baja crea sola la alerta de retroceso',
              any(a.get('tipo') == 'caida' for a in activas),
              '%d alertas: %s' % (len(activas), [a.get('tipo') for a in activas]))

    db.recalcular_evolucion_equipo(uid)
    activas = db.rows('fut_player_alerts', 'alertas', activa=True, **dueno)
    comprobar('Con el boton de recalcular si aparece la alerta',
              any(a.get('tipo') == 'caida' for a in activas),
              str([a.get('tipo') for a in activas]))

    #  Y guardar otra vez lo mismo no duplica la alerta ni le cambia la fecha:
    #  con esto corriendo en cada marca de cada prueba, duplicar seria cientos
    #  de filas al dia, y reescribir la fecha borraria desde cuando arrastra el
    #  problema.
    caida = next((a for a in activas if a.get('tipo') == 'caida'), None)
    n_antes = len(activas)
    reloj.en(lunes_de(0))
    db.guardar_atributos(manual_player_id=mid, **hundido)
    reloj.restaurar()
    despues = db.rows('fut_player_alerts', 'alertas', activa=True, **dueno)
    comprobar('Guardar otra vez no duplica las alertas',
              len(despues) == n_antes, '%d -> %d' % (n_antes, len(despues)))
    misma = next((a for a in despues if a.get('id') == (caida or {}).get('id')), None)
    comprobar('La alerta que sigue vigente conserva su fecha',
              bool(misma) and misma.get('creado') == caida.get('creado'),
              '')


# ===========================================================================
#  6. LOS BORDES
# ===========================================================================
def probar_bordes(mid):
    titulo('Bordes: potencial, escala y semana')

    db.guardar_atributos(manual_player_id=mid, potencial=70)
    subido = {k: min(100, v + 20) for k, v in SEMANA_1.items()}
    db.guardar_atributos(manual_player_id=mid, **subido)
    ficha = db.ficha_atributos(manual_player_id=mid)
    comprobar('El overall no puede superar al potencial sin corregirlo',
              ficha['overall'] <= ficha['potencial'],
              'OVR %s - POT %s' % (ficha['overall'], ficha['potencial']))

    cliente = aplicacion.app.test_client()
    if not entrar(cliente, CUENTAS['coach_pro']['correo']):
        print(ROJO + '  No se pudo entrar como coach_pro' + FIN)
        return
    with cliente.session_transaction() as s:
        tok = s.get('_csrf')
    cliente.post('/api/manual',
                 json={'id': mid, 'nombre': 'Simulacion Temporada', 'pase': 999},
                 headers={'X-CSRFToken': tok})
    fila = db.fila_atributos(manual_player_id=mid) or {}
    comprobar('«Nuevo jugador» recorta los atributos a 1-100 como la evaluacion',
              (fila.get('pase') or 0) <= 100, 'pase = %s' % fila.get('pase'))

    #  La semana del historico tiene que contarse con la hora del EQUIPO. En
    #  produccion el servidor va en UTC: un domingo a las 20:00 en Ecuador alli
    #  ya es lunes, y la foto de ese domingo se archivaba en la semana
    #  siguiente. Aqui se compara lo que devuelve la app con lo que toca segun
    #  la hora de Ecuador — en esta maquina coincide, en el servidor no.
    local = (datetime.now(timezone.utc) + timedelta(hours=db.HORAS_UTC_LOCAL)).date()
    toca = (local - timedelta(days=local.weekday())).isoformat()
    comprobar('La semana del historico se cuenta con la hora de Ecuador',
              db._lunes_de_esta_semana() == toca,
              'dice %s, toca %s' % (db._lunes_de_esta_semana(), toca))

    #  Y dar de alta a un jugador sin tocar los selectores no puede inventarle
    #  una evaluacion: los 18 arrancan en 5 y guardarlos lo dejaba con 50 de
    #  overall sin que nadie lo hubiera visto jugar.
    cliente2 = aplicacion.app.test_client()
    if entrar(cliente2, CUENTAS['coach_pro']['correo']):
        with cliente2.session_transaction() as s:
            tok2 = s.get('_csrf')
        r = cliente2.post('/api/manual',
                          json={'nombre': 'Simulacion Sin Evaluar', 'fatiga': 'bajo',
                                'riesgo_sobrecarga': 'bajo'},
                          headers={'X-CSRFToken': tok2})
        nuevo = (r.get_json() or {}).get('id')
        if nuevo:
            ficha = db.ficha_atributos(manual_player_id=nuevo)
            comprobar('Un jugador dado de alta sin valorar queda SIN evaluar',
                      not ficha['_tiene_perfil'],
                      'overall %s' % ficha['overall'])
            db.delete('fut_attributes', 'limpiar', manual_player_id=nuevo)
            db.delete('fut_attribute_history', 'limpiar', manual_player_id=nuevo)
            db.delete('fut_manual_players', 'limpiar', id=nuevo)


# ===========================================================================
#  6 ter. UN JUGADOR CON UNA SOLA EVALUACION
# ===========================================================================
#  El caso del primer dia: el entrenador acaba de evaluar a un chaval y abre su
#  progreso. No hay evolucion que enseñar, y decirlo es mejor que restar la
#  unica foto de si misma y pintar un «igual» que se lee como «no mejora».
def probar_una_sola_foto(uid):
    titulo('Un jugador recien evaluado, con una sola foto')
    fila = db.insert('fut_manual_players', {
        'coach_id': uid, 'nombre': 'Simulacion Primera Foto', 'activo': True,
        'anio_nacimiento': date.today().year - 16}, 'sim foto')
    if not fila:
        print(ROJO + '  No se pudo crear el jugador' + FIN)
        return
    mid = fila['id']
    try:
        db.guardar_atributos(manual_player_id=mid, **SEMANA_1)
        datos = pantallas.datos_de_progreso(
            uid, {'id': mid, 'es_manual': True, 'nombre': fila['nombre']}, '30')
        comprobar('Se le ensena su overall de hoy',
                  datos['resumen']['overall'] == media18(SEMANA_1),
                  str(datos['resumen']['overall']))
        comprobar('Pero NO un cambio contra si mismo',
                  datos['resumen']['delta'] is None,
                  'dice delta %s' % datos['resumen']['delta'])
        comprobar('Ni un «comparado con» que no compara nada',
                  datos['resumen']['desde'] is None,
                  'dice desde %s' % datos['resumen']['desde'])
        comprobar('Y no se dibuja una linea de un punto',
                  datos['grafica'] is None, '')

        cliente = aplicacion.app.test_client()
        if entrar(cliente, CUENTAS['coach_pro']['correo']):
            html = cliente.get('/coach/jugador/%s/progreso' % mid).get_data(as_text=True)
            comprobar('La pantalla lo dice con palabras',
                      'sin comparar' in html and 'Solo hay una foto' in html,
                      '')
    finally:
        for tabla in ('fut_attribute_history', 'fut_attributes', 'fut_player_alerts'):
            db.delete(tabla, 'limpiar foto', manual_player_id=mid)
        db.delete('fut_manual_players', 'limpiar foto', id=mid)


# ===========================================================================
#  6 bis. A QUIEN NADIE HA EVALUADO NO SE LE INVENTA UNA NOTA
# ===========================================================================
#  `ficha_atributos()` rellena los huecos con 50 para no dejar pantallas en
#  blanco, y eso esta bien mientras nadie lo confunda con una evaluacion. El
#  jugador abria «Mi Ficha» y leia un «50 · En progreso» enorme, con su radar
#  entero dibujado, sin que ningun entrenador le hubiera visto jugar. Y en la
#  misma app, la pantalla de su entrenador decia «Todavia sin evaluar».
def probar_sin_evaluar(ids):
    titulo('El jugador al que nadie ha evaluado todavia')
    pid = ids['jugador_pro']
    dueno = db.dueno_filtro(player_id=pid)
    db.delete('fut_attributes', 'limpiar sin evaluar', **dueno)
    db.delete('fut_attribute_history', 'limpiar sin evaluar', **dueno)

    cliente = aplicacion.app.test_client()
    if not entrar(cliente, CUENTAS['jugador_pro']['correo']):
        print(ROJO + '  No se pudo entrar como jugador_pro' + FIN)
        return
    html = cliente.get('/ficha').get_data(as_text=True)
    comprobar('«Mi Ficha» le dice que aun no le han evaluado',
              'no te ha evaluado' in html, '')
    comprobar('...y no le ensena una valoracion general inventada',
              'En progreso' not in html and 'Nivel destacado' not in html,
              '')
    comprobar('...ni el radar de un jugador que nadie ha visto jugar',
              'Radar de atributos' not in html, '')

    coach = aplicacion.app.test_client()
    if entrar(coach, CUENTAS['coach_pro']['correo']):
        html = coach.get('/coach/jugador/%s' % pid).get_data(as_text=True)
        comprobar('La pantalla del entrenador no se contradice en su cabecera',
                  'Valoración 50' not in html and 'Todavía sin evaluar' in html,
                  '')

    #  Y la IA tampoco. Con los cuatro atributos a 50, `min` y `max` daban la
    #  misma familia y le decia que su punto fuerte y su punto flojo eran el
    #  mismo, los dos a 50.
    from futbol import ia                                    # noqa: E402
    from usuarios import User                                # noqa: E402
    texto = ia._respaldo(User(db.one('usuarios', 'sin evaluar', id=pid)), '¿como voy?')
    comprobar('La IA no le inventa un punto fuerte a quien nadie ha evaluado',
              'no te ha evaluado' in texto, texto.splitlines()[0][:70])
    comprobar('...y no le nombra su punto fuerte y su punto flojo iguales',
              'punto fuerte' not in texto, texto.splitlines()[0][:70])


# ===========================================================================
#  7. UN CORTE DE RED NO PUEDE ECHARTE DE LA APP
# ===========================================================================
def probar_corte_de_red():
    titulo('La base deja de contestar a mitad de sesion')
    cliente = aplicacion.app.test_client()
    if not entrar(cliente, CUENTAS['coach_pro']['correo']):
        print(ROJO + '  No se pudo entrar como coach_pro' + FIN)
        return

    real = db.one_estricto
    db.one_estricto = lambda *a, **k: (_ for _ in ()).throw(
        db.ErrorDeLectura('getaddrinfo failed'))
    try:
        r = cliente.get('/coach')
        comprobar('Con la base caida NO te manda a la pantalla de acceso',
                  r.status_code == 503,
                  'devolvio %s%s' % (r.status_code,
                                     ' -> ' + r.headers.get('Location', '')
                                     if r.status_code in (301, 302) else ''))
        r = cliente.get('/api/manual', json={})
        comprobar('Y a una llamada de /api/ le contesta JSON, no HTML',
                  r.status_code in (405, 503) and 'json' in (r.content_type or ''),
                  '%s %s' % (r.status_code, r.content_type))
    finally:
        db.one_estricto = real

    r = cliente.get('/coach')
    comprobar('Cuando vuelve la conexion, la sesion sigue abierta',
              r.status_code == 200, 'devolvio %s' % r.status_code)


# ===========================================================================
def main():
    print(AMARILLO + 'Simulando una temporada entera...' + FIN)
    ids = preparar()
    uid = db.equipo_id(ids['coach_pro'])

    #  Se empieza en limpio. Las marcas mandan: desde que una prueba premia
    #  MEJORAR y no repetir, una marca vieja del jugador de pruebas —de una
    #  ejecucion que se corto a medias, por ejemplo— hace que el «primer
    #  Cooper» de esta ya no sea el primero, y media prueba sale en rojo por
    #  algo que no esta en el codigo.
    limpiar_jugador(ids['jugador'])
    mid = crear_jugador(uid)
    reloj = Reloj()
    try:
        dueno, esperados = simular(mid, semanas_del_jugador(), reloj)
        probar_la_curva(mid, dueno, esperados)
        probar_pantalla_progreso(uid, mid, esperados)
        probar_tarjeta_equipo(uid, mid, esperados)
        probar_pantalla_evaluar(mid, esperados)
        probar_coherencia_global(ids)
        probar_prueba_fisica(uid, ids, reloj)
        probar_repetir_prueba(uid, ids)
        probar_equipo_de_formacion(uid, mid)
        probar_alertas(uid, mid, esperados, reloj)
        probar_bordes(mid)
        probar_una_sola_foto(uid)
        probar_sin_evaluar(ids)
        probar_corte_de_red()
    finally:
        reloj.restaurar()
        borrar_jugador(mid)
        limpiar_jugador(ids['jugador'])

    print('\n' + '=' * 68)
    color = VERDE if not _mal else ROJO
    print(color + '%d comprobaciones bien - %d con problema' % (_ok, _mal) + FIN)
    if _red.n:
        print(AMARILLO + 'Ojo: la base no contesto %d vez/veces durante la prueba '
              '(red o Supabase). Si hay fallos arriba, repite antes de buscarlos '
              'en el codigo.' % _red.n + FIN)
    if _fallos:
        print('\n' + ROJO + 'Lo que no cuadra:' + FIN)
        for texto, detalle in _fallos:
            print('  - %s %s%s%s' % (texto, GRIS, detalle, FIN))
    return 1 if _mal else 0


if __name__ == '__main__':
    raise SystemExit(main())
