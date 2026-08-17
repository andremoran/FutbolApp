# -*- coding: utf-8 -*-
"""
futbol/coach.py — Las 5 pestañas del ENTRENADOR.

Inicio · Equipo · Agenda · Táctica · IA, en el orden de
navigation/CoachTabNavigator.tsx.

La plantilla del equipo vive en `fut_plantilla` (entrenador ↔ jugador). El
código con el que un jugador se une es el `codigo_equipo` del entrenador, que
se genera al darse de alta.
"""
from datetime import date, timedelta
from functools import wraps

from flask import render_template, redirect, url_for, abort, request
from flask_login import login_required, current_user

import roles

from . import bp, db


def solo_entrenador(f):
    @wraps(f)
    @login_required
    def wrapper(*a, **kw):
        if getattr(current_user, 'role', '') != 'especialista':
            return redirect(url_for('futbol.inicio'))
        return f(*a, **kw)
    return wrapper


def _hay_perfil_dinamico(player_ids, manual_ids):
    """¿Hay alguien del equipo con el Perfil Dinámico ya cargado?

    Vale para marcar «evaluá a un jugador»: un jugador dado de alta con sus
    18 atributos está evaluado, aunque nunca se le haya tomado una prueba.
    """
    for columna, ids in (('player_id', player_ids), ('manual_player_id', manual_ids)):
        if not ids:
            continue
        filas = db.q(
            lambda c=columna, i=ids: db.sb().table('fut_attributes').select('id')
            .in_(c, i).not_.is_('overall', 'null').limit(1).execute().data or [],
            [], 'perfil dinamico')
        if filas:
            return True
    return False


