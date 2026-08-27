# -*- coding: utf-8 -*-
"""
futbol/player.py — Las 5 pestañas del JUGADOR.

Inicio · Agenda · Progreso · Mi Ficha · IA Coach, en el mismo orden que
navigation/PlayerTabNavigator.tsx. Progreso es un hub con 5 hijas
(Entrenos, Metas, Hábitos, Partidos, Mis Tests), igual que ProgressStack.
"""
import random
from datetime import date, datetime, timedelta
from functools import wraps

from flask import render_template, redirect, url_for, abort
from flask_login import login_required, current_user

import roles

from . import bp, db


# ─── Guardia de rol ──────────────────────────────────────────────────────────
def solo_jugador(f):
    """Las pantallas del jugador no las abre un entrenador: se le manda a las suyas."""
    @wraps(f)
    @login_required
    def wrapper(*a, **kw):
        if getattr(current_user, 'role', '') == 'especialista':
            return redirect(url_for('futbol.c_inicio'))
        return f(*a, **kw)
    return wrapper


# ─── Consejos del día (HomeScreen.tsx › TIPS_BY_CATEGORY) ────────────────────
CONSEJOS = {
    'Hidratación': [
        'Bebe al menos 2 litros de agua al día',
        'Hidrátate antes, durante y después del entrenamiento',
        'Evita las bebidas azucaradas durante el entrenamiento',
        'El agua es tu mejor aliado para mantenerte hidratado',
        'Lleva siempre una botella de agua contigo',
        'La deshidratación afecta tu rendimiento deportivo',
        'Bebe agua aunque no sientas sed',
        'El color de tu orina indica tu nivel de hidratación',
    ],
    'Mentalidad': [
        'Visualiza tu éxito antes de cada partido',
        'Mantén una actitud positiva incluso en derrotas',
        'La confianza se construye día a día',
        'Aprende de cada error sin castigarte',
        'Enfócate en lo que puedes controlar',
        'La presión es un privilegio de los grandes',
        'Celebra tus pequeños logros diarios',
        'La mentalidad ganadora se entrena',
    ],
    'Estiramientos': [
        'Dedica 10 minutos a estirar después de entrenar',
        'Los estiramientos previenen lesiones',
        'Estira cuando tus músculos estén calientes',
        'No rebotes durante los estiramientos',
        'Mantén cada estiramiento por 20-30 segundos',
        'Respira profundamente mientras estiras',
        'Estira todos los grupos musculares principales',
        'La flexibilidad mejora tu rendimiento',
    ],
    'Recuperación': [
        'Duerme entre 7-9 horas cada noche',
        'El descanso es parte del entrenamiento',
        'Alterna días intensos con días suaves',
        'Un buen sueño repara el músculo',
        'Escucha a tu cuerpo cuando pide parar',
        'La recuperación activa acelera el proceso',
        'Evita las pantallas antes de dormir',
        'Un masaje o un baño de contraste ayudan',
    ],
    'Nutrición': [
        'Come proteína después de entrenar',
        'Los carbohidratos son tu combustible',
        'No entrenes en ayunas prolongado',
        'Incluye frutas y verduras cada día',
        'Come algo ligero 2 horas antes del partido',
        'Evita frituras el día previo a competir',
        'El desayuno marca tu energía del día',
        'Come variado: ningún alimento lo tiene todo',
    ],
    'Técnica': [
        'Practica con tu pierna menos hábil',
        'La repetición construye la automatización',
        'Levanta la cabeza antes de recibir',
        'El primer toque define la jugada',
        'Entrena los remates desde varios ángulos',
        'La técnica se mantiene bajo fatiga solo si la entrenas cansado',
        'Observa a los mejores en tu posición',
        'Filma tus entrenamientos y revísalos',
    ],
}

ICONO_CATEGORIA = {
    'Hidratación': 'droplet', 'Mentalidad': 'smile', 'Estiramientos': 'wind',
    'Recuperación': 'moon', 'Nutrición': 'sun', 'Técnica': 'target',
}


