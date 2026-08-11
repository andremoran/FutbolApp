# -*- coding: utf-8 -*-
"""
futbol/calendario.py — Calendario, entrenamientos y asistencia.

Lo que había antes era una lista de eventos. Un calendario de verdad tiene que
responder a tres preguntas que una lista no responde:

  ¿Qué hay este mes?      → rejilla mensual con un punto por evento.
  ¿Cuánto estamos cargando? → carga semanal = minutos × factor de intensidad,
                              con avisos si hay partido cerca o exceso.
  ¿Quién vino?             → asistencia con cuatro estados y su porcentaje.

Los planes de entrenamiento son sesiones guardadas: se arman una vez y se
vuelcan al calendario cuantas veces haga falta, que es como trabaja de verdad
un entrenador con una pretemporada de doce semanas.
"""
import logging
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles

from . import bp, db

logger = logging.getLogger(__name__)


# ─── Vocabulario ────────────────────────────────────────────────────────────
TIPOS_EVENTO = [
    ('entreno',  'Entrenamiento', '🏃', '#3b82f6'),
    ('partido',  'Partido',       '⚽', '#ef4444'),
    ('descanso', 'Descanso',      '🌙', '#94a3b8'),
    ('reunion',  'Reunión',       '👥', '#f97316'),
    ('medico',   'Médico',        '🏥', '#06b6d4'),
    ('test',     'Evaluación',    '📊', '#8b5cf6'),
]
TIPO_META = {c: {'etiqueta': e, 'emoji': m, 'color': col}
             for c, e, m, col in TIPOS_EVENTO}

TIPOS_ENTRENO = [
    ('fisico',  'Físico',  '#3b82f6'),
    ('tecnico', 'Técnico', '#10b981'),
    ('tactico', 'Táctico', '#f59e0b'),
    ('mental',  'Mental',  '#8b5cf6'),
    ('mixto',   'Mixto',   '#64748b'),
]
ENTRENO_META = {c: {'etiqueta': e, 'color': col} for c, e, col in TIPOS_ENTRENO}

# El factor convierte minutos en carga: 90 minutos suaves no cansan como 90 al
# límite. Es la idea del RPE de sesión de Foster, simplificada a cuatro peldaños.
INTENSIDADES = [
    ('baja',     'Suave',    0.5),
    ('media',    'Media',    1.0),
    ('alta',     'Alta',     1.5),
    ('muy_alta', 'Máxima',   2.0),
]
FACTOR = {c: f for c, _, f in INTENSIDADES}
INTENSIDAD_META = {c: {'etiqueta': e, 'factor': f} for c, e, f in INTENSIDADES}

ESTADOS_ASISTENCIA = [
    ('presente',  'Presente',    '✅', '#10b981'),
    ('ausente',   'Ausente',     '❌', '#ef4444'),
    ('tarde',     'Tarde',       '⏰', '#f59e0b'),
    ('justificado', 'Justificado', '📝', '#6366f1'),
    ('pendiente', 'Sin marcar',  '·',  '#94a3b8'),
]
ASISTENCIA_META = {c: {'etiqueta': e, 'emoji': m, 'color': col}
                   for c, e, m, col in ESTADOS_ASISTENCIA}

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
DIAS_CORTOS = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _coach_o_fuera():
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.inicio'))
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  REJILLA DEL MES
# ═══════════════════════════════════════════════════════════════════════════
def rejilla(anio, mes, eventos):
    """Las 5 o 6 semanas del mes, cada día con sus eventos.

    La semana empieza en lunes, como en España y Latinoamérica. Se rellenan los
    huecos del principio y del final con los días del mes de al lado en vez de
    dejar celdas vacías: así el calendario no tiene agujeros y se puede tocar
    un día del mes que viene sin cambiar de vista.
    """
    primero = date(anio, mes, 1)
    dias_mes = monthrange(anio, mes)[1]
    relleno_ini = primero.weekday()                     # lunes = 0

    por_dia = {}
    for e in eventos:
        f = db.parse_fecha(e.get('fecha'))
        if f:
            por_dia.setdefault(f.isoformat(), []).append(e)

    hoy = date.today()
    celdas = []
    inicio = primero - timedelta(days=relleno_ini)
    total = relleno_ini + dias_mes
    semanas = (total + 6) // 7
    for i in range(semanas * 7):
        d = inicio + timedelta(days=i)
        del_mes = (d.month == mes and d.year == anio)
        suyos = sorted(por_dia.get(d.isoformat(), []),
                       key=lambda e: str(e.get('hora') or '99:99'))
        celdas.append({
            'fecha': d, 'iso': d.isoformat(), 'dia': d.day,
            'del_mes': del_mes, 'hoy': d == hoy,
            'finde': d.weekday() >= 5,
            'eventos': suyos,
            'colores': list(dict.fromkeys(color_de(e) for e in suyos))[:4],
        })
    return [celdas[i:i + 7] for i in range(0, len(celdas), 7)]


