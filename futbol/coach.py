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

    uid = current_user.id
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
    #  Por ahora el entrenador es uno. Se deja como lista para que añadir
    #  asistentes no obligue a rehacer la tarjeta.
    cuerpo = [{'nombre': current_user.name, 'rol': 'Entrenador Principal',
               'sigla': 'MAIN', 'foto': current_user.profile_photo, 'yo': True}]

    proximos = db.eventos_equipo(uid, desde=hoy.isoformat(),
                                 hasta=(hoy + timedelta(days=14)).isoformat())
    for e in proximos:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))

    return render_template('c_inicio.html',
                           tab_activa='inicio',
                           equipo=equipo,
                           codigo=db.codigo_equipo(uid),
                           jugadores=jugadores,
                           n_jugadores=len(jugadores),
                           activos=activos,
                           n_partidos=n_partidos,
                           estado=estado,
                           n_reportan=n_reportan,
                           solicitudes=solicitudes,
                           cuerpo=cuerpo,
                           eventos=proximos[:3],
                           es_pro=roles.es_pro(current_user))


@bp.route('/coach/equipo/editar')
@solo_entrenador
def c_equipo_editar():
    return render_template('c_equipo_editar.html',
                           hide_tabbar=True,
                           equipo=db.equipo_del_entrenador(current_user.id))


# ═══════════════════════ 2. EQUIPO ═══════════════════════
@bp.route('/coach/plantilla')
@solo_entrenador
def c_equipo():
    uid = current_user.id
    jugadores = db.jugadores_del_entrenador(uid)

    # Media de atributos por jugador, para el badge de nivel
    if jugadores:
        ids = [j['id'] for j in jugadores]
        attrs = db.q(
            lambda: db.sb().table('fut_attributes').select('*').in_('player_id', ids).execute().data or [],
            [], 'atributos equipo')
        by_id = {a['player_id']: a for a in attrs}
        for j in jugadores:
            a = by_id.get(j['id'])
            vals = [a.get(k) for k in db.ATRIBUTOS if a and a.get(k) is not None] if a else []
            j['_media'] = round(sum(vals) / len(vals)) if vals else 50

    return render_template('c_equipo.html',
                           tab_activa='equipo',
                           jugadores=jugadores,
                           equipo=db.equipo_del_entrenador(uid),
                           codigo=db.codigo_equipo(uid))


@bp.route('/coach/jugador/<pid>')
@solo_entrenador
def c_jugador(pid):
    uid = current_user.id
    # Solo se puede ver a un jugador de la propia plantilla.
    jugadores = db.jugadores_del_entrenador(uid)
    jugador = next((j for j in jugadores if str(j['id']) == str(pid)), None)
    if not jugador:
        abort(404)

    entrenos = db.rows('fut_trainings', 'entrenos jug', player_id=pid,
                       _order='fecha', _desc=True, _limit=10)
    for e in entrenos:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))
    evaluaciones = db.rows('fut_evaluations', 'evals jug', player_id=pid,
                           _order='fecha', _desc=True, _limit=5)
    for e in evaluaciones:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))

    return render_template('c_jugador.html',
                           tab_activa='equipo',
                           hide_tabbar=True,
                           jugador=jugador,
                           perfil=db.perfil_jugador(pid),
                           atributos=db.atributos(pid),
                           media=db.media_atributos(pid),
                           entrenos=entrenos,
                           evaluaciones=evaluaciones,
                           racha=db.racha_actual(pid))


@bp.route('/coach/jugador/<pid>/evaluar')
@solo_entrenador
def c_evaluar(pid):
    jugadores = db.jugadores_del_entrenador(current_user.id)
    jugador = next((j for j in jugadores if str(j['id']) == str(pid)), None)
    if not jugador:
        abort(404)
    return render_template('c_evaluar.html',
                           hide_tabbar=True,
                           jugador=jugador,
                           atributos=db.atributos(pid))


# ═══════════════════════ 3. AGENDA ═══════════════════════
@bp.route('/coach/agenda')
@solo_entrenador
def c_agenda():
    uid = current_user.id
    desde = (date.today() - timedelta(days=30)).isoformat()
    hasta = (date.today() + timedelta(days=90)).isoformat()
    eventos = db.eventos_equipo(uid, desde, hasta)

    conteo = {}
    if eventos:
        for a in db.asistencia_de([e['id'] for e in eventos]):
            if a.get('estado') == 'asiste':
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
                           n_jugadores=len(db.jugadores_del_entrenador(uid)))


@bp.route('/coach/agenda/<eid>')
@solo_entrenador
def c_evento(eid):
    uid = current_user.id
    evento = db.one('fut_events', 'evento', id=eid, coach_id=uid)
    if not evento:
        abort(404)
    evento['_fecha'] = db.parse_fecha(evento.get('fecha'))

    jugadores = db.jugadores_del_entrenador(uid)
    estados = {a['player_id']: a.get('estado') for a in db.asistencia_de([eid])}
    for j in jugadores:
        j['_asistencia'] = estados.get(j['id'])

    return render_template('c_evento.html',
                           tab_activa='agenda', hide_tabbar=True,
                           evento=evento, jugadores=jugadores)


# ═══════════════════════ 4. TÁCTICA ═══════════════════════
@bp.route('/coach/tactica')
@solo_entrenador
@roles.solo_pro('tactica')
def c_tactica():
    jugadas = db.rows('fut_tactical_plays', 'jugadas', coach_id=current_user.id,
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
        jugada = db.one('fut_tactical_plays', 'jugada', id=jid, coach_id=current_user.id)
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
    jugadores = db.jugadores_del_entrenador(current_user.id)
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
    uid = current_user.id
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
    uid = current_user.id
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