def consejo_del_dia(seed_extra=''):
    """Un consejo estable durante todo el día para el mismo usuario."""
    semilla = f'{date.today().isoformat()}|{seed_extra}'
    rnd = random.Random(semilla)
    categoria = rnd.choice(list(CONSEJOS.keys()))
    return categoria, rnd.choice(CONSEJOS[categoria]), ICONO_CATEGORIA[categoria]


def saludo():
    h = datetime.now().hour
    if h < 12:
        return 'Buenos días'
    if h < 19:
        return 'Buenas tardes'
    return 'Buenas noches'


# ═══════════════════════ 1. INICIO ═══════════════════════
@bp.route('/inicio')
@solo_jugador
def inicio():
    uid = current_user.id
    habitos = db.habitos(uid)
    hechos = db.completados_hoy(uid)
    categoria, texto, icono = consejo_del_dia(uid)

    # Check-in de bienestar: pendiente si no hay uno en los últimos 7 días
    ultimo = db.rows('fut_checkins', 'checkin', player_id=uid,
                     _order='fecha', _desc=True, _limit=1)
    ultimo = ultimo[0] if ultimo else None
    hecho_esta_semana = False
    if ultimo:
        f = db.parse_fecha(ultimo.get('fecha'))
        hecho_esta_semana = bool(f and (date.today() - f).days < 7)

    entrenador = db.entrenador_del_jugador(uid)

    # Próximo evento del equipo, para la tarjeta de "lo que viene"
    proximos = db.eventos_para_jugador(uid, desde=db.hoy_iso())[:1]

    # Check-in que el entrenador asignó — manda sobre el ciclo semanal
    from .mental import asignacion_pendiente
    asignacion = asignacion_pendiente(uid)

    # Mensajes personales del coach sin leer
    sin_leer = 0
    if entrenador:
        sin_leer = len(db.rows('fut_messages', 'sin leer',
                               coach_id=entrenador['id'], player_id=uid, leido=False))

    return render_template(
        'p_inicio.html',
        tab_activa='inicio',
        saludo=saludo(),
        habitos_hoy=len(hechos), habitos_total=len(habitos),
        racha=db.racha_actual(uid),
        consejo_categoria=categoria, consejo_texto=texto, consejo_icono=icono,
        checkin_hecho=hecho_esta_semana, ultimo_checkin=ultimo,
        asignacion=asignacion,
        entrenador=entrenador,
        sin_leer=sin_leer,
        proximo=(proximos[0] if proximos else None),
    )


# ═══════════════════════ 2. AGENDA ═══════════════════════
@bp.route('/agenda/<eid>')
@solo_jugador
def p_evento(eid):
    """Un entrenamiento o un partido, con todo lo que el entrenador puso.

    El jugador solo ve los eventos de SU equipo: se resuelve por su entrenador
    y no por el id que venga en la direccion, porque si no cualquiera podria
    leer la agenda de otro club cambiando el numero.
    """
    from . import calendario as cal

    uid = current_user.id
    coach = db.entrenador_del_jugador(uid)
    if not coach:
        return redirect(url_for('futbol.p_unirme'))

    evento = db.one('fut_events', 'evento del jugador', id=eid,
                    coach_id=coach['id'])
    if not evento:
        abort(404)

    evento['_fecha'] = db.parse_fecha(evento.get('fecha'))
    #  La táctica que el entrenador colgó de esta sesión. Es lo que el jugador
    #  venía a mirar: que la jugada esté en la biblioteca no sirve de nada si
    #  hay que buscarla entre veinte el día del partido.
    evento['_jugadas'] = db.jugadas_de_eventos([eid]).get(eid, [])
    meta = cal.ENTRENO_META.get(evento.get('tipo_entreno') or '', {})
    evento['_tipo_entreno'] = meta.get('etiqueta')
    evento['_intensidad'] = dict(
        (c, e) for c, e, _ in cal.INTENSIDADES).get(evento.get('intensidad'))
    if evento.get('tipo') == 'entreno':
        evento['_carga'] = cal.carga_de(evento)

    #  El plan de la sesion, que es donde el entrenador escribe el material y
    #  los bloques. Es lo que de verdad le dice al jugador que va a hacer.
    plan = None
    if evento.get('plan_id'):
        plan = db.one('fut_training_plans', 'plan del evento',
                      id=evento['plan_id'], coach_id=coach['id'])

    #  Dos cosas distintas en la misma fila: lo que el jugador AVISO antes y
    #  lo que el entrenador MARCO despues. La segunda manda.
    marca = (db.asistencia_de([eid], uid) or [None])[0]

    return render_template('p_evento.html',
                           tab_activa='agenda', hide_tabbar=True,
                           evento=evento, plan=plan, entrenador=coach,
                           marca=marca,
                           estados=cal.ESTADOS_ASISTENCIA)