# ═══════════════════════ 1. INICIO (dashboard) ═══════════════════════
@bp.route('/coach')
@solo_entrenador
def c_inicio():
    """El tablero del entrenador, con la misma estructura que CoachDashboardScreen.

    Orden de la app original, de arriba abajo: código de equipo · tres cifras
    (Plantel, Activos, Partidos) · solicitudes pendientes si las hay ·
    Evaluaciones · Salud mental · Estado físico promedio · Cuerpo técnico.
    """
    import roles

    uid = db.equipo_id(current_user.id)
    equipo = db.equipo_del_entrenador(uid)
    jugadores = db.jugadores_del_entrenador(uid)
    hoy = date.today()
    ids = [j['id'] for j in jugadores]

    # ── Activos hoy: quien marcó al menos un hábito ──
    activos = 0
    if ids:
        marcas = db.q(
            lambda: db.sb().table('fut_habit_completions').select('player_id')
            .in_('player_id', ids).eq('fecha', hoy.isoformat())
            .eq('hecho', True).execute().data or [], [], 'activos hoy')
        activos = len({m['player_id'] for m in marcas})

    n_partidos = len(db.rows('fut_matches', 'partidos', coach_id=uid) or [])

    # ── Primeros pasos (onboarding) ──
    #  Se marcan con datos reales, nunca a mano: igual que SetupChecklist.tsx
    #  de la app original. Basta con saber si existe al menos uno, de ahi el
    #  _limit=1 en vez de traerse la tabla entera para contarla.
    #
    #  Cuentan los jugadores SIN CUENTA: son jugadores del equipo igual, y con
    #  la plantilla llena de ellos el paso seguia sin marcarse.
    manuales = db.rows('fut_manual_players', 'manuales inicio',
                       coach_id=uid, activo=True) or []
    n_plantilla = len(jugadores) + len(manuales)

    #  «Evaluado» es cualquiera de las tres formas de evaluar que tiene la app,
    #  no solo las pruebas fisicas con baremo: tambien la evaluacion de los 18
    #  atributos (que es la que se hace desde la ficha del jugador) y el alta
    #  con Perfil Dinamico de un jugador sin cuenta.
    hay_evaluacion = bool(
        db.rows('fut_eval_results', 'primeros pasos', coach_id=uid, _limit=1)
        or db.rows('fut_evaluations', 'primeros pasos', coach_id=uid, _limit=1)
        or _hay_perfil_dinamico(ids, [m['id'] for m in manuales]))

    hay_evento = bool(db.rows('fut_events', 'primeros pasos',
                              coach_id=uid, _limit=1))

    # ── Estado físico promedio ──
    #  Sale del AUTOINFORME del jugador (fut_player_profile), igual que en la
    #  app original. NO tiene nada que ver con las respuestas del check-in de
    #  bienestar, que el entrenador no ve nunca.
    estado, n_reportan = [], 0
    if ids:
        perfiles = db.q(
            lambda: db.sb().table('fut_player_profile')
            .select('user_id, energia, motivacion, estado_fisico')
            .in_('user_id', ids).execute().data or [], [], 'estado equipo')
        for etiqueta, campo, icono, color in (
                ('Energía', 'energia', '⚡', '#f59e0b'),
                ('Motivación', 'motivacion', '💗', '#ec4899'),
                ('Estado físico', 'estado_fisico', '📈', '#10b981')):
            valores = [p[campo] for p in perfiles if p.get(campo) is not None]
            if valores:
                estado.append({'etiqueta': etiqueta, 'icono': icono, 'color': color,
                               'valor': round(sum(valores) / len(valores))})
        n_reportan = len([p for p in perfiles
                          if any(p.get(c) is not None
                                 for c in ('energia', 'motivacion', 'estado_fisico'))])

    # ── Solicitudes pendientes ──
    from .equipo import solicitudes_pendientes
    solicitudes = solicitudes_pendientes(uid)

    # ── Cuerpo técnico ──
    cuerpo = db.cuerpo_tecnico(uid)
    for m in cuerpo:
        m['yo'] = str(m['id']) == str(current_user.id)

    proximos = db.eventos_equipo(uid, desde=hoy.isoformat(),
                                 hasta=(hoy + timedelta(days=14)).isoformat())
    for e in proximos:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))

    return render_template('c_inicio.html',
                           tab_activa='inicio',
                           equipo=equipo,
                           codigo=db.codigo_equipo(uid),
                           jugadores=jugadores,
                           # La cifra «Plantel» y el primer paso cuentan a todos,
                           # tengan cuenta o no: son la plantilla del equipo.
                           n_jugadores=n_plantilla,
                           activos=activos,
                           n_partidos=n_partidos,
                           estado=estado,
                           n_reportan=n_reportan,
                           solicitudes=solicitudes,
                           cuerpo=cuerpo,
                           eventos=proximos[:3],
                           hay_evaluacion=hay_evaluacion,
                           hay_evento=hay_evento,
                           es_pro=roles.es_pro(current_user),
                           es_principal=roles.es_principal(current_user))


@bp.route('/coach/equipo/editar')
@solo_entrenador
def c_equipo_editar():
    """Datos del equipo + nivel competitivo (TeamLevelConfigModal.tsx).

    El nivel y la categoría de edad no son decoración: son los que deciden
    contra qué baremo se puntúan las pruebas físicas (ver tests_catalogo.py).
    """
    from . import tests_catalogo as cat
    from .evaluaciones import contexto_equipo

    uid = db.equipo_id(current_user.id)
    edad, nivel = contexto_equipo(uid)
    return render_template('c_equipo_editar.html',
                           hide_tabbar=True,
                           equipo=db.equipo_del_entrenador(uid),
                           categorias=cat.CATEGORIAS_EDAD,
                           niveles=cat.NIVELES_COMPETITIVOS,
                           ctx_edad=edad, ctx_nivel=nivel)


# ═══════════════════════ 2. EQUIPO ═══════════════════════
def _edad_de(anio_nacimiento):
    if not anio_nacimiento:
        return None
    return max(0, date.today().year - int(anio_nacimiento))


