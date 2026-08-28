# -*- coding: utf-8 -*-
"""
futbol/microciclos.py — Planificación semanal del equipo.

Un microciclo es la semana de trabajo del equipo. Es la planilla que el cuerpo
técnico imprime y cuelga: los días en columnas, las capacidades en filas. La
forma sale de una planilla real de club (Cantera Orense, «MICRO 7»).

Encima de la planilla va una capa de periodización: cada día sabe qué lugar
ocupa en la semana y qué carga lleva. De ahí salen la gráfica de carga y los
avisos de la guía.

Este archivo es el MOTOR: la planilla, el guardado, la gráfica y el volcado al
calendario. Lo que cambia de un tipo de equipo a otro —qué días tiene la
semana, cómo se llaman las filas, qué principios respaldan el plan y de qué se
avisa— vive en `microciclo_modelos.py`, un modelo por segmento:

    profesional   La periodización de élite. Semana de partido a partido.
    semipro       Tres sesiones, jugadores que trabajan, sin fisioterapeuta.
    colegio       La semana lectiva. El objetivo no es la jornada del sábado.

El segmento sale del equipo (`futbol/segmentos.py`). Un microciclo GUARDA el
suyo: si el entrenador cambia de segmento después, las semanas viejas se siguen
leyendo con el modelo con el que se escribieron, que es lo honesto — esa semana
se pensó así.
"""
from datetime import date, datetime, timedelta, timezone

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles

from . import bp, db
from . import microciclo_modelos as modelos
from . import segmentos as seg


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _coach_o_fuera():
    """Estas pantallas son del cuerpo técnico. Un jugador va a lo suyo."""
    if getattr(current_user, 'role', '') != 'especialista':
        #  `futbol.inicio`, que es como se llama de verdad. Con `p_inicio`
        #  —el nombre de la PLANTILLA, no del endpoint— este redirect no se
        #  podia construir y la pantalla contestaba 500: al jugador con Pro
        #  que abriera esta direccion le reventaba en vez de echarlo.
        return redirect(url_for('futbol.inicio'))
    return None


def _modelo_del_equipo():
    """El modelo de periodización que le toca a quien está mirando."""
    return modelos.de_segmento(seg.del_entrenador(db.equipo_id(current_user.id)))


def _modelo_del_micro(micro):
    """El modelo con el que se escribió ESTA semana.

    Los microciclos creados antes de que existieran los segmentos no tienen la
    columna rellena y caen en `profesional`, que es exactamente lo que eran.
    """
    return modelos.de_segmento((micro or {}).get('segmento'))


# ═══════════════════════════════════════════════════════════════════════════
#  ARMAR Y LEER UN MICROCICLO
# ═══════════════════════════════════════════════════════════════════════════
DIAS_SEMANA = ('LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO')


def etiqueta_fecha(f):
    """'LUNES 11' — como se rotula la columna en la planilla impresa."""
    if not f:
        return ''
    return f'{DIAS_SEMANA[f.weekday()]} {f.day}'


def plantilla(modelo, rotacion, desde=None):
    """Los días que sugiere el modelo para una rotación, ya rellenos.

    Es el punto de partida del planificador: el entrenador abre una semana
    nueva y ya tiene la forma puesta, con la carga y la capacidad de cada día.
    Encima escribe lo suyo.
    """
    rotaciones = modelo['rotaciones']
    rotacion = rotacion if rotacion in rotaciones else 7
    desde = desde or date.today()
    salida = []
    for i, md in enumerate(rotaciones[rotacion]):
        guia = modelo['dias'][md]
        f = desde + timedelta(days=i)
        dia = {
            'fecha': f.isoformat(),
            'etiqueta': etiqueta_fecha(f),
            'md': md,
            'carga': guia['carga'],
            'capacidad': guia['capacidad'],
            'lugar': '', 'hora': '', 'duracion': 0,
        }
        for clave in modelos.CLAVES_CAMPOS:
            dia[clave] = ''
        salida.append(dia)
    return salida


