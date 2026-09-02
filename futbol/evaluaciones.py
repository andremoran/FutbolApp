# -*- coding: utf-8 -*-
"""
futbol/evaluaciones.py — Evaluar a un jugador contra baremos internacionales.

Qué hace que esto valga y no sea una tabla de números
─────────────────────────────────────────────────────
Anotar «4,22 s en 30 metros» no le dice nada a nadie. El módulo compara ese
número con el baremo que corresponde a la EDAD y al NIVEL COMPETITIVO del
equipo (tests_catalogo.py) y devuelve un veredicto: élite, bueno, promedio, a
mejorar o bajo, más un puntaje 0-100 que sí es comparable entre pruebas
distintas — y por eso permite decir «este chico corre mejor de lo que salta».

Quién ve qué
────────────
  Entrenador (gratis)  puede tomar pruebas y ver los números en crudo.
  Coach Pro            además ve el nivel contra baremo, el ranking del equipo
                       y la evolución.
  Jugador              ve SUS resultados; el nivel solo si es Pro.

Se separó de coach.py porque son dieciséis rutas y allí dentro no se
encontraría nada.
"""
import logging
import math
import uuid
from datetime import date, datetime, timedelta, timezone

from flask import (abort, flash, jsonify, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_required

import roles

from . import bp, db
from . import tests_catalogo as cat

logger = logging.getLogger(__name__)


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _coach_o_fuera():
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.inicio'))
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  CONTEXTO: contra qué baremo se compara
# ═══════════════════════════════════════════════════════════════════════════
def contexto_equipo(coach_id):
    """Categoría de edad y nivel competitivo configurados para el equipo."""
    eq = db.one('fut_teams', 'contexto', coach_id=coach_id) or {}
    return (eq.get('categoria_edad') or 'general', eq.get('nivel') or 'general')


def contexto_de(jugador, coach_id=None):
    """El contexto de UN jugador.

    El del equipo manda, porque el entrenador lo eligió a conciencia. Solo si
    no lo configuró se deduce de su nacimiento: un sub-15 metido en un grupo
    sin categoría se compara al menos con su edad y no con adultos.

    Con la FECHA completa la categoría es exacta y cambia sola el día que el
    jugador cumple años. Con solo el año —lo único que se sabía antes— cambiaba
    de golpe cada 1 de enero, y a un chico de diciembre lo subía de categoría
    once meses antes de tiempo.
    """
    edad, nivel = ('general', 'general')
    if coach_id:
        edad, nivel = contexto_equipo(coach_id)

    if edad == 'general':
        edad = cat.categoria_por_edad(
            (jugador or {}).get('anio_nacimiento'),
            fecha_nacimiento=(jugador or {}).get('fecha_nacimiento'))
    if nivel == 'general' and edad != 'general':
        nivel = cat.nivel_sugerido(edad)
        #  Para las categorías de formación la edad ya dice bastante (un sub-14
        #  es formativo lo entrene quien lo entrene) y ese respaldo se respeta
        #  tal cual. Donde la edad no informa de nada es en el adulto: ahí
        #  `nivel_sugerido` devolvía `amateur` para todo el mundo, así que un
        #  club profesional que nunca tocó «Nivel del equipo» estaba midiendo a
        #  sus jugadores contra el baremo de una liga barrial. Quien sí lo sabe
        #  es el segmento.
        if nivel == 'amateur' and coach_id:
            from . import segmentos as seg
            nivel = seg.nivel_sugerido(seg.del_entrenador(coach_id))
    return edad, nivel


def guardar_contexto(coach_id, categoria_edad, nivel):
    """La edad y el nivel del equipo, que son los que eligen el baremo.

    Obligatorio a proposito: si esto se pierde en silencio, el entrenador lee
    «Listo» y las evaluaciones siguen comparandose con la categoria vieja. Es
    exactamente el lio que se queria quitar de encima al juntar el ajuste en
    un solo sitio, asi que aqui mentir sale caro.
    """
    eq = db.one('fut_teams', 'equipo ctx', coach_id=coach_id)
    datos = {'categoria_edad': categoria_edad, 'nivel': nivel}
    if eq:
        db.update('fut_teams', datos, 'ctx up', obligatorio=True, id=eq['id'])
    else:
        datos.update({'coach_id': coach_id, 'nombre': 'Mi equipo', 'creado': _ahora()})
        db.insert('fut_teams', datos, 'ctx nuevo', obligatorio=True)


# ═══════════════════════════════════════════════════════════════════════════
#  PRUEBAS: catálogo estándar + las propias del entrenador
# ═══════════════════════════════════════════════════════════════════════════
def pruebas_propias(coach_id):
    filas = db.rows('fut_eval_templates', 'propias', coach_id=coach_id) or []
    salida = []
    for f in filas:
        salida.append({
            'clave': f['clave'], 'nombre': f['nombre'],
            'categoria': f.get('categoria') or 'fisico',
            'subcategoria': 'Prueba propia',
            'descripcion': f.get('descripcion') or '',
            'protocolo': f.get('protocolo') or '',
            'icono': f.get('icono') or 'activity',
            'campos': f.get('campos') or [],
            'fuente': 'Prueba creada por el entrenador',
            'baremos': {}, '_propia': True, '_id': f['id'],
        })
    return salida


def prueba(clave, coach_id=None):
    """Busca la prueba en el catálogo y, si no está, entre las del entrenador."""
    t = cat.test(clave)
    if t:
        return t
    if coach_id:
        return next((p for p in pruebas_propias(coach_id) if p['clave'] == clave), None)
    fila = db.one('fut_eval_templates', 'prueba suelta', clave=clave)
    if not fila:
        return None
    return {'clave': fila['clave'], 'nombre': fila['nombre'],
            'categoria': fila.get('categoria') or 'fisico',
            'subcategoria': 'Prueba propia',
            'descripcion': fila.get('descripcion') or '',
            'protocolo': fila.get('protocolo') or '',
            'icono': fila.get('icono') or 'activity',
            'campos': fila.get('campos') or [], 'baremos': {},
            'fuente': 'Prueba creada por el entrenador', '_propia': True}


def catalogo_completo(coach_id=None):
    todas = cat.tests_por_categoria()
    if coach_id:
        todas = todas + pruebas_propias(coach_id)
    return todas


def _baremo_propio(coach_id, clave, campo, edad, nivel):
    """El baremo que el entrenador ajustó, si lo hizo. Manda sobre el estándar."""
    if not coach_id:
        return None
    filas = db.rows('fut_eval_ranges', 'baremo propio',
                    coach_id=coach_id, test_clave=clave, campo=campo) or []
    if not filas:
        return None
    for e, n in ((edad, nivel), (edad, 'general'), ('general', nivel), ('general', 'general')):
        f = next((x for x in filas
                  if x.get('categoria') == e and x.get('nivel') == n), None)
        if f:
            cortes = [f.get('elite'), f.get('bueno'), f.get('promedio'), f.get('debil')]
            if all(c is not None for c in cortes):
                return {'cortes': [float(c) for c in cortes], 'edad': e, 'nivel': n,
                        'fuente': f.get('fuente') or 'Baremo propio del entrenador',
                        'direccion': f.get('direccion') or cat.MAYOR, '_propio': True}
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  EVALUAR
# ═══════════════════════════════════════════════════════════════════════════
def evaluar(clave, valores, edad='general', nivel='general', coach_id=None):
    """Convierte {campo: número} en niveles + puntaje global.

    El puntaje del conjunto es el del campo PRINCIPAL, no el promedio de todos:
    en el Yo-Yo la distancia es el resultado y el nivel alcanzado es su reflejo,
    promediarlos contaría dos veces lo mismo. Si el principal no tiene baremo,
    se promedia lo que haya.
    """
    t = prueba(clave, coach_id)
    if not t:
        return {}, None

    niveles, puntajes, detalle = {}, {}, {}
    principal = cat.campo_principal(t)
    clave_principal = principal['clave'] if principal else None

    for campo, valor in (valores or {}).items():
        if valor is None:
            continue
        propio = _baremo_propio(coach_id, clave, campo, edad, nivel)
        if propio:
            direccion = propio.get('direccion') or cat.direccion_de(clave, campo)
            n = cat.clasificar(valor, propio['cortes'], direccion)
            p = cat.puntaje_de(valor, propio['cortes'], direccion)
            baremo = propio
        else:
            r = cat.evaluar_valor(clave, campo, valor, edad, nivel)
            n, p, baremo = r['nivel'], r['puntaje'], r['baremo']
        if n:
            niveles[campo] = n
            detalle[campo] = {'nivel': n, 'puntaje': p, 'baremo': baremo,
                              'meta': cat.NIVEL_META.get(n)}
        if p is not None:
            puntajes[campo] = p

    if clave_principal and clave_principal in puntajes:
        global_ = puntajes[clave_principal]
    elif puntajes:
        global_ = int(round(sum(puntajes.values()) / len(puntajes)))
    else:
        global_ = None

    return niveles, global_, detalle


def guardar_resultado(coach_id, jugador, clave, valores, fecha=None, notas='',
                      manual_id=None, registrado_por=None):
    """Anota la prueba y la deja ya clasificada. Devuelve (fila, error)."""
    t = prueba(clave, coach_id)
    if not t:
        return None, 'Esa prueba no existe.'

    limpios = {}
    for campo in t.get('campos', []):
        bruto = (valores or {}).get(campo['clave'])
        if bruto in (None, ''):
            continue
        try:
            v = float(str(bruto).replace(',', '.'))
        except (TypeError, ValueError):
            return None, f'«{campo["etiqueta"]}» tiene que ser un número.'
        lo, hi = campo.get('min'), campo.get('max')
        if lo is not None and hi is not None and not (lo <= v <= hi):
            return None, (f'«{campo["etiqueta"]}» debería estar entre {lo:g} y '
                          f'{hi:g} {campo.get("unidad", "")}. '
                          f'¿Seguro que anotaste {v:g}?')
        limpios[campo['clave']] = round(v, 3)

    if not limpios:
        return None, 'Anota al menos una medida.'

    edad, nivel = contexto_de(jugador, coach_id)
    niveles, puntaje, _ = evaluar(clave, limpios, edad, nivel, coach_id)

    fila = db.insert('fut_eval_results', {
        'coach_id': coach_id,
        'player_id': (jugador or {}).get('id') if not manual_id else None,
        'manual_player_id': manual_id,
        'jugador_nombre': ((jugador or {}).get('nombre')
                           or (jugador or {}).get('name') or '')[:120],
        'test_clave': clave,
        'test_nombre': t['nombre'][:120],
        'categoria': t.get('categoria') or 'fisico',
        'fecha': fecha or db.hoy_iso(),
        'valores': limpios,
        'niveles': niveles,
        'puntaje': puntaje,
        'contexto_edad': edad,
        'contexto_nivel': nivel,
        'notas': (notas or '')[:1500],
        # Quién puso el número. En un equipo con asistentes, sin esto el
        # primer dato raro se convierte en una discusión sin árbitro.
        'registrado_por': registrado_por,
        'creado': _ahora(),
    }, 'guardar evaluacion')

    if not fila:
        return None, 'No se pudo guardar. Inténtalo de nuevo.'

    # La marca no se queda en una tabla aparte: mueve la ficha del jugador,
    # tenga cuenta o no.
    principal = cat.campo_principal(t)
    fila['_cambios'] = aplicar_a_ficha(
        coach_id,
        db.dueno_filtro(player_id=None if manual_id else (jugador or {}).get('id'),
                        manual_player_id=manual_id),
        t, niveles.get(principal['clave']) if principal else None, marca=fila)
    return fila, None


# ═══════════════════════════════════════════════════════════════════════════
#  LA MARCA MUEVE LA FICHA
# ═══════════════════════════════════════════════════════════════════════════
#  Igual que teamTestAnalysis.ts en la app original. El delta sale de dos
#  lecturas y se queda con la más generosa para el jugador:
#
#    · Cómo quedó DENTRO DEL EQUIPO (percentil). Pide tres marcas o más:
#      con dos jugadores, «último puesto» no significa nada.
#    · Cómo quedó CONTRA EL BAREMO (nivel absoluto). Evita castigar a quien
#      corre a nivel élite pero juega en un equipo aún mejor.
#
#  Luego se reparte según el peso del atributo y se limita a ±2, para que una
#  sola tarde de pruebas no reescriba la ficha entera.

DELTA_POR_NIVEL = {'elite': 2, 'bueno': 1, 'promedio': 0, 'debil': -1, 'muy_debil': -2}
TOPE_DELTA = 2

#  ...pero esas dos lecturas solo valen LA PRIMERA VEZ que el jugador hace la
#  prueba. Dicen dónde está, y eso ya se le sumó a la ficha ese día. Volver a
#  premiarlas en cada repetición era pagar diez veces por el mismo Cooper: un
#  chaval que corriera los mismos 3.000 m cada lunes ganaba veinte puntos de
#  resistencia en diez semanas sin haber mejorado nada, y el global con él.
#
#  De la segunda marca en adelante manda una sola pregunta: ¿ha mejorado su
#  propia marca? El cambio se mide en porcentaje sobre su mejor marca anterior,
#  que es lo único comparable entre segundos, metros, centímetros y
#  repeticiones.
#
#  Sube antes de lo que baja, y a propósito: un mal día —viento, cronómetro a
#  mano, mala noche— no es perder facultades, pero quedarse un 7% por debajo de
#  tu mejor marca sí dice algo. Por debajo del 1,5% no se mueve nada: eso es
#  ruido de medición, no progreso.
MEJORA_GRANDE, MEJORA_MINIMA = 5.0, 1.5
CAIDA_GRANDE, CAIDA_MINIMA = -7.0, -3.0

#  Cómo se llama por escrito lo que movió la marca. Salen de `db.ETIQUETAS_18`
#  porque lo que se mueve son los 18 del Perfil Dinámico: el aviso dice
#  «Resistencia», que es lo que se entrenó, y no «Físico», que no dice nada.
NOMBRE_ATRIBUTO = db.ETIQUETAS_18


def percentil(puesto, total):
    """100 es la mejor marca del equipo; 0, la peor."""
    if not puesto or not total or total < 2:
        return None
    return round((total - puesto) / (total - 1) * 100)


def _delta_por_percentil(p, total):
    if p is None or total < 3:
        return None
    if p >= 85:
        return 2
    if p >= 65:
        return 1
    if p >= 35:
        return 0
    if p >= 15:
        return -1
    return -2


def _redondear(x):
    """El medio punto sube, como Math.round en la app original.

    round() de Python redondea al par: round(0.5) da 0 y round(1.5) da 2. Con
    un peso de 0.5 las dos apps darían números distintos para la misma marca.
    """
    return math.floor(x + 0.5)


def estadisticas(valores):
    """Media, mediana, mínimo y máximo de un conjunto de marcas.

    La mediana importa tanto como la media: con un jugador muy destacado, la
    media miente sobre cómo está el resto del equipo.
    """
    limpios = sorted(v for v in (valores or []) if v is not None)
    if not limpios:
        return {'n': 0, 'media': None, 'mediana': None,
                'minimo': None, 'maximo': None}
    n = len(limpios)
    mitad = n // 2
    mediana = limpios[mitad] if n % 2 else (limpios[mitad - 1] + limpios[mitad]) / 2
    return {'n': n,
            'media': round(sum(limpios) / n, 2),
            'mediana': round(mediana, 2),
            'minimo': limpios[0],
            'maximo': limpios[-1]}


def ranking_de(coach_id, clave, t=None):
    """Mejor marca de cada jugador en una prueba, de mejor a peor.

    Del ranking cuelgan tres cosas —la pantalla, el percentil y el delta de la
    ficha—, así que vive aquí y no dentro de la vista.
    """
    t = t or prueba(clave, coach_id)
    if not t:
        return [], None, cat.MAYOR

    principal = cat.campo_principal(t)
    campo = principal['clave'] if principal else None
    direccion = principal.get('direccion') if principal else cat.MAYOR

    mejores = {}
    for r in enriquecer([x for x in resultados_equipo(coach_id, 400)
                         if x.get('test_clave') == clave], coach_id):
        pid = r.get('player_id') or r.get('manual_player_id')
        if not pid or r['_valor'] is None:
            continue
        actual = mejores.get(pid)
        if not actual or (r['_valor'] < actual['_valor'] if direccion == cat.MENOR
                          else r['_valor'] > actual['_valor']):
            mejores[pid] = r

    tabla = sorted(mejores.values(),
                   key=lambda r: r['_valor'] * (1 if direccion == cat.MENOR else -1))
    total = len(tabla)
    for i, r in enumerate(tabla, 1):
        r['_puesto'] = i
        r['_percentil'] = percentil(i, total)
    return tabla, campo, direccion


def _progreso_propio(dueno, t, marca):
    """Cuánto ha mejorado respecto a SU mejor marca anterior, en puntos de
    ficha (-2 a +2). Devuelve None si es la primera vez que hace esta prueba,
    que es cuando siguen mandando el baremo y el puesto en el equipo.

    Se compara contra la mejor, no contra la última: la mejor es la que ya se
    le pagó, y con la última bastaría con alternar un día malo y otro bueno
    para ir cobrando la misma mejora una y otra vez.
    """
    principal = cat.campo_principal(t) if t else None
    if not principal or not marca:
        return None
    campo = principal['clave']
    ahora = (marca.get('valores') or {}).get(campo)
    if not isinstance(ahora, (int, float)):
        return None

    previas = []
    for f in db.rows('fut_eval_results', 'marcas previas',
                     test_clave=t.get('clave'), **dueno):
        if str(f.get('id')) == str(marca.get('id')):
            continue
        v = (f.get('valores') or {}).get(campo)
        if isinstance(v, (int, float)):
            previas.append(v)
    if not previas:
        return None

    menor_mejor = principal.get('direccion') == cat.MENOR
    mejor = min(previas) if menor_mejor else max(previas)
    if not mejor:
        return None

    cambio = (mejor - ahora) if menor_mejor else (ahora - mejor)
    pct = cambio / abs(mejor) * 100
    if pct >= MEJORA_GRANDE:
        return 2
    if pct >= MEJORA_MINIMA:
        return 1
    if pct <= CAIDA_GRANDE:
        return -2
    if pct <= CAIDA_MINIMA:
        return -1
    return 0


def aplicar_a_ficha(coach_id, dueno, t, nivel_absoluto, marca=None):
    """Mueve los atributos del jugador según cómo le fue. Devuelve los cambios.

    `dueno` es el par de `db.dueno_filtro()`: vale igual para un jugador con
    cuenta y para uno apuntado a mano. Antes solo movía la ficha del
    registrado, y en un equipo de formación —donde casi nadie tiene cuenta—
    eso quería decir que las pruebas no movían nada de nadie.

    Se escribe por `db.guardar_atributos`, que es la única puerta al Perfil
    Dinámico: recalcula el overall, las tres medias de familia y deja la foto
    de la semana. Antes se escribía en las cuatro columnas derivadas
    (`guardar_familias`) y pasaban dos cosas malas: el overall no se movía y la
    siguiente evaluación borraba lo que las pruebas habían subido.

    A quien todavía no tiene Perfil Dinámico no se le toca nada. Sumarle
    puntos a los cincuenta con los que `ficha_atributos()` rellena los huecos
    sería inventarle una evaluación que nadie hizo, y a partir de ahí la
    pantalla de progreso enseñaría la «evolución» de un jugador sin evaluar.
    """
    if not dueno:
        return []

    ficha = db.ficha_atributos(**dueno)
    if not ficha.get('_tiene_perfil'):
        return []

    #  ¿Es la primera vez que hace esta prueba, o ya tiene marca con la que
    #  compararse? Ver el comentario de MEJORA_MINIMA: la respuesta cambia por
    #  completo de dónde sale el delta.
    base = _progreso_propio(dueno, t, marca)
    if base is None:
        tabla, _, _ = ranking_de(coach_id, t.get('clave'), t)
        mio_id = str(list(dueno.values())[0])
        mio = next((r for r in tabla
                    if str(r.get('player_id') or r.get('manual_player_id')) == mio_id), None)
        por_equipo = (_delta_por_percentil(mio.get('_percentil'), len(tabla))
                      if mio else None)
        por_baremo = DELTA_POR_NIVEL.get(nivel_absoluto)

        lecturas = [d for d in (por_equipo, por_baremo) if d is not None]
        if not lecturas:
            return []
        base = max(lecturas)
    if base == 0:
        return []

    nuevos, cambios = {}, []
    for atributo, peso in cat.atributos_de(t).items():
        delta = max(-TOPE_DELTA, min(TOPE_DELTA, _redondear(base * peso)))
        antes = ficha.get(atributo)
        if antes is None:
            continue
        despues = max(1, min(100, antes + delta))
        if despues == antes:
            continue
        nuevos[atributo] = despues
        cambios.append({'atributo': atributo, 'delta': despues - antes,
                        'antes': antes, 'despues': despues})

    if cambios:
        db.guardar_atributos(**dueno, **nuevos)
    return cambios


def enriquecer(filas, coach_id=None, con_nivel=True):
    """Añade a cada resultado lo que la pantalla necesita para dibujarlo."""
    # Quién anotó cada marca, en UNA consulta para toda la lista. En un equipo
    # con asistentes es la diferencia entre un número y un número con dueño.
    firmas = db.nombres_de([f.get('registrado_por') for f in (filas or [])])

    for f in filas or []:
        f['_firma'] = firmas.get(f.get('registrado_por'))
        t = prueba(f.get('test_clave'), coach_id) or {}
        f['_test'] = t
        f['_fecha'] = db.parse_fecha(f.get('fecha'))
        f['_campos'] = t.get('campos') or []
        f['_categoria_meta'] = cat.CATEGORIA_META.get(f.get('categoria') or 'fisico', {})

        principal = cat.campo_principal(t) if t else None
        f['_principal'] = principal
        valores = f.get('valores') or {}
        if principal and principal['clave'] in valores:
            f['_valor'] = valores[principal['clave']]
            f['_unidad'] = principal.get('unidad', '')
            f['_etiqueta_valor'] = principal.get('etiqueta', '')
        else:
            primera = next(iter(valores.items()), (None, None))
            f['_valor'] = primera[1]
            f['_unidad'] = ''
            f['_etiqueta_valor'] = primera[0] or ''

        niveles = f.get('niveles') or {}
        clave_n = principal['clave'] if principal else next(iter(niveles), None)
        f['_nivel'] = niveles.get(clave_n) if con_nivel else None
        f['_nivel_meta'] = cat.NIVEL_META.get(f['_nivel'] or '')
        f['_detalle'] = _detalle_campos(f, t, con_nivel)
    return filas or []


def _detalle_campos(fila, t, con_nivel):
    """Una línea por medida: etiqueta, valor, unidad y nivel."""
    salida = []
    valores = fila.get('valores') or {}
    niveles = fila.get('niveles') or {}
    for campo in (t.get('campos') or []):
        c = campo['clave']
        if c not in valores:
            continue
        n = niveles.get(c) if con_nivel else None
        salida.append({
            'etiqueta': campo.get('etiqueta', c),
            'valor': valores[c],
            'unidad': campo.get('unidad', ''),
            'decimales': campo.get('decimales', 2),
            'nivel': n,
            'meta': cat.NIVEL_META.get(n or ''),
            'resumen': (cat.resumen_baremo(fila.get('test_clave'), c,
                                           fila.get('contexto_edad') or 'general',
                                           fila.get('contexto_nivel') or 'general')
                        if con_nivel else ''),
        })
    return salida


def resultados_de(player_id, limite=100):
    filas = db.rows('fut_eval_results', 'evals jugador', player_id=player_id,
                    _order='fecha', _desc=True, _limit=limite) or []
    return filas


def resultados_equipo(coach_id, limite=400):
    return db.rows('fut_eval_results', 'evals equipo', coach_id=coach_id,
                   _order='fecha', _desc=True, _limit=limite) or []


def perfil_de(player_id, coach_id=None):
    """El último resultado de cada prueba: la foto actual del jugador."""
    filas = enriquecer(resultados_de(player_id, 200), coach_id)
    ultimos = {}
    for f in filas:                      # vienen de la más nueva a la más vieja
        if f['test_clave'] not in ultimos:
            ultimos[f['test_clave']] = f
    return list(ultimos.values())


def medias_por_categoria(resultados):
    """Puntaje medio por familia de pruebas: el radar del jugador."""
    suma, cuenta = {}, {}
    for r in resultados:
        p = r.get('puntaje')
        if p is None:
            continue
        c = r.get('categoria') or 'fisico'
        suma[c] = suma.get(c, 0) + p
        cuenta[c] = cuenta.get(c, 0) + 1
    salida = []
    for clave, etiqueta, emoji, _ in cat.CATEGORIAS:
        if clave in cuenta:
            salida.append({'clave': clave, 'etiqueta': etiqueta, 'emoji': emoji,
                           'puntaje': int(round(suma[clave] / cuenta[clave])),
                           'n': cuenta[clave]})
    return salida


def evolucion_de(player_id, clave_test, coach_id=None):
    """Serie temporal de una prueba para dibujar la línea de progreso."""
    filas = [f for f in resultados_de(player_id, 300)
             if f.get('test_clave') == clave_test]
    filas.sort(key=lambda f: str(f.get('fecha') or ''))
    enriquecer(filas, coach_id)
    serie = []
    for f in filas:
        if f['_valor'] is None:
            continue
        serie.append({'fecha': f['_fecha'], 'valor': f['_valor'],
                      'puntaje': f.get('puntaje'), 'nivel': f['_nivel']})
    return serie


# ═══════════════════════════════════════════════════════════════════════════
#  PANTALLAS DEL ENTRENADOR
# ═══════════════════════════════════════════════════════════════════════════
@bp.route('/coach/evaluaciones')
@login_required
def c_evaluaciones():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    jugadores = db.jugadores_del_entrenador(uid)
    manuales = db.rows('fut_manual_players', 'manuales', coach_id=uid, activo=True) or []
    resultados = enriquecer(resultados_equipo(uid, 60), uid,
                            con_nivel=roles.es_pro(current_user))

    # A quién le toca: sin evaluar nunca, o hace más de 45 días.
    ultima = {}
    for r in resultados_equipo(uid, 400):
        pid = r.get('player_id')
        f = db.parse_fecha(r.get('fecha'))
        if pid and f and (pid not in ultima or f > ultima[pid]):
            ultima[pid] = f
    limite = date.today() - timedelta(days=45)
    pendientes = [j for j in jugadores if ultima.get(j['id'], date.min) < limite]

    # Las tres cifras de la cabecera, como en TestsHomeScreen.
    todos = resultados_equipo(uid, 400)
    hoy = date.today()
    este_mes = len([r for r in todos
                    if (db.parse_fecha(r.get('fecha')) or date.min).month == hoy.month
                    and (db.parse_fecha(r.get('fecha')) or date.min).year == hoy.year])
    evaluados = len({r.get('player_id') or r.get('manual_player_id')
                     for r in todos if r.get('player_id') or r.get('manual_player_id')})
    puntajes = [r['puntaje'] for r in todos if r.get('puntaje') is not None]
    puntaje_medio = int(round(sum(puntajes) / len(puntajes))) if puntajes else None

    edad, nivel = contexto_equipo(uid)
    return render_template(
        'c_evaluaciones.html',
        tab_activa='equipo', hide_tabbar=True,
        jugadores=jugadores, manuales=manuales,
        resultados=resultados[:20],
        este_mes=este_mes, evaluados=evaluados, puntaje_medio=puntaje_medio,
        pendientes=pendientes,
        categorias=cat.CATEGORIAS,
        contexto_edad=edad, contexto_nivel=nivel,
        etiqueta_edad=dict(cat.CATEGORIAS_EDAD).get(edad, 'General'),
        etiqueta_nivel=dict((c, e) for c, e, _ in cat.NIVELES_COMPETITIVOS).get(nivel, 'General'),
        # Las listas de categorias y niveles ya no van: el ajuste se edita solo
        # en «Nivel del equipo» (c_equipo_editar). Aqui solo se enseñan las
        # etiquetas de lo que hay configurado.
        n_pruebas=len(catalogo_completo(uid)),
        # Las seis del MVP que más se usan, en su orden del catálogo.
        destacadas=[cat.test(c) for c in
                    ('sprint_30m', 'cooper', 'yoyo_ir1', 'cmj',
                     'pase_precision', 'perfil_mental')])


@bp.route('/coach/evaluaciones/catalogo')
@login_required
def c_eval_catalogo():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    from . import segmentos as seg

    uid = db.equipo_id(current_user.id)
    todas = catalogo_completo(uid)

    # Cuántas veces se ha usado cada prueba, para ordenar por lo que de verdad usa.
    usos = {}
    for r in resultados_equipo(uid, 400):
        usos[r.get('test_clave')] = usos.get(r.get('test_clave'), 0) + 1
    for t in todas:
        t['_usos'] = usos.get(t['clave'], 0)

    #  La batería del segmento. 58 pruebas avaladas son una biblioteca para un
    #  club y un muro para un profesor de colegio: ve «VO2máx directo», entiende
    #  que esto no es para él y no vuelve — aunque catorce de ellas se las pueda
    #  tomar mañana con una cinta métrica. Así que se le dice cuáles son las
    #  suyas y en qué orden, sin esconderle ninguna.
    segmento = seg.del_entrenador(uid)
    orden_bateria = {c: i for i, c in enumerate(seg.bateria(segmento))}
    avisar = seg.avisa_material(segmento)
    for t in todas:
        t['_bateria'] = orden_bateria.get(t['clave'])
        #  El aviso de material NO oculta la prueba: la marca. Un colegio con un
        #  convenio universitario puede tener acceso a un analizador de gases, y
        #  decidirlo es suyo, no nuestro.
        t['_material'] = avisar and t['clave'] in seg.PRUEBAS_CON_MATERIAL
    recomendadas = sorted((t for t in todas if t['_bateria'] is not None),
                          key=lambda t: t['_bateria'])

    #  El filtrado y la búsqueda van en el navegador, no aquí: son 58 pruebas y
    #  recargar la página por cada letra tecleada se nota. El `?c=` se sigue
    #  aceptando para que los enlaces de fuera sigan cayendo en su pestaña.
    conteos = {}
    for t in todas:
        conteos[t['categoria']] = conteos.get(t['categoria'], 0) + 1

    return render_template('c_eval_catalogo.html',
                           tab_activa='equipo', hide_tabbar=True,
                           categorias=cat.CATEGORIAS,
                           pruebas=todas,
                           recomendadas=recomendadas,
                           segmento=seg.meta(segmento),
                           conteos=conteos,
                           filtro=request.args.get('c') or '',
                           n_pruebas=len(todas),
                           n_avaladas=sum(1 for t in todas if t.get('avalado')))


@bp.route('/api/eval/ficha/<clave>')
@login_required
def api_eval_ficha(clave):
    """La ficha de una prueba: como se toma y que mide.

    Se pide suelta y no va en la pagina porque el texto de las 58 pruebas son
    44 KB, y quien mira va a abrir UNA. En el movil, con datos, eso importa.

    La ve tambien el JUGADOR, no solo el entrenador: es la explicacion de una
    prueba estandar —que mide, con que material, con que protocolo— y a quien
    se la acaban de tomar es al que mas le sirve saberlo. No lleva ningun dato
    del equipo, asi que no hay nada que proteger; lo que si depende del equipo
    son las pruebas que el entrenador se haya inventado, y por eso se resuelve
    contra SU equipo tanto si pregunta el como si pregunta uno de sus
    jugadores.
    """
    from .api import api_guard

    err = api_guard()
    if err:
        return err

    if getattr(current_user, 'role', '') == 'especialista':
        equipo = db.equipo_id(current_user.id)
    else:
        equipo = (db.entrenador_del_jugador(current_user.id) or {}).get('id')

    t = prueba(clave, equipo)
    if not t:
        return jsonify({'error': 'Esa prueba no existe.'}), 404

    return jsonify({'ok': True, 'ficha': {
        'nombre': t.get('nombre'),
        'objetivo': t.get('objetivo') or '',
        'material': t.get('material') or '',
        'protocolo': t.get('protocolo_detallado') or t.get('protocolo') or '',
        'variables': t.get('variables') or '',
        'normativa': t.get('normativa') or '',
        'bibliografia': t.get('bibliografia') or t.get('fuente') or '',
        'donde_se_usa': t.get('donde_se_usa') or '',
        'url': url_for('futbol.c_eval_ficha', clave=clave),
    }})


@bp.route('/coach/evaluaciones/ficha/<clave>')
@login_required
def c_eval_ficha(clave):
    """La ficha de una prueba: cómo se toma y contra qué se compara.

    La ruta `/test/<clave>` ya la ocupa el ranking, así que esta va por
    `/ficha/`.
    """
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    t = prueba(clave, uid)
    if not t:
        abort(404)

    edad, nivel = contexto_equipo(uid)

    # Una tabla de rangos por cada campo puntuable. El principal va primero,
    # que es el que manda en el ranking y el que mueve la ficha del jugador.
    tablas = []
    for campo in cat.campos_con_baremo(t):
        filas = cat.tabla_baremos(clave, campo['clave'], edad, nivel)
        if filas:
            tablas.append({'campo': campo, 'filas': filas,
                           'menor_mejor': campo.get('direccion') == cat.MENOR})

    usos = sum(1 for r in resultados_equipo(uid, 400) if r.get('test_clave') == clave)

    return render_template('c_eval_ficha.html',
                           tab_activa='equipo', hide_tabbar=True,
                           test=t, tablas=tablas, usos=usos,
                           contexto_edad=edad, contexto_nivel=nivel,
                           etiqueta_edad=dict(cat.CATEGORIAS_EDAD).get(edad, 'General'),
                           etiqueta_nivel=next((e for c, e, _ in cat.NIVELES_COMPETITIVOS
                                                if c == nivel), 'General'),
                           categoria_meta=cat.CATEGORIA_META.get(t['categoria'], {}))


@bp.route('/coach/evaluaciones/aplicar/<clave>')
@login_required
def c_eval_aplicar(clave):
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    t = prueba(clave, uid)
    if not t:
        abort(404)

    jugadores = db.jugadores_del_entrenador(uid)
    manuales = db.rows('fut_manual_players', 'manuales', coach_id=uid, activo=True) or []
    edad, nivel = contexto_equipo(uid)

    # El listón que se les va a aplicar, para que el entrenador lo vea antes.
    baremos = []
    for campo in t.get('campos', []):
        resumen = cat.resumen_baremo(clave, campo['clave'], edad, nivel)
        if resumen:
            baremos.append({'etiqueta': campo['etiqueta'], 'resumen': resumen})

    # Marca anterior de cada jugador: comparar en el momento vale más que
    # descubrir la mejora tres semanas después.
    previos = {}
    for r in resultados_equipo(uid, 400):
        if r.get('test_clave') != clave:
            continue
        pid = r.get('player_id') or r.get('manual_player_id')
        if pid and pid not in previos:
            previos[pid] = r

    return render_template('c_eval_aplicar.html',
                           tab_activa='equipo', hide_tabbar=True,
                           test=t, jugadores=jugadores, manuales=manuales,
                           baremos=baremos, previos=previos,
                           contexto_edad=edad, contexto_nivel=nivel,
                           es_pro=roles.es_pro(current_user),
                           hoy=db.hoy_iso())


@bp.route('/coach/evaluaciones/test/<clave>')
@login_required
def c_eval_ranking(clave):
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    if not roles.es_pro(current_user):
        return redirect(url_for('futbol.pro', f='ranking'))

    uid = db.equipo_id(current_user.id)
    t = prueba(clave, uid)
    if not t:
        abort(404)

    # El mejor registro de cada jugador, no el último: el ranking es de marcas.
    principal = cat.campo_principal(t)
    tabla, campo, direccion = ranking_de(uid, clave, t)
    stats = estadisticas([r['_valor'] for r in tabla])

    edad, nivel = contexto_equipo(uid)
    return render_template('c_eval_ranking.html',
                           tab_activa='equipo', hide_tabbar=True,
                           test=t, tabla=tabla, campo=campo,
                           media=stats['media'], stats=stats,
                           unidad=(principal or {}).get('unidad', ''),
                           menor_mejor=(direccion == cat.MENOR),
                           resumen=cat.resumen_baremo(clave, campo or '', edad, nivel),
                           contexto_edad=edad, contexto_nivel=nivel)


@bp.route('/coach/evaluaciones/jugador/<pid>')
@login_required
def c_eval_jugador(pid):
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    jugadores = db.jugadores_del_entrenador(uid)
    jugador = next((j for j in jugadores if str(j['id']) == str(pid)), None)
    manual = None
    if not jugador:
        manual = db.one('fut_manual_players', 'manual', id=pid, coach_id=uid)
        if not manual:
            abort(404)

    es_pro = roles.es_pro(current_user)
    if manual:
        filas = [f for f in resultados_equipo(uid, 400)
                 if str(f.get('manual_player_id')) == str(pid)]
        filas = enriquecer(filas, uid, con_nivel=es_pro)
    else:
        filas = enriquecer(resultados_de(pid, 200), uid, con_nivel=es_pro)

    ultimos = {}
    for f in filas:
        ultimos.setdefault(f['test_clave'], f)

    ficha = db.ficha_atributos(player_id=None if manual else pid,
                               manual_player_id=pid if manual else None)
    # La ficha médica solo la ve el entrenador cuando es un jugador SIN cuenta:
    # ahí la escribió él con lo que le dio el representante. La del jugador con
    # cuenta la escribe él y sigue siendo suya (ver futbol/salud.py).
    medico = db.ficha_medica(manual_player_id=pid) if manual else {}

    return render_template('c_eval_jugador.html',
                           tab_activa='equipo', hide_tabbar=True,
                           jugador=jugador or {'id': pid, 'name': manual['nombre'],
                                               'nombre': manual['nombre'], '_manual': True},
                           es_manual=bool(manual),
                           historial=filas[:40],
                           perfil=list(ultimos.values()),
                           radar=medias_por_categoria(list(ultimos.values())),
                           ficha=ficha,
                           medico=medico,
                           aptitud=db.APTITUD_META.get(medico.get('apto')),
                           es_pro=es_pro)


@bp.route('/coach/evaluaciones/resultado/<rid>')
@login_required
def c_eval_resultado(rid):
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    fila = db.one('fut_eval_results', 'resultado', id=rid, coach_id=uid)
    if not fila:
        abort(404)
    enriquecer([fila], uid, con_nivel=roles.es_pro(current_user))

    serie = []
    if fila.get('player_id'):
        serie = evolucion_de(fila['player_id'], fila['test_clave'], uid)

    return render_template('c_eval_resultado.html',
                           tab_activa='equipo', hide_tabbar=True,
                           r=fila, serie=serie,
                           es_pro=roles.es_pro(current_user))


@bp.route('/coach/evaluaciones/nueva')
@login_required
@roles.solo_pro('evaluaciones')
def c_eval_nueva():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    return render_template('c_eval_nueva.html',
                           tab_activa='equipo', hide_tabbar=True,
                           categorias=cat.CATEGORIAS,
                           # Por equipo_id: las pruebas propias son del
                           # EQUIPO, y un asistente no veia ninguna.
                           propias=pruebas_propias(db.equipo_id(current_user.id)))


def _recordatorio_protocolo(texto, tope=400):
    """El protocolo recortado para el paso 3, cortando por final de frase.

    En el asistente el protocolo es un recordatorio —el completo está en la
    ficha—, pero cortarlo a pelo por el carácter 400 dejaba a veinte pruebas
    terminando a mitad de palabra. Se corta en el último punto que quepa, y si
    no hay ninguno, en el último espacio.
    """
    texto = (texto or '').strip()
    if len(texto) <= tope:
        return texto
    recorte = texto[:tope]
    punto = recorte.rfind('. ')
    if punto > tope * 0.5:
        return recorte[:punto + 1]
    espacio = recorte.rfind(' ')
    return (recorte[:espacio] if espacio > 0 else recorte).rstrip(' ,;:') + '…'


@bp.route('/coach/evaluaciones/asistente')
@login_required
def c_eval_asistente():
    """Evaluar a UN jugador, guiado: jugador → prueba → marcas.

    Convive con `c_eval_aplicar`, que va al revés —prueba primero y luego toda
    la plantilla de una sentada—. No sobra ninguno: el asistente es para el día
    que mides a uno, y el otro para la tarde de tests con el equipo entero.

    Los tres pasos van en una sola página y se cambian sin recargar. Partirlo
    en tres peticiones obligaría a arrastrar el estado por la URL o por la
    sesión, y son dos listas que caben de sobra en la primera carga.
    """
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    edad, nivel = contexto_equipo(uid)

    #  Lo que el paso 3 necesita de cada prueba para dibujar sus casillas. Se
    #  manda todo de una porque la prueba se elige en el navegador.
    pruebas = catalogo_completo(uid)
    detalle = {}
    for t in pruebas:
        detalle[t['clave']] = {
            'nombre': t['nombre'],
            'categoria': t['categoria'],
            'protocolo': _recordatorio_protocolo(t.get('protocolo')),
            'campos': [{'clave': c['clave'], 'etiqueta': c['etiqueta'],
                        'unidad': c.get('unidad') or '',
                        'decimales': c.get('decimales', 2),
                        'min': c.get('min'), 'max': c.get('max'),
                        'ejemplo': c.get('ejemplo') or ''}
                       for c in (t.get('campos') or [])],
            #  El listón de la categoría del equipo, para que el entrenador vea
            #  contra qué se compara antes de anotar y no después.
            'baremos': [{'etiqueta': c['etiqueta'],
                         'resumen': cat.resumen_baremo(t['clave'], c['clave'], edad, nivel)}
                        for c in (t.get('campos') or [])
                        if cat.resumen_baremo(t['clave'], c['clave'], edad, nivel)],
        }

    return render_template('c_eval_asistente.html',
                           tab_activa='equipo', hide_tabbar=True,
                           jugadores=db.jugadores_del_entrenador(uid),
                           manuales=db.rows('fut_manual_players', 'manuales',
                                            coach_id=uid, activo=True) or [],
                           pruebas=pruebas, detalle=detalle,
                           contexto_edad=edad, contexto_nivel=nivel,
                           etiqueta_edad=dict(cat.CATEGORIAS_EDAD).get(edad, 'General'),
                           etiqueta_nivel=next((e for c, e, _ in cat.NIVELES_COMPETITIVOS
                                                if c == nivel), 'General'),
                           es_pro=roles.es_pro(current_user),
                           hoy=db.hoy_iso())


@bp.route('/coach/evaluaciones/rankings')
@login_required
def c_eval_rankings():
    """Las pruebas que ya tienen marcas, para entrar al ranking de cada una.

    El ranking es siempre de UNA prueba —no tiene sentido ordenar juntos un
    sprint y un Yo-Yo—, así que hace falta este paso intermedio para elegirla.
    """
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    conteo, ultima = {}, {}
    for r in resultados_equipo(uid, 400):
        clave = r.get('test_clave')
        if not clave:
            continue
        conteo[clave] = conteo.get(clave, 0) + 1
        fecha = db.parse_fecha(r.get('fecha'))
        if fecha and (clave not in ultima or fecha > ultima[clave]):
            ultima[clave] = fecha

    filas = []
    for clave, n in conteo.items():
        t = prueba(clave, uid)
        if not t:
            continue
        filas.append({'test': t, 'n': n, 'ultima': ultima.get(clave)})
    filas.sort(key=lambda f: (-f['n'], f['test']['nombre']))

    return render_template('c_eval_rankings.html',
                           tab_activa='equipo', hide_tabbar=True,
                           filas=filas, es_pro=roles.es_pro(current_user))


@bp.route('/coach/evolucion')
@login_required
@roles.solo_pro('evolucion')
def c_evolucion():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    #  TODA la plantilla, con cuenta y sin ella. Con `jugadores_del_entrenador`
    #  esta pantalla dejaba fuera a los apuntados a mano: en el equipo real hay
    #  19 y ninguno tiene cuenta, así que la media del equipo salía calculada
    #  con sus marcas y debajo no aparecía nadie. Es el mismo despiste que ya
    #  hubo con la asistencia y con el contexto de la IA, y por eso existe
    #  `db.plantilla_completa`.
    jugadores = [{'id': j['id'], 'name': j['nombre'], 'profile_photo': j.get('foto'),
                  'es_manual': j['es_manual']}
                 for j in db.plantilla_completa(uid)]
    todos = enriquecer(resultados_equipo(uid, 400), uid)

    # Puntaje medio del equipo por mes: la línea que enseña si se progresa.
    por_mes = {}
    for r in todos:
        if r.get('puntaje') is None or not r['_fecha']:
            continue
        k = r['_fecha'].strftime('%Y-%m')
        por_mes.setdefault(k, []).append(r['puntaje'])
    meses = [{'mes': k, 'puntaje': int(round(sum(v) / len(v))), 'n': len(v)}
             for k, v in sorted(por_mes.items())][-12:]

    # Ficha resumida por jugador, ordenada por quién está mejor.
    resumen = []
    for j in jugadores:
        columna = 'manual_player_id' if j['es_manual'] else 'player_id'
        suyos = [r for r in todos if str(r.get(columna)) == str(j['id'])]
        ultimos = {}
        for r in suyos:
            ultimos.setdefault(r['test_clave'], r)
        puntajes = [r['puntaje'] for r in ultimos.values() if r.get('puntaje') is not None]
        resumen.append({
            'jugador': j, 'n': len(suyos),
            'puntaje': int(round(sum(puntajes) / len(puntajes))) if puntajes else None,
            'radar': medias_por_categoria(list(ultimos.values())),
            'ultima': max((r['_fecha'] for r in suyos if r['_fecha']), default=None),
        })
    resumen.sort(key=lambda x: (x['puntaje'] is None, -(x['puntaje'] or 0)))

    puntajes_eq = [x['puntaje'] for x in resumen if x['puntaje'] is not None]
    return render_template('c_evolucion.html',
                           tab_activa='equipo', hide_tabbar=True,
                           meses=meses, resumen=resumen,
                           media_equipo=(int(round(sum(puntajes_eq) / len(puntajes_eq)))
                                         if puntajes_eq else None),
                           radar_equipo=medias_por_categoria(todos),
                           n_evaluaciones=len(todos))


# ═══════════════════════════════════════════════════════════════════════════
#  PANTALLAS DEL JUGADOR
# ═══════════════════════════════════════════════════════════════════════════
@bp.route('/evaluaciones')
@login_required
def p_evaluaciones():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_evaluaciones'))

    uid = current_user.id
    es_pro = roles.es_pro(current_user)
    coach = db.entrenador_del_jugador(uid)
    filas = enriquecer(resultados_de(uid, 120), (coach or {}).get('id'), con_nivel=es_pro)

    ultimos = {}
    for f in filas:
        ultimos.setdefault(f['test_clave'], f)
    perfil = list(ultimos.values())
    puntajes = [r['puntaje'] for r in perfil if r.get('puntaje') is not None]

    return render_template('p_evaluaciones.html',
                           tab_activa='progreso',
                           historial=filas[:40], perfil=perfil,
                           radar=medias_por_categoria(perfil) if es_pro else [],
                           media=(int(round(sum(puntajes) / len(puntajes)))
                                  if puntajes and es_pro else None),
                           entrenador=coach, es_pro=es_pro)


@bp.route('/evaluaciones/<rid>')
@login_required
def p_eval_detalle(rid):
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_eval_resultado', rid=rid))

    uid = current_user.id
    fila = db.one('fut_eval_results', 'mi resultado', id=rid, player_id=uid)
    if not fila:
        abort(404)
    es_pro = roles.es_pro(current_user)
    enriquecer([fila], fila.get('coach_id'), con_nivel=es_pro)

    return render_template('p_eval_detalle.html',
                           tab_activa='progreso', hide_tabbar=True,
                           r=fila, es_pro=es_pro,
                           serie=evolucion_de(uid, fila['test_clave']) if es_pro else [])


@bp.route('/evolucion')
@login_required
@roles.solo_pro('evolucion')
def p_evolucion():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_evolucion'))

    uid = current_user.id
    coach = db.entrenador_del_jugador(uid)
    filas = enriquecer(resultados_de(uid, 300), (coach or {}).get('id'))

    ultimos = {}
    for f in filas:
        ultimos.setdefault(f['test_clave'], f)
    perfil = list(ultimos.values())

    # Cada prueba con más de una toma: dónde se ve el progreso.
    series = []
    por_test = {}
    for f in filas:
        por_test.setdefault(f['test_clave'], []).append(f)
    for clave, lista in por_test.items():
        if len(lista) < 2:
            continue
        lista = sorted(lista, key=lambda f: str(f.get('fecha') or ''))
        primero, ultimo = lista[0], lista[-1]
        if primero['_valor'] is None or ultimo['_valor'] is None:
            continue
        t = prueba(clave, (coach or {}).get('id')) or {}
        principal = cat.campo_principal(t) or {}
        menor_mejor = principal.get('direccion') == cat.MENOR
        delta = ultimo['_valor'] - primero['_valor']
        series.append({
            'test': t, 'clave': clave, 'n': len(lista),
            'primero': primero, 'ultimo': ultimo,
            'delta': round(delta, 2),
            'mejora': (delta < 0) if menor_mejor else (delta > 0),
            'unidad': principal.get('unidad', ''),
            'puntos': [{'fecha': f['_fecha'], 'valor': f['_valor'],
                        'puntaje': f.get('puntaje')} for f in lista],
        })
    series.sort(key=lambda s: -s['n'])

    puntajes = [r['puntaje'] for r in perfil if r.get('puntaje') is not None]
    return render_template('p_evolucion.html',
                           tab_activa='progreso', hide_tabbar=True,
                           series=series, radar=medias_por_categoria(perfil),
                           media=(int(round(sum(puntajes) / len(puntajes)))
                                  if puntajes else None),
                           n=len(filas))


# ═══════════════════════════════════════════════════════════════════════════
#  API
# ═══════════════════════════════════════════════════════════════════════════
def _guardia_coach():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el entrenador evalúa.'}), 403
    return None


@bp.route('/api/eval/resultado', methods=['POST'])
@login_required
def api_eval_guardar():
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)
    clave = d.get('test')
    entradas = d.get('resultados') or []
    if not clave or not entradas:
        return jsonify({'error': 'Faltan datos.'}), 400

    jugadores = {str(j['id']): j for j in db.jugadores_del_entrenador(uid)}
    manuales = {str(m['id']): m for m in
                (db.rows('fut_manual_players', 'manuales', coach_id=uid) or [])}

    guardados, errores, movidos = [], [], []
    for e in entradas:
        pid = str(e.get('player_id') or '')
        es_manual = bool(e.get('manual'))

        if es_manual:
            m = manuales.get(pid)
            if not m:
                errores.append('Un jugador apuntado a mano ya no está en tu equipo.')
                continue
            jugador = {'id': None, 'nombre': m['nombre'],
                       'anio_nacimiento': m.get('anio_nacimiento'),
                       'fecha_nacimiento': m.get('fecha_nacimiento')}
            manual_id = m['id']
        else:
            j = jugadores.get(pid)
            if not j:
                errores.append('Ese jugador no es de tu plantilla.')
                continue
            jugador = j
            manual_id = None

        fila, error = guardar_resultado(uid, jugador, clave, e.get('valores'),
                                        e.get('fecha'), e.get('notas'),
                                        manual_id=manual_id,
                                        registrado_por=current_user.id)
        if error:
            nombre = jugador.get('nombre') or jugador.get('name') or '?'
            errores.append(f'{nombre}: {error}')
        elif fila:
            guardados.append(fila['id'])
            if fila.get('_cambios'):
                movidos.append(fila['_cambios'])

    if not guardados:
        return jsonify({'error': errores[0] if errores else 'No se guardó nada.'}), 400

    # Que el entrenador se entere de que la marca no se quedó en una tabla.
    # Va por flash y no en la respuesta porque justo después hay redirección.
    if movidos:
        tocados = sorted({c['atributo'] for cambios in movidos for c in cambios})
        flash('Esta prueba movió la ficha de {} jugador{}: {}.'.format(
            len(movidos), '' if len(movidos) == 1 else 'es',
            ', '.join(NOMBRE_ATRIBUTO.get(a, a) for a in tocados)), 'success')

    return jsonify({'ok': True, 'n': len(guardados), 'ids': guardados,
                    'avisos': errores,
                    'redirect': url_for('futbol.c_eval_ranking', clave=clave)
                                if roles.es_pro(current_user) else
                                url_for('futbol.c_evaluaciones')})