def _ficha_equipo(coach_id, semana_actual, alertas_por_dueno, *, player_id=None,
                  manual_player_id=None, nombre, posicion, dorsal, anio_nacimiento,
                  foto=None, activo=True):
    """Arma la tarjeta de un jugador (con o sin cuenta) para la pantalla
    Equipo: overall/potencial, cambio semanal y alerta principal — mismos
    datos que TeamPlayersScreen.tsx, calculados en futbol/db.py.
    """
    ficha = db.ficha_atributos(player_id, manual_player_id)
    historial = db.rows('fut_attribute_history', 'historial equipo',
                        _order='semana', _desc=True,
                        **db.dueno_filtro(player_id, manual_player_id))
    anterior = next((h for h in historial if h.get('semana') != semana_actual), None)
    delta = 0
    if ficha['_tiene_perfil'] and anterior and anterior.get('overall') is not None:
        delta = ficha['overall'] - anterior['overall']

    clave = str(player_id or manual_player_id)
    alertas = alertas_por_dueno.get(clave, [])
    # Las graves primero, como en la app: si solo caben dos, que se vean esas.
    alertas.sort(key=lambda a: 0 if a.get('severidad') == 'grave' else 1)

    return {
        'id': player_id or manual_player_id,
        'tipo': 'registrado' if player_id else 'manual',
        'name': nombre, 'posicion': posicion or 'Sin posición',
        # Se muestra la posición tal cual, pero se filtra por su familia.
        'familia': db.familia_posicion(posicion),
        'dorsal': dorsal, 'edad': _edad_de(anio_nacimiento),
        'profile_photo': foto, 'activo': activo,
        'overall': ficha['overall'], 'potencial': ficha['potencial'],
        'media_tecnica': ficha['media_tecnica'], 'media_fisica': ficha['media_fisica'],
        'media_mental': ficha['media_mental'],
        '_tiene_perfil': ficha['_tiene_perfil'], '_delta': delta,
        '_alertas': alertas,
        # Resumen semanal escrito por la IA. Vacío hasta la Fase 6 (espera al
        # proxy de IA); la tarjeta simplemente no pinta ese párrafo.
        '_resumen_ia': None,
    }


@bp.route('/coach/plantilla')
@solo_entrenador
def c_equipo():
    uid = db.equipo_id(current_user.id)
    jugadores = db.jugadores_del_entrenador(uid)
    manuales = db.rows('fut_manual_players', 'manuales equipo', coach_id=uid, activo=True) or []

    hoy = date.today()
    semana_actual = (hoy - timedelta(days=hoy.weekday())).isoformat()

    alertas_por_dueno = {}
    for a in (db.rows('fut_player_alerts', 'alertas equipo', coach_id=uid, activa=True) or []):
        clave = str(a.get('player_id') or a.get('manual_player_id'))
        alertas_por_dueno.setdefault(clave, []).append(a)

    plantilla = []
    for j in jugadores:
        plantilla.append(_ficha_equipo(
            uid, semana_actual, alertas_por_dueno, player_id=j['id'],
            nombre=j.get('name'), posicion=(j.get('fut') or {}).get('posicion'),
            dorsal=(j.get('fut') or {}).get('dorsal'), anio_nacimiento=j.get('anio_nacimiento'),
            foto=j.get('profile_photo'), activo=j.get('activo', True)))
    for m in manuales:
        plantilla.append(_ficha_equipo(
            uid, semana_actual, alertas_por_dueno, manual_player_id=m['id'],
            nombre=m.get('nombre'), posicion=m.get('posicion'),
            dorsal=m.get('dorsal'), anio_nacimiento=m.get('anio_nacimiento')))

    # Con perfil primero (de mejor a peor overall); sin evaluar, al final.
    plantilla.sort(key=lambda p: (0 if p['_tiene_perfil'] else 1, -(p['overall'] or 0)))

    con_perfil = [p for p in plantilla if p['_tiene_perfil']]
    resumen = {
        'con_perfil': len(con_perfil),
        'total': len(plantilla),
        'overall_prom': round(sum(p['overall'] for p in con_perfil) / len(con_perfil)) if con_perfil else 0,
        'cambio_semanal': sum(p['_delta'] for p in con_perfil),
        'subiendo': len([p for p in con_perfil if p['_delta'] > 0]),
        'bajando': len([p for p in con_perfil if p['_delta'] < 0]),
        'con_alertas': len([p for p in plantilla if p['_alertas']]),
    }

    return render_template('c_equipo.html',
                           tab_activa='equipo',
                           jugadores=plantilla,
                           resumen=resumen,
                           equipo=db.equipo_del_entrenador(uid),
                           codigo=db.codigo_equipo(uid))