def decorar(micro, modelo=None):
    """Añade a cada día lo que la plantilla necesita para pintarlo.

    Nada de esto se guarda: son la carga, la fase y el consejo del día,
    derivados de su posición en la semana según el modelo del segmento.
    """
    modelo = modelo or _modelo_del_micro(micro)
    carga_meta, fase_meta = modelo['carga_meta'], modelo['fase_meta']
    dias = micro.get('dias') or []
    for d in dias:
        guia = modelo['dias'].get(d.get('md') or '', {})
        carga = d.get('carga') if d.get('carga') in carga_meta else guia.get('carga', 'baja')
        d['_carga'] = carga_meta.get(carga, carga_meta['baja'])
        d['_carga_clave'] = carga
        d['_fase'] = fase_meta.get(guia.get('fase', 'adquisicion'), fase_meta['adquisicion'])
        d['_foco'] = guia.get('foco', '')
        d['_detalle'] = guia.get('detalle', '')
        d['_principios'] = guia.get('principios', ())
        #  Un día se considera escrito si tiene algo en cualquiera de sus
        #  bloques. Sirve para la barra de «cuánto llevas planificado».
        d['_escrito'] = any((d.get(k) or '').strip() for k in modelos.CLAVES_CAMPOS)

    micro['_dias'] = dias
    micro['_modelo'] = modelo
    micro['_segmento'] = seg.meta(modelo['segmento'])
    micro['_rotacion'] = micro.get('rotacion') or len(dias) or 7
    micro['_aviso'] = modelo['aviso_rotacion'].get(micro['_rotacion'], '')
    micro['_escritos'] = sum(1 for d in dias if d['_escrito'])
    micro['_desde'] = db.parse_fecha(micro.get('desde'))
    micro['_hasta'] = db.parse_fecha(micro.get('hasta'))
    #  Minutos de la semana: solo cuentan los días con duración puesta.
    micro['_minutos'] = sum(int(d.get('duracion') or 0) for d in dias)
    return micro


# ═══════════════════════════════════════════════════════════════════════════
#  PANTALLAS
# ═══════════════════════════════════════════════════════════════════════════
@bp.route('/coach/microciclos')
@login_required
@roles.solo_pro('planes')
def c_microciclos():
    """La lista de semanas del equipo."""
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    uid = db.equipo_id(current_user.id)
    segmento = seg.del_entrenador(uid)
    modelo = modelos.de_segmento(segmento)
    micros = db.rows('fut_microcycles', 'microciclos', coach_id=uid,
                     _order='desde', _desc=True) or []
    for m in micros:
        #  Cada uno con SU modelo: en la lista pueden convivir semanas escritas
        #  antes y después de un cambio de segmento.
        decorar(m)
    return render_template('c_microciclos.html',
                           tab_activa='agenda', hide_tabbar=True,
                           micros=micros,
                           modelo=modelo,
                           segmento=seg.meta(segmento),
                           palabras=seg.palabras(segmento),
                           rotaciones=sorted(modelo['rotaciones'], reverse=True),
                           avisos_rotacion=modelo['aviso_rotacion'],
                           hoy=date.today().isoformat())


@bp.route('/coach/microciclos/<mid>')
@login_required
@roles.solo_pro('planes')
def c_microciclo(mid):
    """El planificador: la semana entera, editable."""
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    uid = db.equipo_id(current_user.id)
    micro = db.one('fut_microcycles', 'microciclo', id=mid, coach_id=uid)
    if not micro:
        abort(404)
    modelo = _modelo_del_micro(micro)
    decorar(micro, modelo)
    return render_template('c_microciclo.html',
                           tab_activa='agenda', hide_tabbar=True,
                           micro=micro,
                           modelo=modelo,
                           segmento=seg.meta(modelo['segmento']),
                           palabras=seg.palabras(modelo['segmento']),
                           campos=modelo['campos'],
                           bloques=modelo['bloques'],
                           capacidades=modelo['capacidades'],
                           cargas=modelo['cargas'],
                           dias_md=modelo['dias'],
                           rotaciones=sorted(modelo['rotaciones'], reverse=True),
                           principios=modelo['principios'],
                           avisos=modelo['revisar'](micro['_dias']),
                           fuentes=modelo['fuentes'],
                           fuente=modelo['fuente'])