def color_de(evento):
    if (evento.get('tipo') or '') == 'entreno':
        te = evento.get('tipo_entreno') or 'mixto'
        return ENTRENO_META.get(te, ENTRENO_META['mixto'])['color']
    return TIPO_META.get(evento.get('tipo') or 'entreno',
                         TIPO_META['entreno'])['color']


def etiqueta_de(evento):
    tipo = evento.get('tipo') or 'entreno'
    if tipo == 'entreno':
        te = evento.get('tipo_entreno')
        if te and te in ENTRENO_META and te != 'mixto':
            return f'Entreno {ENTRENO_META[te]["etiqueta"].lower()}'
        return 'Entrenamiento'
    return TIPO_META.get(tipo, {}).get('etiqueta', tipo.title())


def decorar(eventos):
    hoy = date.today()
    for e in eventos:
        f = db.parse_fecha(e.get('fecha'))
        e['_fecha'] = f
        e['_pasado'] = bool(f and f < hoy)
        e['_hoy'] = bool(f and f == hoy)
        e['_dias'] = (f - hoy).days if f else None
        e['_color'] = color_de(e)
        e['_etiqueta'] = etiqueta_de(e)
        e['_meta'] = TIPO_META.get(e.get('tipo') or 'entreno', TIPO_META['entreno'])
        e['_intensidad'] = INTENSIDAD_META.get(e.get('intensidad') or 'media',
                                               INTENSIDAD_META['media'])
        e['_carga'] = carga_de(e)
    return eventos


def carga_de(evento):
    """Carga de una sesión. Solo los entrenamientos cargan.

    Se redondea con `+0.5` y no con `round()`: el round de Python redondea el
    medio al par (112,5 → 112) y ver 112 donde uno calculó 113 hace dudar del
    número entero.
    """
    if (evento.get('tipo') or '') != 'entreno':
        return 0
    minutos = int(evento.get('duracion_min') or 0)
    return int(minutos * FACTOR.get(evento.get('intensidad') or 'media', 1.0) + 0.5)


