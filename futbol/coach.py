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


#  Los periodos que se pueden mirar. El de un mes es el que sale por defecto:
#  una semana suele ser poco para que se mueva nada, y tres meses ya es una
#  pregunta distinta.
PERIODOS = [
    ('7',    'Una semana',         7),
    ('30',   'Un mes',             30),
    ('90',   'Tres meses',         90),
    ('365',  'Una temporada',      365),
    ('todo', 'Desde el principio', None),
]


def _dias_del_periodo(clave):
    for c, _, d in PERIODOS:
        if c == clave:
            return d
    return 30


def _delta(ahora, antes):
    """El cambio entre dos numeros, o None si falta alguno.

    Devolver None y no cero importa: «no habia dato» y «no cambio» son cosas
    distintas, y en una pantalla de evolucion se leen muy distinto.
    """
    if ahora is None or antes is None:
        return None
    return round(ahora - antes, 1)


@bp.route('/coach/jugador/<pid>/progreso')
@solo_entrenador
def c_progreso_jugador(pid):
    """Como ha evolucionado un jugador, con todo lo que la app sabe de el.

    Responde a «¿esta mejorando?» sin que el entrenador tenga que ir juntando
    cuatro pantallas: su ficha dice como esta HOY, y esto dice de donde viene.

    Todo se compara contra un momento del pasado que el elige —una semana, un
    mes, la temporada— y cada bloque cuenta su propio cambio.
    """
    from datetime import date, timedelta
    from . import evaluaciones as ev
    from . import tests_catalogo as cat

    uid = db.equipo_id(current_user.id)

    #  El jugador, tenga cuenta o no. `plantilla_completa` evita el fallo de
    #  siempre: buscar solo entre los registrados y no encontrar a nadie.
    jugador = next((x for x in db.plantilla_completa(uid) if str(x['id']) == str(pid)), None)
    if not jugador:
        abort(404)
    dueno = db.dueno_filtro(
        player_id=None if jugador['es_manual'] else pid,
        manual_player_id=pid if jugador['es_manual'] else None)

    clave = request.args.get('periodo', '30')
    dias = _dias_del_periodo(clave)
    desde = (date.today() - timedelta(days=dias)) if dias else None
    desde_iso = desde.isoformat() if desde else '0000-01-01'

    # ─── El perfil dinamico: hoy contra entonces ────────────────────────────
    historial = db.rows('fut_attribute_history', 'historial progreso',
                        _order='semana', **dueno) or []
    ficha = db.ficha_atributos(**dueno)

    dentro = [h for h in historial if (h.get('semana') or '') >= desde_iso]
    #  La referencia es la ultima foto ANTERIOR al periodo; si no la hay, la
    #  primera que caiga dentro. Comparar contra la de hoy no diria nada.
    antes = next((h for h in reversed(historial) if (h.get('semana') or '') < desde_iso),
                 dentro[0] if dentro else None)
    hoy = historial[-1] if historial else None

    #  `ficha_atributos` rellena los huecos con 50 para no dejar pantallas en
    #  blanco, y avisa de ello en `_tiene_perfil`. Aqui ese 50 no vale: seria
    #  ensenar el «progreso» de alguien a quien nadie ha evaluado nunca.
    evaluado = bool(ficha.get('_tiene_perfil'))

    def _valor(foto, k):
        return ((foto or {}).get('atributos') or {}).get(k)

    atributos = []
    for k in db.ATRIBUTOS_18:
        v_hoy = _valor(hoy, k)
        if v_hoy is None and evaluado:
            v_hoy = ficha.get(k)
        atributos.append({
            'clave': k,
            'etiqueta': k.replace('_', ' ').capitalize(),
            'familia': ('tecnica' if k in db.ATRIBUTOS_TECNICOS
                        else 'fisico' if k in db.ATRIBUTOS_FISICOS else 'mental'),
            'hoy': v_hoy,
            'delta': _delta(v_hoy, _valor(antes, k)),
        })

    overall_hoy = ((hoy or {}).get('overall') if hoy
                   else (ficha.get('overall') if evaluado else None))

    #  La linea que se dibuja: la foto de referencia mas las del periodo. No
    #  todo el historial: si el numero de arriba dice «+9 en un mes» y la linea
    #  arranca hace un año, el entrenador ve dos cosas que no cuadran.
    a_dibujar = list(dentro)
    if antes is not None and (not dentro or antes is not dentro[0]):
        a_dibujar = [antes] + a_dibujar

    resumen = {
        'overall': overall_hoy,
        'delta': _delta(overall_hoy, (antes or {}).get('overall')),
        'desde': (antes or {}).get('semana'),
        'fotos': len(historial),
        'curva': [{'fecha': db.parse_fecha(h.get('semana')), 'valor': h.get('overall')}
                  for h in a_dibujar if h.get('overall') is not None],
    }

    #  Las tres familias, cada una en un numero. Es la lectura que se quiere de
    #  un golpe —«fisicamente mejor, mentalmente igual»— y que leer 18 filas no
    #  da: al llegar a la fila doce ya no te acuerdas de la tres.
    familias = []
    for fam, titulo, ico, tono, fondo in (
            ('tecnica', 'Técnico', 'target', 'var(--primary)', 'var(--primary-soft)'),
            ('fisico', 'Físico', 'zap', '#475569', '#f1f5f9'),
            ('mental', 'Mental', 'cpu', '#7e6acb', '#ede9fe')):
        suyos = [a for a in atributos if a['familia'] == fam]
        ahora = [a['hoy'] for a in suyos if a['hoy'] is not None]
        antano = [_valor(antes, a['clave']) for a in suyos]
        antano = [v for v in antano if v is not None]
        media = round(sum(ahora) / float(len(ahora)), 1) if ahora else None
        familias.append({
            'clave': fam, 'titulo': titulo, 'icono': ico, 'tono': tono, 'fondo': fondo,
            'media': media,
            'delta': _delta(media, round(sum(antano) / float(len(antano)), 1)
                            if antano else None),
        })

    #  Y lo que de verdad se movio. Los atributos que no cambiaron son ruido en
    #  una pantalla que trata justamente del cambio.
    movidos = sorted([a for a in atributos if a['delta']],
                     key=lambda a: -abs(a['delta']))[:6]

    # ─── Las pruebas: primera contra ultima del periodo ─────────────────────
    if jugador['es_manual']:
        marcas = [f for f in ev.resultados_equipo(uid, 400)
                  if str(f.get('manual_player_id')) == str(pid)]
    else:
        marcas = ev.resultados_de(pid, 300)
    marcas = ev.enriquecer(marcas, uid, con_nivel=True)

    pruebas = {}
    for m in sorted([x for x in marcas if (x.get('fecha') or '') >= desde_iso],
                    key=lambda x: x.get('fecha') or ''):
        p = pruebas.setdefault(m.get('test_clave'), {
            'nombre': m.get('test_nombre') or m.get('test_clave'),
            'unidad': m.get('_unidad') or '',
            #  Si en esta prueba bajar es mejorar. Sale de la direccion del
            #  campo principal: `enriquecer()` NO trae ningun `_menor_mejor`,
            #  y darlo por hecho hacia que un sprint mas lento saliera con
            #  flecha verde.
            'menor_mejor': (m.get('_principal') or {}).get('direccion') == cat.MENOR,
            'marcas': []})
        p['marcas'].append(m)

    tests = []
    for p in pruebas.values():
        primera, ultima = p['marcas'][0], p['marcas'][-1]
        a, b = primera.get('_valor'), ultima.get('_valor')
        mejora = None
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a != b:
            #  En una prueba de tiempo, bajar es mejorar. Se normaliza aqui
            #  para que la pantalla no tenga que saber de que va cada prueba.
            mejora = round((a - b) if p['menor_mejor'] else (b - a), 2)
        #  La minilinea. En una prueba de tiempo se dibuja del reves, para que
        #  «mejorar» sea siempre subir: una linea que baja mientras el jugador
        #  mejora es justo lo que hace dudar al que la mira.
        numeros = [x.get('_valor') for x in p['marcas']
                   if isinstance(x.get('_valor'), (int, float))]
        tests.append({
            'datos': [-v for v in numeros] if p['menor_mejor'] else numeros,
            'nombre': p['nombre'], 'unidad': p['unidad'], 'veces': len(p['marcas']),
            'primera': a, 'ultima': b, 'mejora': mejora,
            'menor_mejor': p['menor_mejor'],
            'fecha_primera': primera.get('fecha'), 'fecha_ultima': ultima.get('fecha'),
            'nivel': (ultima.get('_nivel_meta') or {}).get('etiqueta'),
            'serie': [{'fecha': x.get('fecha'), 'valor': x.get('_valor')}
                      for x in p['marcas'] if isinstance(x.get('_valor'), (int, float))],
        })
    tests.sort(key=lambda t: -t['veces'])

    # ─── Competicion y compromiso, dentro del periodo ───────────────────────
    partidos = [m for m in (db.rows('fut_matches', 'partidos progreso', coach_id=uid) or [])
                if (m.get('fecha') or '') >= desde_iso]
    #  Ojo con el `or None`: `totales_de_partidos` entiende None como «trae
    #  tu los partidos», o sea TODOS. Con una lista vacia devuelve {}, que es
    #  lo que se quiere aqui — si no, «esta semana» acababa ensenando los goles
    #  de toda la temporada.
    competicion = db.totales_de_partidos(uid, ids={pid}, partidos=partidos).get(pid)

    columna = 'manual_player_id' if jugador['es_manual'] else 'player_id'
    marcas_asis = db.q(
        lambda: db.sb().table('fut_attendance').select('estado,event_id')
        .eq(columna, pid).execute().data or [], [], 'asistencia progreso')
    eventos_periodo = {e['id'] for e in (db.eventos_equipo(uid) or [])
                       if (e.get('fecha') or '') >= desde_iso}
    #  Solo lo que marco el entrenador. El aviso del jugador no es asistencia.
    puestas = [m for m in marcas_asis
               if m.get('estado') and m['estado'] != 'pendiente'
               and m.get('event_id') in eventos_periodo]
    asistencia = None
    if puestas:
        from collections import Counter
        c = Counter(m['estado'] for m in puestas)
        vino = c.get('presente', 0) + c.get('tarde', 0)
        asistencia = {'total': len(puestas), 'vino': vino,
                      'pct': round(100 * vino / len(puestas)),
                      'tarde': c.get('tarde', 0), 'faltas': c.get('ausente', 0),
                      'justificadas': c.get('justificado', 0)}

    # ─── Lesiones del periodo ───────────────────────────────────────────────
    lesiones = [l for l in (db.rows('fut_injuries', 'lesiones progreso', **dueno) or [])
                if (l.get('fecha') or '') >= desde_iso]
    for l in lesiones:
        l['_fecha'] = db.parse_fecha(l.get('fecha'))

    return render_template('c_progreso_jugador.html',
                           tab_activa='equipo', hide_tabbar=True,
                           jugador=jugador, periodos=PERIODOS, periodo=clave,
                           etiqueta_periodo=next((e for c, e, _ in PERIODOS if c == clave), ''),
                           resumen=resumen, atributos=atributos, tests=tests,
                           familias=familias, movidos=movidos,
                           competicion=competicion, asistencia=asistencia,
                           lesiones=lesiones,
                           es_pro=roles.es_pro(current_user))