@bp.route('/coach/microciclos/guia')
@login_required
@roles.solo_pro('planes')
def c_microciclo_guia():
    """Los principios del segmento, en limpio."""
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    segmento = seg.del_entrenador(db.equipo_id(current_user.id))
    modelo = modelos.de_segmento(segmento)
    #  Las rotaciones dibujadas con su carga día a día: es la figura que resume
    #  el modelo entero y la que de verdad se consulta.
    formas = []
    for r in sorted(modelo['rotaciones'], reverse=True):
        formas.append({
            'rotacion': r,
            'aviso': modelo['aviso_rotacion'].get(r, ''),
            'dias': [{'md': md,
                      'carga': modelo['carga_meta'][modelo['dias'][md]['carga']],
                      'fase': modelo['fase_meta'][modelo['dias'][md]['fase']],
                      'foco': modelo['dias'][md]['foco']}
                     for md in modelo['rotaciones'][r]],
        })
    return render_template('c_microciclo_guia.html',
                           tab_activa='agenda', hide_tabbar=True,
                           modelo=modelo,
                           segmento=seg.meta(segmento),
                           palabras=seg.palabras(segmento),
                           objetivos=seg.objetivos(segmento),
                           principios=modelo['principios'],
                           formas=formas,
                           fases=modelo['fases'],
                           dias_md=modelo['dias'],
                           fuentes=modelo['fuentes'],
                           fuente=modelo['fuente'])


# ═══════════════════════════════════════════════════════════════════════════
#  API
# ═══════════════════════════════════════════════════════════════════════════
def _guardia_coach():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el cuerpo técnico planifica la semana.'}), 403
    if not roles.es_pro(current_user):
        return jsonify({'error': 'La planificación semanal es del plan Pro.',
                        'pro': True, 'url': url_for('futbol.planes')}), 402
    return None


def _minutos(v):
    """Los minutos de una sesión, venga como venga.

    El formulario manda un número, pero el servidor no puede fiarse de eso: un
    «90 min» escrito a mano reventaba la petición ENTERA y el entrenador perdía
    la semana que acababa de escribir por un campo.
    """
    try:
        return max(0, min(300, int(float(str(v).strip() or 0))))
    except (TypeError, ValueError):
        return 0


def _limpiar_dia(d, modelo):
    """Un día tal y como se guarda. Todo recortado y dentro de su vocabulario."""
    md = d.get('md') if d.get('md') in modelo['dias'] else ''
    carga = d.get('carga') if d.get('carga') in modelo['carga_meta'] else 'baja'
    salida = {
        'fecha': (d.get('fecha') or '')[:10],
        'etiqueta': (d.get('etiqueta') or '').strip()[:40],
        'md': md,
        'carga': carga,
        #  La capacidad admite texto libre a propósito: las del modelo son las
        #  sugerencias, no una lista cerrada — cada cuerpo técnico tiene su
        #  vocabulario y no se le va a corregir.
        'capacidad': (d.get('capacidad') or '').strip()[:60],
        'lugar': (d.get('lugar') or '').strip()[:80],
        'hora': (d.get('hora') or '').strip()[:5],
        'duracion': _minutos(d.get('duracion')),
    }
    for clave in modelos.CLAVES_CAMPOS:
        salida[clave] = (d.get(clave) or '').strip()[:600]
    return salida