def _para_js(e):
    """Versión del evento que va al navegador.

    Se recorta a mano en vez de volcar la fila entera porque `_fecha` es un
    objeto date que no es serializable, y porque no hace falta mandar al
    cliente columnas que la pantalla no usa.
    """
    return {
        'id': e.get('id'), 'tipo': e.get('tipo') or 'entreno',
        'titulo': e.get('titulo') or '',
        'fecha': str(e.get('fecha') or '')[:10],
        'hora': str(e.get('hora') or '')[:5] or None,
        'lugar': e.get('lugar') or '', 'descripcion': e.get('descripcion') or '',
        'tipo_entreno': e.get('tipo_entreno') or 'mixto',
        'intensidad': e.get('intensidad') or 'media',
        'duracion_min': e.get('duracion_min') or 90,
        'rival': e.get('rival') or '', 'local': bool(e.get('local', True)),
        'resultado': e.get('resultado') or '',
        '_color': e.get('_color'), '_etiqueta': e.get('_etiqueta'),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ANÁLISIS DE LA SEMANA
# ═══════════════════════════════════════════════════════════════════════════
def analisis_semana(eventos, referencia=None):
    """Carga, reparto por tipo y avisos. Lo que el entrenador mira el domingo."""
    hoy = referencia or date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)

    semana = [e for e in eventos
              if e.get('_fecha') and lunes <= e['_fecha'] <= domingo]
    entrenos = [e for e in semana if (e.get('tipo') or '') == 'entreno']
    carga = sum(carga_de(e) for e in entrenos)
    minutos = sum(int(e.get('duracion_min') or 0) for e in entrenos)

    reparto = []
    for clave, etiqueta, color in TIPOS_ENTRENO:
        m = sum(int(e.get('duracion_min') or 0) for e in entrenos
                if (e.get('tipo_entreno') or 'mixto') == clave)
        if m:
            reparto.append({'clave': clave, 'etiqueta': etiqueta, 'color': color,
                            'minutos': m,
                            'pct': round(100 * m / minutos) if minutos else 0})

    futuros = [e for e in eventos
               if (e.get('tipo') or '') == 'partido'
               and e.get('_fecha') and e['_fecha'] >= hoy
               and (e.get('estado') or '') != 'cancelado']
    futuros.sort(key=lambda e: e['_fecha'])
    proximo = futuros[0] if futuros else None
    dias_partido = (proximo['_fecha'] - hoy).days if proximo else None

    # Racha: días seguidos hacia atrás con al menos un entrenamiento.
    fechas = {e['_fecha'] for e in eventos
              if (e.get('tipo') or '') == 'entreno' and e.get('_fecha')}
    racha, cursor = 0, hoy
    while cursor in fechas:
        racha += 1
        cursor -= timedelta(days=1)

    # Los umbrales son orientativos: 500 unidades ≈ 5 sesiones de 90' a media
    # intensidad, que para una semana con partido ya es mucho.
    alertas = []
    if dias_partido is not None and dias_partido <= 2:
        cuando = ('hoy' if dias_partido == 0
                  else 'mañana' if dias_partido == 1 else 'en 2 días')
        alertas.append({'tipo': 'warn',
                        'texto': f'Partido {cuando}: baja la carga y prioriza '
                                 f'táctica y activación.'})
    if carga > 650:
        alertas.append({'tipo': 'mal',
                        'texto': f'Carga muy alta esta semana ({carga}). '
                                 f'Mete un día de recuperación.'})
    elif carga > 450:
        alertas.append({'tipo': 'warn',
                        'texto': f'Carga alta ({carga}). Vigila las molestias.'})
    recientes = [e for e in entrenos
                 if e.get('_fecha') and 0 <= (hoy - e['_fecha']).days <= 3]
    if not recientes and not alertas:
        alertas.append({'tipo': 'info',
                        'texto': 'Sin entrenamientos en los últimos días. '
                                 'Programa la próxima sesión.'})
    if minutos and not reparto:
        alertas.append({'tipo': 'info',
                        'texto': 'Tus sesiones no tienen tipo. Marcarlas como '
                                 'físico/técnico/táctico te enseña el reparto.'})

    return {
        'lunes': lunes, 'domingo': domingo,
        'carga': carga, 'minutos': minutos,
        'n_entrenos': len(entrenos),
        'n_partidos': len([e for e in semana if (e.get('tipo') or '') == 'partido']),
        'reparto': reparto,
        'proximo_partido': proximo, 'dias_partido': dias_partido,
        'racha': racha,
        'alertas': alertas,
        'color': ('#ef4444' if carga > 650 else '#f59e0b' if carga > 450 else '#10b981'),
        'pct': min(100, round(100 * carga / 700)) if carga else 0,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ASISTENCIA
# ═══════════════════════════════════════════════════════════════════════════
def asistencia_evento(event_id):
    return db.rows('fut_attendance', 'asistencia ev', event_id=event_id) or []


def resumen_asistencia(coach_id, desde=None, hasta=None):
    """Porcentaje de asistencia por jugador en el periodo."""
    eventos = db.eventos_equipo(coach_id, desde, hasta)
    # Solo cuentan los eventos a los que se va: un descanso no se "falta".
    eventos = [e for e in eventos if (e.get('tipo') or '') in ('entreno', 'partido')]
    ids = [e['id'] for e in eventos]
    if not ids:
        return [], []

    marcas = db.asistencia_de(ids)
    por_jugador = {}
    for m in marcas:
        pid = m.get('player_id') or m.get('manual_player_id')
        if pid:
            por_jugador.setdefault(str(pid), []).append(m)

    jugadores = db.jugadores_del_entrenador(coach_id)
    manuales = db.rows('fut_manual_players', 'manuales', coach_id=coach_id,
                       activo=True) or []

    filas = []
    for j in jugadores + [{'id': m['id'], 'name': m['nombre'], 'nombre': m['nombre'],
                           '_manual': True} for m in manuales]:
        suyas = por_jugador.get(str(j['id']), [])
        conteo = {c: 0 for c, _, _, _ in ESTADOS_ASISTENCIA}
        for m in suyas:
            estado = m.get('estado') or 'pendiente'
            conteo[estado] = conteo.get(estado, 0) + 1
        # Llegar tarde es haber ido: cuenta como asistencia para el porcentaje,
        # pero se enseña aparte porque al entrenador le importa.
        fueron = conteo.get('presente', 0) + conteo.get('tarde', 0)
        marcados = sum(v for k, v in conteo.items() if k != 'pendiente')
        filas.append({
            'jugador': j, 'conteo': conteo,
            'marcados': marcados, 'fueron': fueron,
            'sin_marcar': len(ids) - marcados,
            'pct': round(100 * fueron / marcados) if marcados else None,
        })
    filas.sort(key=lambda f: (f['pct'] is None, -(f['pct'] or 0)))
    return filas, eventos


# ═══════════════════════════════════════════════════════════════════════════
#  PANTALLAS DEL ENTRENADOR
# ═══════════════════════════════════════════════════════════════════════════
def _mes_pedido():
    hoy = date.today()
    try:
        anio = int(request.args.get('a') or hoy.year)
        mes = int(request.args.get('m') or hoy.month)
        if not 1 <= mes <= 12 or not 2000 <= anio <= 2100:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month
    return anio, mes


@bp.route('/coach/calendario')
@login_required
def c_calendario():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    anio, mes = _mes_pedido()

    # Se cargan tres meses: el que se ve y sus vecinos, para que los días de
    # relleno de la rejilla también muestren sus puntos.
    desde = (date(anio, mes, 1) - timedelta(days=10)).isoformat()
    hasta = (date(anio, mes, monthrange(anio, mes)[1]) + timedelta(days=10)).isoformat()
    eventos = decorar(db.eventos_equipo(uid, desde, hasta))

    # Para el análisis hace falta un rango más ancho (racha y próximo partido).
    amplio = decorar(db.eventos_equipo(
        uid,
        (date.today() - timedelta(days=45)).isoformat(),
        (date.today() + timedelta(days=120)).isoformat()))

    conteo = {}
    if eventos:
        for a in db.asistencia_de([e['id'] for e in eventos]):
            if a.get('estado') in ('presente', 'tarde'):
                conteo[a['event_id']] = conteo.get(a['event_id'], 0) + 1
    for e in eventos:
        e['_asisten'] = conteo.get(e['id'], 0)

    ant = date(anio, mes, 1) - timedelta(days=1)
    sig = date(anio, mes, monthrange(anio, mes)[1]) + timedelta(days=1)
    proximos = [e for e in amplio if not e['_pasado']][:6]

    return render_template(
        'c_calendario.html',
        tab_activa='agenda',
        semanas=rejilla(anio, mes, eventos),
        eventos_json=[_para_js(e) for e in eventos],
        proximos_json=[_para_js(e) for e in proximos],
        anio=anio, mes=mes, nombre_mes=MESES[mes - 1],
        dias_cortos=DIAS_CORTOS,
        mes_ant={'a': ant.year, 'm': ant.month},
        mes_sig={'a': sig.year, 'm': sig.month},
        es_mes_actual=(anio == date.today().year and mes == date.today().month),
        analisis=analisis_semana(amplio),
        proximos=proximos,
        tipos=TIPOS_EVENTO, tipos_entreno=TIPOS_ENTRENO, intensidades=INTENSIDADES,
        planes=db.rows('fut_training_plans', 'planes', coach_id=uid,
                       _order='creado', _desc=True) or [],
        n_jugadores=len(db.jugadores_del_entrenador(uid)),
        hoy=date.today().isoformat())


@bp.route('/coach/asistencia')
@login_required
def c_asistencia():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    dias = 90
    try:
        dias = max(7, min(365, int(request.args.get('d') or 90)))
    except (TypeError, ValueError):
        pass
    desde = (date.today() - timedelta(days=dias)).isoformat()
    hasta = date.today().isoformat()

    filas, eventos = resumen_asistencia(uid, desde, hasta)
    decorar(eventos)
    eventos.sort(key=lambda e: (e['_fecha'] or date.min), reverse=True)

    marcados = [f for f in filas if f['pct'] is not None]
    return render_template('c_asistencia.html',
                           tab_activa='agenda', hide_tabbar=True,
                           filas=filas, eventos=eventos[:30],
                           dias=dias, n_eventos=len(eventos),
                           media=(round(sum(f['pct'] for f in marcados) / len(marcados))
                                  if marcados else None),
                           estados=ESTADOS_ASISTENCIA)


@bp.route('/coach/asistencia/<eid>')
@login_required
def c_pasar_lista(eid):
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    evento = db.one('fut_events', 'evento lista', id=eid, coach_id=uid)
    if not evento:
        abort(404)
    decorar([evento])

    jugadores = db.jugadores_del_entrenador(uid)
    manuales = db.rows('fut_manual_players', 'manuales', coach_id=uid, activo=True) or []
    marcas = {}
    for a in asistencia_evento(eid):
        marcas[str(a.get('player_id') or a.get('manual_player_id'))] = a

    lista = []
    for j in jugadores:
        m = marcas.get(str(j['id']), {})
        lista.append({'id': j['id'], 'nombre': j.get('name') or j.get('nombre'),
                      'dorsal': (j.get('fut') or {}).get('dorsal'),
                      'posicion': (j.get('fut') or {}).get('posicion'),
                      'foto': j.get('profile_photo'), 'manual': False,
                      'estado': m.get('estado') or 'pendiente',
                      'motivo': m.get('motivo') or ''})
    for x in manuales:
        m = marcas.get(str(x['id']), {})
        lista.append({'id': x['id'], 'nombre': x['nombre'], 'dorsal': x.get('dorsal'),
                      'posicion': x.get('posicion'), 'foto': None, 'manual': True,
                      'estado': m.get('estado') or 'pendiente',
                      'motivo': m.get('motivo') or ''})

    return render_template('c_pasar_lista.html',
                           tab_activa='agenda', hide_tabbar=True,
                           evento=evento, lista=lista, estados=ESTADOS_ASISTENCIA)


@bp.route('/coach/planes')
@login_required
@roles.solo_pro('planes')
def c_planes():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    uid = db.equipo_id(current_user.id)
    planes = db.rows('fut_training_plans', 'planes', coach_id=uid,
                     _order='creado', _desc=True) or []
    for p in planes:
        p['_fecha'] = db.parse_fecha(p.get('creado'))
        p['_bloques'] = p.get('bloques') or []
        p['_minutos'] = sum(int(b.get('minutos') or 0) for b in p['_bloques'])
        p['_meta'] = ENTRENO_META.get(p.get('tipo') or 'mixto', ENTRENO_META['mixto'])
    return render_template('c_planes.html',
                           tab_activa='agenda', hide_tabbar=True,
                           planes=planes,
                           tipos_entreno=TIPOS_ENTRENO,
                           intensidades=INTENSIDADES)


@bp.route('/coach/planes/<plid>')
@login_required
@roles.solo_pro('planes')
def c_plan(plid):
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    plan = db.one('fut_training_plans', 'plan', id=plid, coach_id=db.equipo_id(current_user.id))
    if not plan:
        abort(404)
    plan['_bloques'] = plan.get('bloques') or []
    plan['_minutos'] = sum(int(b.get('minutos') or 0) for b in plan['_bloques'])
    return render_template('c_plan.html',
                           tab_activa='agenda', hide_tabbar=True,
                           plan=plan,
                           tipos_entreno=TIPOS_ENTRENO,
                           intensidades=INTENSIDADES,
                           hoy=date.today().isoformat())


# ═══════════════════════════════════════════════════════════════════════════
#  PANTALLA DEL JUGADOR
# ═══════════════════════════════════════════════════════════════════════════
@bp.route('/calendario')
@login_required
def p_calendario():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_calendario'))

    uid = current_user.id
    anio, mes = _mes_pedido()
    coach = db.entrenador_del_jugador(uid)

    desde = (date(anio, mes, 1) - timedelta(days=10)).isoformat()
    hasta = (date(anio, mes, monthrange(anio, mes)[1]) + timedelta(days=10)).isoformat()
    eventos = decorar(db.eventos_para_jugador(uid, desde, hasta))

    mias = {}
    if eventos:
        for a in db.asistencia_de([e['id'] for e in eventos], uid):
            mias[a['event_id']] = a.get('estado')
    for e in eventos:
        e['_mi_estado'] = mias.get(e['id']) or 'pendiente'
        e['_mi_meta'] = ASISTENCIA_META.get(e['_mi_estado'], ASISTENCIA_META['pendiente'])

    amplio = decorar(db.eventos_para_jugador(
        uid, (date.today() - timedelta(days=10)).isoformat(),
        (date.today() + timedelta(days=90)).isoformat()))

    ant = date(anio, mes, 1) - timedelta(days=1)
    sig = date(anio, mes, monthrange(anio, mes)[1]) + timedelta(days=1)

    return render_template('p_calendario.html',
                           tab_activa='agenda',
                           semanas=rejilla(anio, mes, eventos),
                           eventos_json=[_para_js(e) for e in eventos],
                           anio=anio, mes=mes, nombre_mes=MESES[mes - 1],
                           dias_cortos=DIAS_CORTOS,
                           mes_ant={'a': ant.year, 'm': ant.month},
                           mes_sig={'a': sig.year, 'm': sig.month},
                           proximos=[e for e in amplio if not e['_pasado']][:6],
                           entrenador=coach,
                           estados=ESTADOS_ASISTENCIA,
                           hoy=date.today().isoformat())


# ═══════════════════════════════════════════════════════════════════════════
#  API
# ═══════════════════════════════════════════════════════════════════════════
def _guardia_coach():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el entrenador organiza el calendario.'}), 403
    return None


def _campos_evento(d):
    tipo = d.get('tipo') if d.get('tipo') in TIPO_META else 'entreno'
    datos = {
        'tipo': tipo,
        'titulo': (d.get('titulo') or '').strip()[:120] or etiqueta_de({'tipo': tipo}),
        'fecha': d.get('fecha') or db.hoy_iso(),
        'hora': d.get('hora') or None,
        'lugar': (d.get('lugar') or '')[:120],
        'descripcion': (d.get('descripcion') or '')[:1200],
        'duracion_min': max(0, min(600, int(d.get('duracion_min') or 90))),
        'estado': (d.get('estado') if d.get('estado') in
                   ('programado', 'hecho', 'cancelado') else 'programado'),
    }
    if tipo == 'entreno':
        datos['tipo_entreno'] = (d.get('tipo_entreno')
                                 if d.get('tipo_entreno') in ENTRENO_META else 'mixto')
        datos['intensidad'] = (d.get('intensidad')
                               if d.get('intensidad') in FACTOR else 'media')
    if tipo == 'partido':
        datos['rival'] = (d.get('rival') or '')[:80]
        datos['local'] = bool(d.get('local', True))
        datos['resultado'] = (d.get('resultado') or '')[:20] or None
    return datos


@bp.route('/api/calendario/evento', methods=['POST'])
@login_required
def api_cal_evento():
    """Crea o actualiza un evento. Con `id` actualiza; sin él, crea."""
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)
    datos = _campos_evento(d)

    eid = d.get('id')
    if eid:
        if not db.one('fut_events', 'mio', id=eid, coach_id=uid):
            return jsonify({'error': 'Ese evento no es tuyo.'}), 403
        db.update('fut_events', datos, 'evento up', id=eid, coach_id=uid)
        return jsonify({'ok': True, 'id': eid, 'mensaje': 'Evento actualizado.'})

    # Sin plan Pro hay tope de eventos futuros: se puede organizar una
    # temporada corta, no un club entero.
    if not roles.es_pro(current_user):
        futuros = [e for e in db.eventos_equipo(uid, desde=db.hoy_iso())]
        if len(futuros) >= roles.LIMITE_EVENTOS_FREE:
            return jsonify({
                'error': f'El plan gratuito permite {roles.LIMITE_EVENTOS_FREE} '
                         'eventos por delante. Pásate a Pro para el calendario completo.',
                'pro': True, 'url': url_for('futbol.planes')}), 402

    # `uid` es el EQUIPO; la firma es la PERSONA que lo agenda.
    datos.update({'coach_id': uid, 'registrado_por': current_user.id,
                  'creado': _ahora()})
    if d.get('plan_id'):
        datos['plan_id'] = d['plan_id']
    fila = db.insert('fut_events', datos, 'evento nuevo')
    if not fila:
        return jsonify({'error': 'No se pudo crear el evento.'}), 500

    # Un plan volcado al calendario cuenta un uso: sirve para ordenarlos por
    # los que de verdad se usan.
    if d.get('plan_id'):
        plan = db.one('fut_training_plans', 'plan uso', id=d['plan_id'], coach_id=uid)
        if plan:
            db.update('fut_training_plans',
                      {'veces_usado': int(plan.get('veces_usado') or 0) + 1},
                      'uso plan', id=plan['id'])

    return jsonify({'ok': True, 'id': fila['id'], 'mensaje': 'Evento agendado.'})