@bp.route('/coach/jugador/<pid>')
@solo_entrenador
def c_jugador(pid):
    uid = db.equipo_id(current_user.id)
    # Solo se puede ver a un jugador de la propia plantilla.
    jugadores = db.jugadores_del_entrenador(uid)
    jugador = next((j for j in jugadores if str(j['id']) == str(pid)), None)
    if not jugador:
        abort(404)

    entrenos = db.rows('fut_trainings', 'entrenos jug', player_id=pid,
                       _order='fecha', _desc=True, _limit=10)
    for e in entrenos:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))
    # Los apuntes del entrenador sobre este jugador. En la app son
    # «Observaciones» y van sueltas; aquí viven en la nota de cada evaluación,
    # que es donde el entrenador ya las escribe.
    evaluaciones = db.rows('fut_evaluations', 'evals jug', player_id=pid,
                           _order='fecha', _desc=True, _limit=20)
    for e in evaluaciones:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))
        e.update(e.get('puntuaciones') or {})  # tecnica/fisico/mental sueltos, para el resumen de abajo
    apuntes = [e for e in evaluaciones if (e.get('notas') or '').strip()]

    # Las cuatro cifras de PlayerDetailScreen.
    metas = db.rows('fut_goals', 'metas jug', player_id=pid) or []
    goles = 0
    partidos = db.rows('fut_matches', 'partidos', coach_id=uid, _limit=60) or []
    if partidos:
        marcas = db.q(
            lambda: db.sb().table('fut_match_stats').select('goles')
            .in_('match_id', [m['id'] for m in partidos])
            .eq('player_id', pid).execute().data or [], [], 'goles jugador')
        goles = sum(int(s.get('goles') or 0) for s in marcas)

    cifras = {
        'entrenos': len(db.rows('fut_trainings', 'n entrenos', player_id=pid) or []),
        'goles': goles,
        'metas': len([m for m in metas if m.get('completada')]),
        'racha': db.racha_actual(pid),
    }

    return render_template('c_jugador.html',
                           tab_activa='equipo',
                           hide_tabbar=True,
                           jugador=jugador,
                           perfil=db.perfil_jugador(pid),
                           atributos=db.atributos(pid),
                           media=db.media_atributos(pid),
                           ficha=db.ficha_atributos(player_id=pid),
                           entrenos=entrenos,
                           evaluaciones=evaluaciones,
                           apuntes=apuntes,
                           cifras=cifras,
                           racha=cifras['racha'])