@bp.route('/api/microciclo', methods=['POST'])
@login_required
def api_microciclo():
    """Crea o actualiza un microciclo entero.

    Siempre llega la semana completa: un microciclo se lee y se escribe de una
    pieza, como la planilla que representa.
    """
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)

    nombre = (d.get('nombre') or '').strip()
    if len(nombre) < 3:
        return jsonify({'error': 'Ponle un nombre al microciclo.'}), 400

    mid = d.get('id')
    #  El modelo con el que se valida es el de la semana si ya existe, y el del
    #  equipo si es nueva. Si se validara siempre con el del equipo, un
    #  entrenador que cambió de segmento vería cómo al guardar una semana vieja
    #  se le vacían todos los días (su `md` no existe en el modelo nuevo).
    existente = db.one('fut_microcycles', 'micro mio', id=mid, coach_id=uid) if mid else None
    if mid and not existente:
        return jsonify({'error': 'Ese microciclo no es tuyo.'}), 403
    segmento = (existente or {}).get('segmento') if existente else seg.del_entrenador(uid)
    modelo = modelos.de_segmento(segmento)

    try:
        rotacion = int(d.get('rotacion') or 7)
    except (TypeError, ValueError):
        rotacion = 7
    rotacion = rotacion if rotacion in modelo['rotaciones'] else 7

    dias = [_limpiar_dia(x, modelo) for x in (d.get('dias') or [])[:8]]
    if not dias:
        dias = plantilla(modelo, rotacion, db.parse_fecha(d.get('desde')))

    #  El rango de fechas sale de los días: es un dato derivado y así no puede
    #  contradecir a la planilla.
    fechas = sorted(f for f in (x['fecha'] for x in dias) if f)

    datos = {
        'nombre': nombre[:120],
        'lugar': (d.get('lugar') or '').strip()[:120],
        'rotacion': rotacion,
        'dias': dias,
        'desde': fechas[0] if fechas else None,
        'hasta': fechas[-1] if fechas else None,
        'recomendaciones': (d.get('recomendaciones') or '').strip()[:1200],
        'observaciones': (d.get('observaciones') or '').strip()[:1200],
        'cuerpo_tecnico': (d.get('cuerpo_tecnico') or '').strip()[:300],
        'actualizado': _ahora(),
    }

    if mid:
        db.update('fut_microcycles', datos, 'micro up', id=mid, coach_id=uid,
                  obligatorio=True)
        return jsonify({'ok': True, 'id': mid, 'mensaje': 'Microciclo guardado.',
                        'avisos': modelo['revisar'](dias)})

    datos.update({'coach_id': uid, 'segmento': modelo['segmento'], 'creado': _ahora()})
    fila = db.insert('fut_microcycles', datos, 'micro nuevo')
    if not fila:
        return jsonify({'error': 'No se pudo guardar el microciclo.'}), 500
    return jsonify({'ok': True, 'id': fila['id'], 'mensaje': 'Microciclo creado.',
                    'redirect': url_for('futbol.c_microciclo', mid=fila['id'])})


@bp.route('/api/microciclo/nuevo', methods=['POST'])
@login_required
def api_microciclo_nuevo():
    """Crea un microciclo ya con la forma que sugiere el modelo del segmento."""
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)
    modelo = modelos.de_segmento(seg.del_entrenador(uid))
    try:
        rotacion = int(d.get('rotacion') or 7)
    except (TypeError, ValueError):
        rotacion = 7
    rotacion = rotacion if rotacion in modelo['rotaciones'] else 7

    desde = db.parse_fecha(d.get('desde')) or date.today()
    dias = plantilla(modelo, rotacion, desde)
    equipo = db.equipo_del_entrenador(uid) or {}

    fila = db.insert('fut_microcycles', {
        'coach_id': uid,
        'segmento': modelo['segmento'],
        'nombre': (d.get('nombre') or '').strip()[:120] or f'Microciclo {desde.strftime("%d/%m")}',
        'lugar': (d.get('lugar') or '').strip()[:120] or (equipo.get('nombre') or ''),
        'rotacion': rotacion,
        'dias': dias,
        'desde': dias[0]['fecha'],
        'hasta': dias[-1]['fecha'],
        'creado': _ahora(),
    }, 'micro plantilla')
    if not fila:
        return jsonify({'error': 'No se pudo crear el microciclo.'}), 500
    return jsonify({'ok': True, 'id': fila['id'],
                    'redirect': url_for('futbol.c_microciclo', mid=fila['id'])})