@bp.route('/api/eval/resultado/<rid>', methods=['DELETE'])
@login_required
def api_eval_borrar(rid):
    error = _guardia_coach()
    if error:
        return error
    db.delete('fut_eval_results', 'borrar eval', id=rid, coach_id=db.equipo_id(current_user.id), obligatorio=True)
    return jsonify({'ok': True})


@bp.route('/api/eval/contexto', methods=['POST'])
@login_required
def api_eval_contexto():
    error = _guardia_coach()
    if error:
        return error
    d = request.get_json(silent=True) or {}
    edad = d.get('categoria_edad') or 'general'
    nivel = d.get('nivel') or 'general'
    if edad not in dict(cat.CATEGORIAS_EDAD):
        return jsonify({'error': 'Categoría de edad no válida.'}), 400
    if nivel not in dict((c, e) for c, e, _ in cat.NIVELES_COMPETITIVOS):
        return jsonify({'error': 'Nivel no válido.'}), 400
    # Sobre el EQUIPO, no sobre quien guarda: si lo cambia un asistente tiene
    # que caer en la ficha del principal, que es la que leen los baremos.
    guardar_contexto(db.equipo_id(current_user.id), edad, nivel)
    return jsonify({'ok': True,
                    'mensaje': 'Listo. Las próximas evaluaciones se comparan con '
                               'ese baremo.'})