@bp.route('/agenda')
@solo_jugador
def agenda():
    uid = current_user.id
    desde = (date.today() - timedelta(days=7)).isoformat()
    hasta = (date.today() + timedelta(days=60)).isoformat()
    eventos = db.eventos_para_jugador(uid, desde, hasta)

    #  Dos cosas distintas: lo que el jugador AVISO y lo que el entrenador
    #  MARCO. La segunda manda y solo aparece cuando ya paso lista.
    mi_asistencia, mi_aviso = {}, {}
    if eventos:
        for a in db.asistencia_de([e['id'] for e in eventos], uid):
            mi_asistencia[a['event_id']] = a.get('estado')
            mi_aviso[a['event_id']] = (a.get('aviso'), a.get('aviso_motivo') or '')

    hoy = date.today()
    for e in eventos:
        f = db.parse_fecha(e.get('fecha'))
        e['_fecha'] = f
        e['_pasado'] = bool(f and f < hoy)
        e['_hoy'] = bool(f and f == hoy)
        e['_asistencia'] = mi_asistencia.get(e['id'])
        e['_aviso'], e['_aviso_motivo'] = mi_aviso.get(e['id'], (None, ''))

    return render_template('p_agenda.html',
                           tab_activa='agenda',
                           eventos=[e for e in eventos if not e['_pasado']],
                           pasados=[e for e in eventos if e['_pasado']][-5:],
                           entrenador=db.entrenador_del_jugador(uid))


# ═══════════════════════ 3. PROGRESO (hub) ═══════════════════════
@bp.route('/progreso')
@solo_jugador
def progreso():
    uid = current_user.id
    entrenos = db.rows('fut_trainings', 'entrenos', player_id=uid,
                       _order='fecha', _desc=True, _limit=60)
    metas = db.rows('fut_goals', 'metas', player_id=uid)
    habitos = db.habitos(uid)

    semana = date.today() - timedelta(days=7)
    entrenos_semana = [e for e in entrenos
                       if (db.parse_fecha(e.get('fecha')) or date.min) >= semana]
    minutos_semana = sum(int(e.get('duracion_min') or 0) for e in entrenos_semana)

    return render_template('p_progreso.html',
                           tab_activa='progreso',
                           n_entrenos=len(entrenos_semana),
                           minutos_semana=minutos_semana,
                           n_metas=len([m for m in metas if m.get('estado') != 'completada']),
                           n_habitos=len(habitos),
                           racha=db.racha_actual(uid))


@bp.route('/progreso/entrenos')
@solo_jugador
def entrenos():
    uid = current_user.id
    lista = db.rows('fut_trainings', 'entrenos', player_id=uid,
                    _order='fecha', _desc=True, _limit=100)
    for e in lista:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))
    return render_template('p_entrenos.html',
                           tab_activa='progreso', entrenos=lista,
                           hoy=db.hoy_iso())


@bp.route('/progreso/metas')
@solo_jugador
def metas():
    uid = current_user.id
    lista = db.rows('fut_goals', 'metas', player_id=uid, _order='creado', _desc=True)
    activas = [m for m in lista if m.get('estado') != 'completada']
    hechas = [m for m in lista if m.get('estado') == 'completada']
    return render_template('p_metas.html',
                           tab_activa='progreso', activas=activas, hechas=hechas)