@bp.route('/api/calendario/evento/<eid>', methods=['DELETE'])
@login_required
def api_cal_borrar(eid):
    error = _guardia_coach()
    if error:
        return error
    db.delete('fut_events', 'borrar evento', id=eid, coach_id=db.equipo_id(current_user.id))
    return jsonify({'ok': True, 'mensaje': 'Evento borrado.'})


@bp.route('/api/asistencia/lista', methods=['POST'])
@login_required
def api_pasar_lista():
    """Guarda la lista entera de un evento de una vez."""
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)
    eid = d.get('event_id')
    if not eid or not db.one('fut_events', 'evento mio', id=eid, coach_id=uid):
        return jsonify({'error': 'Ese evento no es tuyo.'}), 403

    validos = {c for c, _, _, _ in ESTADOS_ASISTENCIA}
    jugadores = {str(j['id']) for j in db.jugadores_del_entrenador(uid)}
    manuales = {str(m['id']) for m in
                (db.rows('fut_manual_players', 'manuales', coach_id=uid) or [])}
    previas = {str(a.get('player_id') or a.get('manual_player_id')): a
               for a in asistencia_evento(eid)}

    n = 0
    for m in (d.get('marcas') or []):
        pid = str(m.get('player_id') or '')
        estado = m.get('estado')
        if estado not in validos:
            continue
        es_manual = pid in manuales
        if not es_manual and pid not in jugadores:
            continue

        datos = {
            'event_id': eid,
            'player_id': None if es_manual else pid,
            'manual_player_id': pid if es_manual else None,
            'jugador_nombre': (m.get('nombre') or '')[:120],
            'estado': estado,
            'motivo': (m.get('motivo') or '')[:200],
            'registrado_por': current_user.id,
            'actualizado': _ahora(),
        }
        previa = previas.get(pid)
        if previa:
            db.update('fut_attendance', datos, 'lista up', id=previa['id'])
        else:
            datos['creado'] = _ahora()
            db.insert('fut_attendance', datos, 'lista nueva')
        n += 1

    return jsonify({'ok': True, 'n': n,
                    'mensaje': f'Lista guardada: {n} jugador(es).'})