@bp.route('/coach/jugador/<pid>/evaluar')
@solo_entrenador
def c_evaluar(pid):
    uid = db.equipo_id(current_user.id)

    #  Vale para los dos tipos de jugador. Antes solo abría con los que tienen
    #  cuenta, así que en un equipo de formación —donde casi nadie la tiene—
    #  esta pantalla era inalcanzable.
    jugador = next((j for j in db.jugadores_del_entrenador(uid)
                    if str(j['id']) == str(pid)), None)
    manual = None
    if not jugador:
        manual = db.one('fut_manual_players', 'manual eval', id=pid, coach_id=uid)
        if not manual:
            abort(404)
        jugador = {'id': pid, 'name': manual.get('nombre')}

    dueno = db.dueno_filtro(player_id=None if manual else pid,
                            manual_player_id=pid if manual else None)
    ficha = db.ficha_atributos(**dueno)

    # ── Evolución: la línea del overall y el delta de cada atributo ──
    #  Las dos salen del histórico semanal. Sin dos fotos no hay comparación,
    #  así que con una sola semana no se pinta ni gráfica ni deltas.
    historial_filas = db.rows('fut_attribute_history', 'historial eval',
                              _order='semana', **dueno) or []
    historial = [h['overall'] for h in historial_filas
                 if h.get('overall') is not None][-8:]

    deltas = {}
    if len(historial_filas) >= 2:
        previa = historial_filas[-2].get('atributos') or {}
        for clave in db.ATRIBUTOS_18:
            antes, ahora = previa.get(clave), ficha.get(clave)
            if antes is not None and ahora is not None and ahora != antes:
                deltas[clave] = ahora - antes

    delta_overall = 0
    if len(historial) >= 2:
        delta_overall = historial[-1] - historial[-2]

    # ── Stats competitivas ──
    #  Del que tiene cuenta salen solas de los partidos. El que no la tiene no
    #  aparece en fut_match_stats, así que se usan las cifras que el entrenador
    #  cargó al darlo de alta.
    if manual:
        stats = {'partidos': '—',
                 'minutos': manual.get('minutos_jugados') or 0,
                 'goles': manual.get('goles') or 0,
                 'asistencias': manual.get('asistencias') or 0,
                 'rating': manual.get('valoracion_promedio') or '—'}
        auto = False
    else:
        partidos = db.rows('fut_matches', 'partidos eval', coach_id=uid, _limit=100) or []
        marcas = []
        if partidos:
            marcas = db.q(
                lambda: db.sb().table('fut_match_stats').select('*')
                .in_('match_id', [m['id'] for m in partidos])
                .eq('player_id', pid).execute().data or [], [], 'stats jugador')
        valoraciones = [float(m['valoracion']) for m in marcas if m.get('valoracion')]
        stats = {
            'partidos': len(marcas),
            'minutos': sum(int(m.get('minutos') or 0) for m in marcas),
            'goles': sum(int(m.get('goles') or 0) for m in marcas),
            'asistencias': sum(int(m.get('asistencias') or 0) for m in marcas),
            'rating': round(sum(valoraciones) / len(valoraciones), 1) if valoraciones else '—',
        }
        auto = True

    fila = db.fila_atributos(**dueno) or {}
    perfil = {} if manual else db.perfil_jugador(pid)

    return render_template('c_evaluar.html',
                           hide_tabbar=True,
                           jugador=jugador,
                           es_manual=bool(manual),
                           stats_auto=auto,
                           ficha=ficha,
                           posicion=(manual or {}).get('posicion') or perfil.get('posicion'),
                           deltas=deltas,
                           delta=delta_overall,
                           historial=historial,
                           stats=stats,
                           # El informe lo escribe la IA (fase 6): hasta que el
                           # proxy esté desplegado, la tarjeta lo dice y ya.
                           reporte=None,
                           actualizado=db.parse_fecha(fila.get('actualizado')),
                           niveles_fatiga=db.NIVELES_FATIGA,
                           fatiga_nivel=db.nivel_de_fatiga(ficha.get('fatiga')))


# ═══════════════════════ 3. AGENDA ═══════════════════════
@bp.route('/coach/agenda')
@solo_entrenador
def c_agenda():
    uid = db.equipo_id(current_user.id)
    desde = (date.today() - timedelta(days=30)).isoformat()
    hasta = (date.today() + timedelta(days=90)).isoformat()
    eventos = db.eventos_equipo(uid, desde, hasta)

    conteo = {}
    if eventos:
        for a in db.asistencia_de([e['id'] for e in eventos]):
            # 'asiste' es el nombre VIEJO: schema_v2 lo migró a 'presente' y
            # añadió 'tarde'. Comparando con el viejo, el contador de cada
            # evento salía siempre en 0 por más lista que se pasara.
            if a.get('estado') in ('presente', 'tarde'):
                conteo[a['event_id']] = conteo.get(a['event_id'], 0) + 1

    hoy = date.today()
    for e in eventos:
        f = db.parse_fecha(e.get('fecha'))
        e['_fecha'] = f
        e['_pasado'] = bool(f and f < hoy)
        e['_confirmados'] = conteo.get(e['id'], 0)

    return render_template('c_agenda.html',
                           tab_activa='agenda',
                           proximos=[e for e in eventos if not e['_pasado']],
                           pasados=list(reversed([e for e in eventos if e['_pasado']]))[:10],
                           n_jugadores=db.tamano_plantilla(uid))