@bp.route('/progreso/habitos')
@solo_jugador
def habitos_page():
    uid = current_user.id
    lista = db.habitos(uid)
    hechos = db.completados_hoy(uid)
    for h in lista:
        h['_hecho'] = h['id'] in hechos

    # Rejilla de los últimos 7 días, como en HabitsScreen
    dias = [(date.today() - timedelta(days=i)) for i in range(6, -1, -1)]
    marcas = db.rows('fut_habit_completions', 'marcas7', player_id=uid)
    por_dia = {}
    for m in marcas:
        if m.get('hecho'):
            por_dia.setdefault(str(m.get('fecha'))[:10], set()).add(m['habit_id'])

    return render_template('p_habitos.html',
                           tab_activa='progreso', habitos=lista,
                           racha=db.racha_actual(uid),
                           dias=dias, por_dia=por_dia)


@bp.route('/progreso/partidos')
@solo_jugador
def partidos():
    uid = current_user.id
    coach = db.entrenador_del_jugador(uid)
    lista, mis_stats = [], {}
    if coach:
        lista = db.rows('fut_matches', 'partidos', coach_id=coach['id'],
                        _order='fecha', _desc=True, _limit=40)
        if lista:
            ids = [m['id'] for m in lista]
            stats = db.q(
                lambda: db.sb().table('fut_match_stats').select('*')
                .in_('match_id', ids).eq('player_id', uid).execute().data or [],
                [], 'mis stats')
            mis_stats = {s['match_id']: s for s in stats}

    #  Las cifras salen de db.totales_de_partidos, el mismo sitio del que las
    #  saca la ficha que ve el entrenador. Antes se sumaban aqui aparte y con
    #  otro criterio —contaba como jugado un partido con cero minutos—, asi
    #  que el jugador y su entrenador podian leer numeros distintos del mismo
    #  chaval. Y faltaban las jugadas clave, las titularidades y las tarjetas.
    t = {}
    if coach:
        t = db.totales_de_partidos(coach['id'], ids={uid},
                                   partidos=lista or None).get(uid, {})
    totales = {
        'partidos': t.get('partidos', 0), 'minutos': t.get('minutos', 0),
        'goles': t.get('goles', 0), 'asistencias': t.get('asistencias', 0),
        'jugadas_clave': t.get('jugadas_clave', 0),
        'titularidades': t.get('titularidades', 0),
        'tarjetas_a': t.get('tarjetas_a', 0), 'tarjetas_r': t.get('tarjetas_r', 0),
    }
    for m in lista:
        m['_fecha'] = db.parse_fecha(m.get('fecha'))
        m['_stats'] = mis_stats.get(m['id'])

    return render_template('p_partidos.html',
                           tab_activa='progreso', partidos=lista,
                           totales=totales, tiene_equipo=bool(coach))


@bp.route('/progreso/tests')
@solo_jugador
def mis_tests():
    uid = current_user.id
    resultados = db.rows('fut_test_results', 'mis tests', player_id=uid,
                         _order='creado', _desc=True, _limit=60)
    tests_by_id = {}
    if resultados:
        ids = list({r['test_id'] for r in resultados if r.get('test_id')})
        if ids:
            pruebas = db.q(
                lambda: db.sb().table('fut_tests').select('*').in_('id', ids).execute().data or [],
                [], 'tests')
            tests_by_id = {t['id']: t for t in pruebas}
    for r in resultados:
        r['_test'] = tests_by_id.get(r.get('test_id'), {})
    return render_template('p_tests.html',
                           tab_activa='progreso', resultados=resultados)


# ═══════════════════════ 4. MI FICHA ═══════════════════════
@bp.route('/ficha')
@solo_jugador
def ficha():
    uid = current_user.id
    atributos = db.atributos(uid)
    perfil = db.perfil_jugador(uid)
    evaluaciones = db.rows('fut_evaluations', 'evaluaciones', player_id=uid,
                           _order='fecha', _desc=True, _limit=10)
    for e in evaluaciones:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))

    return render_template('p_ficha.html',
                           tab_activa='ficha',
                           estado={
                               'energia': perfil.get('energia'),
                               'motivacion': perfil.get('motivacion'),
                               'estado_fisico': perfil.get('estado_fisico'),
                           },
                           atributos=atributos,
                           media=db.media_atributos(uid),
                           perfil=perfil,
                           evaluaciones=evaluaciones,
                           entrenador=db.entrenador_del_jugador(uid))