@bp.route('/api/plan', methods=['POST'])
@login_required
def api_plan():
    """Crea o actualiza un plan de entrenamiento."""
    error = _guardia_coach()
    if error:
        return error
    if not roles.es_pro(current_user):
        return jsonify({'error': 'Los planes de entrenamiento son del plan Pro.',
                        'pro': True, 'url': url_for('futbol.planes')}), 402

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)
    nombre = (d.get('nombre') or '').strip()
    if len(nombre) < 3:
        return jsonify({'error': 'Ponle un nombre al plan.'}), 400

    bloques = []
    for b in (d.get('bloques') or [])[:20]:
        titulo = (b.get('nombre') or '').strip()
        if not titulo:
            continue
        bloques.append({
            'nombre': titulo[:100],
            'minutos': max(0, min(180, int(b.get('minutos') or 0))),
            'descripcion': (b.get('descripcion') or '')[:800],
            'material': (b.get('material') or '')[:200],
        })

    datos = {
        'nombre': nombre[:120],
        'objetivo': (d.get('objetivo') or '')[:400],
        'tipo': d.get('tipo') if d.get('tipo') in ENTRENO_META else 'mixto',
        'intensidad': d.get('intensidad') if d.get('intensidad') in FACTOR else 'media',
        'duracion_min': (sum(b['minutos'] for b in bloques)
                         or max(0, min(600, int(d.get('duracion_min') or 90)))),
        'bloques': bloques,
        'material': (d.get('material') or '')[:400],
    }

    plid = d.get('id')
    if plid:
        if not db.one('fut_training_plans', 'plan mio', id=plid, coach_id=uid):
            return jsonify({'error': 'Ese plan no es tuyo.'}), 403
        db.update('fut_training_plans', datos, 'plan up', id=plid, coach_id=uid)
        return jsonify({'ok': True, 'id': plid, 'mensaje': 'Plan actualizado.'})

    datos.update({'coach_id': uid, 'creado': _ahora()})
    fila = db.insert('fut_training_plans', datos, 'plan nuevo')
    if not fila:
        return jsonify({'error': 'No se pudo guardar el plan.'}), 500
    return jsonify({'ok': True, 'id': fila['id'], 'mensaje': 'Plan guardado.',
                    'redirect': url_for('futbol.c_plan', plid=fila['id'])})