#  El detalle del evento vive ahora en futbol/calendario.py (/coach/evento/<id>),
#  que es donde está todo lo del calendario. El que había aquí pintaba la
#  asistencia con los tres estados viejos (asiste/duda/falta), que dejaron de
#  existir al pasar a cuatro (presente/tarde/justificado/ausente) en schema_v2:
#  marcaba a todo el mundo como «sin marcar». Las plantillas que lo enlazan lo
#  hacen por nombre de endpoint, así que siguen funcionando.


# ═══════════════════════ 4. TÁCTICA ═══════════════════════
@bp.route('/coach/tactica')
@solo_entrenador
@roles.solo_pro('tactica')
def c_tactica():
    jugadas = db.rows('fut_tactical_plays', 'jugadas', coach_id=db.equipo_id(current_user.id),
                      _order='creado', _desc=True)
    for j in jugadas:
        j['_fecha'] = db.parse_fecha(j.get('creado'))
    return render_template('c_tactica.html',
                           tab_activa='tactica', jugadas=jugadas)


@bp.route('/coach/tactica/pizarra')
@bp.route('/coach/tactica/pizarra/<jid>')
@solo_entrenador
@roles.solo_pro('tactica')
def c_pizarra(jid=None):
    jugada = None
    if jid:
        jugada = db.one('fut_tactical_plays', 'jugada', id=jid, coach_id=db.equipo_id(current_user.id))
        if not jugada:
            abort(404)
    return render_template('c_pizarra.html',
                           tab_activa='tactica',
                           hide_tabbar=True,       # la barra taparía la caja de herramientas
                           jugada=jugada)


# ═══════════════════════ 5. IA ═══════════════════════
@bp.route('/coach/ia')
@solo_entrenador
def c_ia():
    historial = db.rows('fut_ia_chat', 'chat ia coach', user_id=current_user.id,
                        _order='creado', _limit=40)
    jugadores = db.jugadores_del_entrenador(db.equipo_id(current_user.id))
    return render_template('c_ia.html',
                           tab_activa='ia',
                           historial=historial,
                           n_jugadores=len(jugadores),
                           ia_restantes=roles.ia_restantes(current_user),
                           ia_tope=roles.IA_MENSAJES_GRATIS)


# ═══════════════════════ TESTS (compartido) ═══════════════════════
@bp.route('/coach/tests')
@solo_entrenador
def c_tests():
    uid = db.equipo_id(current_user.id)
    pruebas = db.rows('fut_tests', 'tests', coach_id=uid, _order='fecha', _desc=True)
    for t in pruebas:
        t['_fecha'] = db.parse_fecha(t.get('fecha'))
    return render_template('c_tests.html',
                           tab_activa='equipo', hide_tabbar=True,
                           tests=pruebas,
                           jugadores=db.jugadores_del_entrenador(uid))


@bp.route('/coach/tests/<tid>')
@solo_entrenador
def c_test_detalle(tid):
    uid = db.equipo_id(current_user.id)
    test = db.one('fut_tests', 'test', id=tid, coach_id=uid)
    if not test:
        abort(404)
    resultados = db.rows('fut_test_results', 'resultados', test_id=tid)
    jugadores = {j['id']: j for j in db.jugadores_del_entrenador(uid)}
    for r in resultados:
        r['_jugador'] = jugadores.get(r.get('player_id'), {})

    # Ranking: en pruebas de tiempo gana el menor; en el resto, el mayor.
    menor_mejor = (test.get('tipo') or '') in ('tiempo', 'velocidad')
    resultados.sort(key=lambda r: (r.get('valor') is None,
                                   (r.get('valor') or 0) * (1 if menor_mejor else -1)))
    for i, r in enumerate(resultados, 1):
        r['_puesto'] = i

    return render_template('c_test_detalle.html',
                           tab_activa='equipo', hide_tabbar=True,
                           test=test, resultados=resultados,
                           jugadores=list(jugadores.values()),
                           menor_mejor=menor_mejor)