# ═══════════════════════ JUGADAS DEL ENTRENADOR ═══════════════════════
@bp.route('/tactica')
@solo_jugador
def p_tactica():
    """Las jugadas de su entrenador, en solo lectura.

    El jugador tiene que poder repasar la jugada en casa; que solo la vea en
    la pizarra del vestuario es la razón por la que nadie se acuerda el sábado.
    """
    uid = current_user.id
    coach = db.entrenador_del_jugador(uid)
    jugadas = []
    if coach:
        jugadas = db.rows('fut_tactical_plays', 'jugadas jugador',
                          coach_id=coach['id'], _order='creado', _desc=True) or []
        for j in jugadas:
            j['_fecha'] = db.parse_fecha(j.get('creado'))
            j['_momentos'] = len((j.get('datos') or {}).get('momentos') or [])
    return render_template('p_tactica.html',
                           tab_activa='', hide_tabbar=True,
                           jugadas=jugadas, entrenador=coach)


@bp.route('/tactica/<jid>')
@solo_jugador
def p_jugada(jid):
    uid = current_user.id
    coach = db.entrenador_del_jugador(uid)
    if not coach:
        abort(404)
    # Solo las jugadas de SU entrenador: el id no basta como permiso.
    jugada = db.one('fut_tactical_plays', 'jugada jugador',
                    id=jid, coach_id=coach['id'])
    if not jugada:
        abort(404)
    jugada['_fecha'] = db.parse_fecha(jugada.get('creado'))
    return render_template('p_jugada.html',
                           tab_activa='', hide_tabbar=True,
                           jugada=jugada, entrenador=coach,
                           momentos=len((jugada.get('datos') or {}).get('momentos') or []))


# ═══════════════════════ 5. IA COACH ═══════════════════════
@bp.route('/ia')
@solo_jugador
def ia_jugador():
    historial = db.rows('fut_ia_chat', 'chat ia', user_id=current_user.id,
                        _order='creado', _limit=40)
    return render_template('p_ia.html',
                           tab_activa='ia', historial=historial,
                           ia_restantes=roles.ia_restantes(current_user),
                           ia_tope=roles.IA_MENSAJES_GRATIS)


# ═══════════════════════ CHECK-IN DE BIENESTAR ═══════════════════════
PREGUNTAS_CHECKIN = [
    ('animo',      '¿Cómo está tu ánimo hoy?',                    'Muy bajo', 'Excelente'),
    ('energia',    '¿Cuánta energía sientes?',                     'Agotado',  'Con todo'),
    ('sueno',      '¿Qué tal dormiste?',                           'Muy mal',  'De maravilla'),
    ('estres',     '¿Qué tan tranquilo te sientes?',               'Muy tenso', 'Muy tranquilo'),
    ('dolor',      '¿Qué tan libre de molestias estás?',           'Con dolor', 'Sin molestias'),
    ('motivacion', '¿Con cuántas ganas llegas a entrenar?',        'Ninguna',  'Muchísimas'),
    ('confianza',  '¿Cuánta confianza tienes en tu juego?',        'Muy poca', 'Mucha'),
    ('equipo',     '¿Qué tan a gusto estás con el grupo?',         'Nada',     'Muy a gusto'),
]


@bp.route('/checkin')
@solo_jugador
def checkin():
    return render_template('p_checkin.html',
                           hide_tabbar=True,          # es un asistente a pantalla completa
                           preguntas=PREGUNTAS_CHECKIN)


@bp.route('/checkin/resultado/<cid>')
@solo_jugador
def checkin_resultado(cid):
    reg = db.one('fut_checkins', 'checkin res', id=cid, player_id=current_user.id)
    if not reg:
        abort(404)
    return render_template('p_checkin_result.html',
                           hide_tabbar=True, checkin=reg,
                           preguntas=PREGUNTAS_CHECKIN)