def _valoracion_media(coach_id, pid, manual):
    """La media de las valoraciones puestas partido a partido.

    Va aparte de `totales_de_partidos` porque una media no se acumula sumando,
    y porque los partidos sin valoracion no deben arrastrarla hacia abajo: no
    puntuar no es puntuar cero.
    """
    partidos = db.rows('fut_matches', 'partidos rating', coach_id=coach_id) or []
    if not partidos:
        return '—'
    columna = 'manual_player_id' if manual else 'player_id'
    filas = db.q(
        lambda: db.sb().table('fut_match_stats').select('valoracion')
        .in_('match_id', [p['id'] for p in partidos])
        .eq(columna, pid).execute().data or [], [], 'valoraciones')
    notas = [float(f['valoracion']) for f in filas if f.get('valoracion')]
    return round(sum(notas) / len(notas), 1) if notas else '—'


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

    #  Lo de los partidos sale de un solo sitio (db.totales_de_partidos) para
    #  que la hoja del partido, esta ficha y la IA cuenten lo mismo. Antes
    #  aqui se sumaban los goles a mano y solo eso: ni asistencias ni minutos,
    #  que es lo que de verdad dice si un chaval esta jugando o calentando.
    p = db.totales_de_partidos(uid, ids={pid}).get(pid, {})

    cifras = {
        'entrenos': len(db.rows('fut_trainings', 'n entrenos', player_id=pid) or []),
        'goles': p.get('goles', 0),
        'metas': len([m for m in metas if m.get('completada')]),
        'racha': db.racha_actual(pid),
    }
    partidos_jug = {
        'partidos': p.get('partidos', 0),
        'titularidades': p.get('titularidades', 0),
        'minutos': p.get('minutos', 0),
        'goles': p.get('goles', 0),
        'asistencias': p.get('asistencias', 0),
        'jugadas_clave': p.get('jugadas_clave', 0),
        'tarjetas_a': p.get('tarjetas_a', 0),
        'tarjetas_r': p.get('tarjetas_r', 0),
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
                           partidos_jug=partidos_jug,
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
    #  Ya salen de los partidos apuntados TAMBIEN para el que no tiene cuenta:
    #  antes esos no cabian en fut_match_stats y habia que quedarse con las
    #  cifras que el entrenador tecleo al darlo de alta, que nadie volvia a
    #  tocar nunca. Esas se siguen usando, pero solo mientras no haya ni un
    #  partido apuntado: son el punto de partida del que llega a mitad de
    #  temporada, no su ficha para siempre.
    t = db.totales_de_partidos(uid, ids={pid}).get(pid)
    if t:
        stats = {
            'partidos': t['partidos'],
            'minutos': t['minutos'],
            'goles': t['goles'],
            'asistencias': t['asistencias'],
            'jugadas_clave': t['jugadas_clave'],
            'rating': _valoracion_media(uid, pid, manual),
        }
        auto = True
    elif manual:
        stats = {'partidos': '—',
                 'minutos': manual.get('minutos_jugados') or 0,
                 'goles': manual.get('goles') or 0,
                 'asistencias': manual.get('asistencias') or 0,
                 'jugadas_clave': 0,
                 'rating': manual.get('valoracion_promedio') or '—'}
        auto = False
    else:
        stats = {'partidos': 0, 'minutos': 0, 'goles': 0, 'asistencias': 0,
                 'jugadas_clave': 0, 'rating': '—'}
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
    """Redirige al calendario. Esta pantalla ya no pinta nada propio.

    Era una lista de eventos con un alta rápida encima. El alta se retiró
    —duplicaba la del calendario y guardaba peor— y sin ella lo que quedaba
    eran dos enlaces a otras pestañas y una lista de eventos que el calendario
    ya enseña, por día y con su ficha. Una pantalla entera para no aportar
    nada, con su pestaña compitiendo con la de al lado.

    Se deja la ruta redirigiendo en vez de borrarla: la pestaña Agenda apuntaba
    al calendario desde hace tiempo, pero el enlace seguía en el tablero y en
    el botón de volver de Observaciones y Partidos, y alguien puede tenerla
    guardada.
    """
    return redirect(url_for('futbol.c_calendario'))


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