@bp.route('/api/eval/test', methods=['POST'])
@login_required
def api_eval_test_crear():
    error = _guardia_coach()
    if error:
        return error
    if not roles.es_pro(current_user):
        return jsonify({'error': 'Crear pruebas propias es del plan Pro.',
                        'pro': True}), 402

    d = request.get_json(silent=True) or {}
    nombre = (d.get('nombre') or '').strip()
    if len(nombre) < 3:
        return jsonify({'error': 'Ponle un nombre a la prueba.'}), 400

    campos = []
    for c in (d.get('campos') or [])[:8]:
        etiqueta = (c.get('etiqueta') or '').strip()
        if not etiqueta:
            continue
        # La clave sale de la posición, no del texto: si el entrenador renombra
        # «Tiempo» a «Tiempo total», los resultados ya guardados seguirían valiendo.
        campos.append({
            'clave': f'c{len(campos) + 1}',
            'etiqueta': etiqueta[:60],
            'unidad': (c.get('unidad') or '')[:12],
            'min': None, 'max': None,
            'decimales': int(c.get('decimales') or 2),
            'ejemplo': (c.get('ejemplo') or '')[:20],
            'direccion': (cat.MENOR if c.get('direccion') == cat.MENOR else cat.MAYOR),
            'principal': len(campos) == 0,
            'tipo': 'numero',
        })
    if not campos:
        return jsonify({'error': 'Añade al menos una medida.'}), 400

    fila = db.insert('fut_eval_templates', {
        'coach_id': db.equipo_id(current_user.id),
        'clave': f'propia:{uuid.uuid4().hex[:12]}',
        'nombre': nombre[:120],
        'categoria': (d.get('categoria') if d.get('categoria') in dict(
            (c, e) for c, e, _, _ in cat.CATEGORIAS) else 'fisico'),
        'descripcion': (d.get('descripcion') or '')[:500],
        'protocolo': (d.get('protocolo') or '')[:2000],
        'campos': campos,
        'icono': 'activity',
        'creado': _ahora(),
    }, 'crear prueba propia')

    if not fila:
        return jsonify({'error': 'No se pudo crear la prueba.'}), 500
    return jsonify({'ok': True, 'clave': fila['clave'],
                    'redirect': url_for('futbol.c_eval_aplicar', clave=fila['clave'])})


@bp.route('/api/eval/test/<tid>', methods=['DELETE'])
@login_required
def api_eval_test_borrar(tid):
    error = _guardia_coach()
    if error:
        return error
    db.delete('fut_eval_templates', 'borrar prueba', id=tid, coach_id=db.equipo_id(current_user.id), obligatorio=True)
    return jsonify({'ok': True})