@bp.route('/api/microciclo/<mid>', methods=['DELETE'])
@login_required
def api_microciclo_borrar(mid):
    error = _guardia_coach()
    if error:
        return error
    db.delete('fut_microcycles', 'borrar micro', id=mid,
              coach_id=db.equipo_id(current_user.id), obligatorio=True)
    return jsonify({'ok': True, 'mensaje': 'Microciclo borrado.'})


@bp.route('/api/microciclo/<mid>/agendar', methods=['POST'])
@login_required
def api_microciclo_agendar(mid):
    """Vuelca la semana al calendario: un evento por día escrito.

    Es lo que cierra el círculo — el microciclo deja de ser una hoja y pasa a
    ser la agenda real del equipo, con su asistencia y sus estadísticas.
    """
    error = _guardia_coach()
    if error:
        return error

    uid = db.equipo_id(current_user.id)
    micro = db.one('fut_microcycles', 'micro agendar', id=mid, coach_id=uid)
    if not micro:
        return jsonify({'error': 'Ese microciclo no es tuyo.'}), 404
    modelo = _modelo_del_micro(micro)
    #  Las etiquetas del volcado son las del modelo: en un colegio el evento
    #  del calendario tiene que decir «Juego reducido», no «Táctico».
    campos = modelo['campos']

    creados = 0
    for d in (micro.get('dias') or []):
        fecha = (d.get('fecha') or '')[:10]
        if not fecha or d.get('carga') == 'descanso':
            continue

        #  Solo se agendan los días con contenido: un día en blanco en la
        #  planilla no es una sesión, es un hueco por rellenar.
        cuerpo = [f'{etiqueta}: {d[clave].strip()}'
                  for clave, etiqueta in campos if (d.get(clave) or '').strip()]
        if not cuerpo:
            continue

        guia = modelo['dias'].get(d.get('md') or '', {})
        es_partido = guia.get('fase') == 'partido'
        fila = db.insert('fut_events', {
            'coach_id': uid,
            'tipo': 'partido' if es_partido else 'entreno',
            'titulo': (f'{micro["nombre"]} · {d.get("md") or ""}').strip()[:120],
            'fecha': fecha,
            'hora': (d.get('hora') or '')[:5] or None,
            'lugar': (d.get('lugar') or micro.get('lugar') or '')[:120],
            'descripcion': ('\n'.join(cuerpo))[:1200],
            #  Por `_minutos` y no por `int()` a pelo: al guardar ya se sanea,
            #  pero una fila escrita antes de que eso existiera —o a mano— tiene
            #  la duración como texto, y aquí tumbaba el volcado entero con un
            #  500. La misma función está dos pantallas más arriba.
            'duracion_min': _minutos(d.get('duracion')) or 90,
            'intensidad': {'partido': 'muy_alta', 'alta': 'alta', 'media': 'media',
                           'baja': 'baja', 'descanso': 'baja'}.get(d.get('carga'), 'media'),
            'estado': 'programado',
            'creado': _ahora(),
        }, 'evento del microciclo')
        if fila:
            creados += 1

    if not creados:
        return jsonify({'error': 'No hay ningún día escrito para agendar todavía.'}), 400
    return jsonify({'ok': True, 'n': creados,
                    'mensaje': f'{creados} sesión(es) en el calendario.',
                    'redirect': url_for('futbol.c_calendario')})