@bp.route('/api/plan/<plid>', methods=['DELETE'])
@login_required
def api_plan_borrar(plid):
    error = _guardia_coach()
    if error:
        return error
    db.delete('fut_training_plans', 'borrar plan', id=plid, coach_id=db.equipo_id(current_user.id))
    return jsonify({'ok': True, 'mensaje': 'Plan borrado.'})


@bp.route('/api/plan/<plid>/agendar', methods=['POST'])
@login_required
def api_plan_agendar(plid):
    """Vuelca un plan al calendario, en una fecha o en varias de golpe."""
    error = _guardia_coach()
    if error:
        return error

    uid = db.equipo_id(current_user.id)
    plan = db.one('fut_training_plans', 'plan agendar', id=plid, coach_id=uid)
    if not plan:
        return jsonify({'error': 'Ese plan no es tuyo.'}), 404

    d = request.get_json(silent=True) or {}
    fechas = [f for f in (d.get('fechas') or [d.get('fecha')]) if f][:30]
    if not fechas:
        return jsonify({'error': 'Elige al menos una fecha.'}), 400

    bloques = plan.get('bloques') or []
    detalle = '\n'.join(f'· {b["nombre"]} ({b["minutos"]}\')'
                        + (f' — {b["descripcion"]}' if b.get('descripcion') else '')
                        for b in bloques)
    creados = 0
    for f in fechas:
        fila = db.insert('fut_events', {
            'coach_id': uid, 'tipo': 'entreno',
            'titulo': plan['nombre'][:120],
            'fecha': f, 'hora': d.get('hora') or None,
            'lugar': (d.get('lugar') or '')[:120],
            'descripcion': ((plan.get('objetivo') or '') + '\n\n' + detalle).strip()[:1200],
            'tipo_entreno': plan.get('tipo') or 'mixto',
            'intensidad': plan.get('intensidad') or 'media',
            'duracion_min': plan.get('duracion_min') or 90,
            'estado': 'programado', 'plan_id': plid, 'creado': _ahora(),
        }, 'agendar plan')
        if fila:
            creados += 1

    db.update('fut_training_plans',
              {'veces_usado': int(plan.get('veces_usado') or 0) + creados},
              'uso plan', id=plid)
    return jsonify({'ok': True, 'n': creados,
                    'mensaje': f'{creados} sesión(es) en el calendario.',
                    'redirect': url_for('futbol.c_calendario')})
