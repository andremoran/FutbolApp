# -*- coding: utf-8 -*-
"""
futbol/db.py — Acceso a datos de FutbolApp sobre su propio Supabase.

Los usuarios viven en la tabla `usuarios` (rol='especialista' para el
entrenador, 'paciente' para el jugador) y la plantilla del equipo en
`fut_plantilla`.

Regla del módulo: NUNCA reventar por una tabla que todavía no existe. Mientras
no se corra sql/schema.sql, cada consulta devuelve vacío y la pantalla se ve
como "sin datos" en vez de dar error 500.
"""
import logging
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# El cliente de Supabase se inyecta desde app.py al registrar el Blueprint.
_sb = None


def init(supabase_client):
    global _sb
    _sb = supabase_client


def sb():
    return _sb


# ─── Envoltorio tolerante ────────────────────────────────────────────────────
def q(fn, default=None, ctx=''):
    """Ejecuta una consulta y devuelve `default` si falla.

    Una tabla fut_ ausente, un fallo de red o un permiso RLS no deben tumbar la
    pantalla: se registra y se sigue. `ctx` sirve para ubicar el problema en el log.
    """
    try:
        return fn()
    except Exception as e:
        msg = str(e)
        # Tabla inexistente todavía: es lo esperado antes de correr el .sql
        if 'does not exist' in msg or 'PGRST205' in msg or 'PGRST202' in msg:
            logger.info('db: tabla ausente (%s) — devuelvo vacío. Corre sql/schema.sql', ctx)
        else:
            logger.warning('db error en %s: %s', ctx, msg)
        return default


def rows(table, ctx='', **filters):
    """SELECT * con filtros de igualdad. Azúcar para el 80% de las consultas."""
    def _go():
        sel = _sb.table(table).select('*')
        order = filters.pop('_order', None)
        desc = filters.pop('_desc', False)
        limit = filters.pop('_limit', None)
        for k, v in filters.items():
            sel = sel.eq(k, v)
        if order:
            sel = sel.order(order, desc=desc)
        if limit:
            sel = sel.limit(limit)
        return sel.execute().data or []
    return q(_go, [], ctx or table)


def one(table, ctx='', **filters):
    r = rows(table, ctx, **filters)
    return r[0] if r else None


class ErrorDeEscritura(Exception):
    """Una escritura que TENIA que salir bien y no salio.

    `q()` se traga los errores a proposito: que falte una tabla o falle la red
    no debe tumbar una pantalla de lectura. Pero en una ESCRITURA ese mismo
    silencio es dañino — el usuario guarda, se le dice que si, y no se guardo
    nada. Paso de verdad con pasar lista: `fut_attendance.player_id` era NOT
    NULL, fallaba con todos los jugadores sin cuenta y la pantalla respondia
    «Lista guardada» igual.

    Se lanza solo con `obligatorio=True`, en las escrituras que SON el objeto de
    la peticion. Las de mejor esfuerzo —guardar el historial del chat de IA, por
    ejemplo— siguen fallando en silencio a proposito: si no se guarda el
    historial, el usuario debe recibir su respuesta igual.
    """


def insert(table, data, ctx='', obligatorio=False):
    def _go():
        return (_sb.table(table).insert(data).execute().data or [None])[0]
    fila = q(_go, None, ctx or ('insert ' + table))
    if obligatorio and not fila:
        raise ErrorDeEscritura('no se pudo insertar en %s (%s)' % (table, ctx))
    return fila


def update(table, data, ctx='', obligatorio=False, **filters):
    def _go():
        upd = _sb.table(table).update(data)
        for k, v in filters.items():
            upd = upd.eq(k, v)
        return upd.execute().data
    filas = q(_go, None, ctx or ('update ' + table))
    #  Una lista vacia tambien es un fallo cuando la escritura es obligatoria:
    #  significa que el filtro no encontro la fila, o sea que no se actualizo
    #  nada aunque no hubiera excepcion.
    if obligatorio and not filas:
        raise ErrorDeEscritura('no se pudo actualizar %s (%s)' % (table, ctx))
    return filas


def upsert(table, data, ctx='', on_conflict=None):
    def _go():
        t = _sb.table(table)
        res = t.upsert(data, on_conflict=on_conflict) if on_conflict else t.upsert(data)
        return (res.execute().data or [None])[0]
    return q(_go, None, ctx or ('upsert ' + table))


def delete(table, ctx='', obligatorio=False, **filters):
    def _go():
        d = _sb.table(table).delete()
        for k, v in filters.items():
            d = d.eq(k, v)
        return d.execute().data
    filas = q(_go, None, ctx or ('delete ' + table))
    if obligatorio and filas is None:
        raise ErrorDeEscritura('no se pudo borrar de %s (%s)' % (table, ctx))
    return filas


# ─── Cuerpo técnico: principal y asistentes ──────────────────────────────────
#  En esta app el EQUIPO se identifica por el id del entrenador principal:
#  fut_plantilla.coach_id, fut_events.coach_id, fut_eval_results.coach_id…
#  todos apuntan a él. Cuando entra un asistente, lo que anota tiene que caer
#  en ese mismo equipo, no en uno suyo.
#
#  `equipo_id()` es la traducción: «quién soy» → «de qué equipo escribo». Las
#  vistas hacen `uid = db.equipo_id(current_user.id)` al principio y todo lo
#  demás sigue funcionando igual, sin tocar cien consultas.
def equipo_id(coach_id):
    """El id del equipo al que pertenece este entrenador.

    Devuelve su propio id si es principal (o si no está en ningún cuerpo
    técnico), y el del principal si es asistente.
    """
    if not coach_id:
        return coach_id
    fila = one('fut_team_coaches', 'equipo del coach',
               coach_id=coach_id, estado='activo')
    if fila and fila.get('rol') == 'asistente' and fila.get('principal_id'):
        return fila['principal_id']
    return coach_id


def es_asistente(coach_id):
    fila = one('fut_team_coaches', 'rol coach', coach_id=coach_id, estado='activo')
    return bool(fila and fila.get('rol') == 'asistente')


def cuerpo_tecnico(principal_id):
    """El principal y sus asistentes, en orden, con sus datos de persona."""
    filas = rows('fut_team_coaches', 'cuerpo', principal_id=principal_id,
                 estado='activo') or []
    ids = [principal_id] + [f['coach_id'] for f in filas
                            if f.get('rol') == 'asistente']
    if not ids:
        return []
    personas = q(
        lambda: _sb.table('usuarios').select('id, nombre, correo, foto')
        .in_('id', ids).execute().data or [], [], 'cuerpo tecnico')
    por_id = {p['id']: p for p in personas}

    salida = []
    p = por_id.get(principal_id)
    if p:
        salida.append({'id': p['id'], 'nombre': p.get('nombre'),
                       'correo': p.get('correo'), 'foto': p.get('foto'),
                       'rol': 'principal', 'etiqueta': 'Entrenador Principal',
                       'sigla': 'MAIN', 'desde': None})
    for f in filas:
        if f.get('rol') != 'asistente':
            continue
        a = por_id.get(f['coach_id'])
        if a:
            salida.append({'id': a['id'], 'nombre': a.get('nombre'),
                           'correo': a.get('correo'), 'foto': a.get('foto'),
                           'rol': 'asistente', 'etiqueta': 'Asistente Técnico',
                           'sigla': 'ASST', 'desde': parse_fecha(f.get('creado'))})
    return salida


def nombres_de(ids):
    """{id: nombre} para firmar quién anotó cada cosa, en una sola consulta."""
    ids = [i for i in set(ids or []) if i]
    if not ids:
        return {}
    personas = q(
        lambda: _sb.table('usuarios').select('id, nombre').in_('id', ids)
        .execute().data or [], [], 'nombres')
    return {p['id']: p.get('nombre') for p in personas}


# ─── Equipo: entrenador ↔ jugadores ──────────────────────────────────────────
def _normalizar_usuario(u):
    """Traduce la fila de `usuarios` a las claves que esperan las plantillas.

    Las plantillas se escribieron contra los nombres antiguos (name, gender,
    weight…); mantenerlos aquí evita tocar 35 archivos.
    """
    if not u:
        return {}
    u = dict(u)
    u['name'] = u.get('nombre')
    u['gender'] = u.get('genero')
    u['weight'] = u.get('peso')
    u['height'] = u.get('estatura')
    u['last_weight'] = u.get('peso')
    u['last_height'] = u.get('estatura')
    u['profile_photo'] = u.get('foto')
    u['codigo_profesional'] = u.get('codigo_equipo')
    return u


def equipo_del_entrenador(coach_id):
    """Devuelve (o compone al vuelo) la ficha del equipo del entrenador."""
    eq = one('fut_teams', 'equipo', coach_id=coach_id)
    if eq:
        return eq
    # Sin ficha propia todavía: el equipo "existe" igual, con el nombre del
    # entrenador y su código. Así la app funciona desde el primer minuto.
    u = one('usuarios', 'coach', id=coach_id) or {}
    return {
        'id': None,
        'coach_id': coach_id,
        'nombre': u.get('club') or (u.get('nombre') or 'Mi equipo'),
        'categoria': '',
        'codigo': u.get('codigo_equipo') or '',
        'escudo_url': None,
        '_provisional': True,
    }


def codigo_equipo(coach_id):
    """El código con el que un jugador se une al equipo."""
    u = one('usuarios', 'codigo equipo', id=coach_id) or {}
    return u.get('codigo_equipo') or ''


def jugadores_del_entrenador(coach_id):
    """Plantilla del equipo."""
    vinculos = rows('fut_plantilla', 'plantilla', coach_id=coach_id, activo=True)
    ids = [v['player_id'] for v in vinculos if v.get('player_id')]
    if not ids:
        return []

    jugadores = q(
        lambda: _sb.table('usuarios').select('*').in_('id', ids).execute().data or [],
        [], 'jugadores')
    jugadores = [_normalizar_usuario(j) for j in jugadores]

    # Anexar la ficha futbolística (posición, dorsal) de cada jugador
    perfiles = q(
        lambda: _sb.table('fut_player_profile').select('*').in_('user_id', ids).execute().data or [],
        [], 'perfiles')
    by_id = {p['user_id']: p for p in perfiles}
    for j in jugadores:
        j['fut'] = by_id.get(j['id'], {})

    return sorted(jugadores,
                  key=lambda j: (j.get('fut', {}).get('dorsal') or 999, j.get('name') or ''))


def plantilla_completa(coach_id):
    """TODOS los del equipo: con cuenta y sin ella, en una sola lista.

    Existe porque `jugadores_del_entrenador` devuelve solo a los que tienen
    cuenta, y media aplicacion la usaba creyendo que era la plantilla entera.
    En un equipo de formacion casi nadie se registra: la hoja de estadisticas
    del partido salia vacia y no se podia apuntar nada de nadie. Es el mismo
    despiste que ya hubo con la asistencia y con el contexto de la IA, asi que
    aqui esta el sitio unico donde se junta.

    Cada uno sale con la misma forma, venga de donde venga:
        id, nombre, dorsal, posicion, es_manual, foto
    """
    salida = []
    for j in jugadores_del_entrenador(coach_id):
        f = j.get('fut') or {}
        salida.append({
            'id': j['id'], 'nombre': j.get('name') or 'Sin nombre',
            'dorsal': f.get('dorsal'), 'posicion': f.get('posicion'),
            'es_manual': False, 'foto': j.get('profile_photo'),
        })
    for m in rows('fut_manual_players', 'plantilla manual',
                  coach_id=coach_id, activo=True) or []:
        salida.append({
            'id': m['id'], 'nombre': m.get('nombre') or 'Sin nombre',
            'dorsal': m.get('dorsal'), 'posicion': m.get('posicion'),
            'es_manual': True, 'foto': m.get('foto'),
        })
    return sorted(salida, key=lambda x: (x['dorsal'] or 999, x['nombre']))


#  Lo que se suma de los partidos. Se nombran aqui para que la hoja del
#  partido, el perfil del jugador y la IA cuenten LO MISMO: si cada pantalla
#  elige sus campos, dos sitios acaban dando cifras distintas del mismo chaval.
CAMPOS_PARTIDO = ('minutos', 'goles', 'asistencias', 'jugadas_clave',
                  'tarjetas_a', 'tarjetas_r')


def totales_de_partidos(coach_id, ids=None, partidos=None):
    """Lo acumulado en partidos por cada jugador del equipo.

    Devuelve {id_del_jugador: {partidos, minutos, goles, asistencias, ...}}.
    La clave es el id del jugador, tenga cuenta o no: quien llama no tiene por
    que saber en cual de las dos columnas estaba guardado.

    Se hace en dos consultas para todo el equipo, no una por jugador: el
    perfil y la lista de plantilla los piden de golpe.
    """
    #  Los trae quien llama si ya los tiene: el contexto de la IA necesita
    #  los partidos para contar el balance y no hay que pedirlos dos veces.
    if partidos is None:
        partidos = rows('fut_matches', 'partidos del equipo', coach_id=coach_id) or []
    if not partidos:
        return {}
    mids = [p['id'] for p in partidos]

    filas = q(lambda: _sb.table('fut_match_stats').select('*')
              .in_('match_id', mids).execute().data or [], [], 'stats equipo')

    tot = {}
    for f in filas:
        clave = f.get('player_id') or f.get('manual_player_id')
        if not clave or (ids is not None and clave not in ids):
            continue
        t = tot.setdefault(clave, dict(
            {c: 0 for c in CAMPOS_PARTIDO}, partidos=0, titularidades=0))
        #  Cuenta como partido jugado si de verdad piso el campo. Una fila a
        #  cero entera es «estaba en la lista y no jugo», y sumarla le bajaria
        #  la media a quien no llego a entrar.
        #
        #  Pero no basta con mirar los minutos: el entrenador apunta los goles
        #  en caliente y los minutos muchas veces no los pone. Con la regla
        #  anterior, quien marcaba dos y no tenia minutos escritos salia con
        #  «2 goles en 0 partidos». Quien marca, asiste, ve una tarjeta o sale
        #  de titular, jugo.
        jugo = ((f.get('minutos') or 0) > 0 or f.get('titular')
                or any((f.get(c) or 0) for c in CAMPOS_PARTIDO))
        if jugo:
            t['partidos'] += 1
        if f.get('titular'):
            t['titularidades'] += 1
        for c in CAMPOS_PARTIDO:
            t[c] += int(f.get(c) or 0)
    return tot


def tamano_plantilla(coach_id):
    """Cuántos jugadores tiene el equipo, con cuenta y sin ella.

    Existe porque este cálculo estaba repetido a mano por media docena de
    pantallas y en varias se había olvidado sumar los que no tienen cuenta:
    un equipo de formación lleno se veía como si estuviera vacío.
    """
    return (len(jugadores_del_entrenador(coach_id))
            + len(rows('fut_manual_players', 'tamano plantilla',
                       coach_id=coach_id, activo=True) or []))


def entrenador_del_jugador(player_id):
    """Entrenador vinculado al jugador (o None si aún no se unió a un equipo)."""
    v = one('fut_plantilla', 'mi coach', player_id=player_id, activo=True)
    if not v:
        return None
    return _normalizar_usuario(one('usuarios', 'coach del jugador', id=v['coach_id']))


def perfil_jugador(player_id):
    """Ficha futbolística: posición, dorsal, pie hábil…"""
    return one('fut_player_profile', 'perfil jugador', user_id=player_id) or {}


# ─── Posiciones ──────────────────────────────────────────────────────────────
#  En la app conviven DOS vocabularios de posición: el detallado del alta a
#  mano (equipo.py › POSICIONES: «Lateral derecho», «Mediapunta») y el corto de
#  la ficha del jugador con cuenta («lateral», «medio»). La pantalla de Equipo
#  filtra por las cuatro familias de TeamPlayersScreen.tsx, así que hay que
#  traducir: sin esto, filtrar por «Defensa» no encontraría a un «Central».
_FAMILIAS_POSICION = (
    ('Portero',       ('portero', 'arquero', 'guardameta')),
    ('Defensa',       ('central', 'defensa', 'lateral', 'libero', 'zaguero')),
    ('Mediocampista', ('pivote', 'interior', 'mediapunta', 'mediocentro',
                       'medio', 'volante', 'centrocampista')),
    ('Delantero',     ('delantero', 'extremo', 'punta', 'ariete', 'atacante')),
)


def familia_posicion(posicion):
    """La familia con la que se filtra en Equipo, venga como venga escrita."""
    texto = (posicion or '').strip().lower()
    if not texto:
        return 'Sin posición'
    for familia, palabras in _FAMILIAS_POSICION:
        if any(p in texto for p in palabras):
            return familia
    return 'Sin posición'


# ─── Hábitos ─────────────────────────────────────────────────────────────────
def habitos(player_id):
    return rows('fut_habits', 'habitos', player_id=player_id, activo=True, _order='creado')


def completados_hoy(player_id, dia=None):
    dia = (dia or date.today()).isoformat()
    hechos = rows('fut_habit_completions', 'completados', player_id=player_id, fecha=dia)
    return {h['habit_id'] for h in hechos if h.get('hecho')}


def racha_actual(player_id):
    """Días seguidos, hasta hoy, en que el jugador completó al menos un hábito."""
    def _go():
        desde = (date.today() - timedelta(days=90)).isoformat()
        res = (_sb.table('fut_habit_completions')
               .select('fecha')
               .eq('player_id', player_id).eq('hecho', True)
               .gte('fecha', desde).execute())
        return res.data or []
    marcas = q(_go, [], 'racha')
    dias = {m['fecha'][:10] for m in marcas if m.get('fecha')}
    if not dias:
        return 0
    hoy = date.today()
    # Si hoy aún no marcó nada, la racha puede seguir viva desde ayer.
    cursor = hoy if hoy.isoformat() in dias else hoy - timedelta(days=1)
    racha = 0
    while cursor.isoformat() in dias:
        racha += 1
        cursor -= timedelta(days=1)
    return racha


# ─── Agenda ──────────────────────────────────────────────────────────────────
def eventos_equipo(coach_id, desde=None, hasta=None):
    def _go():
        sel = _sb.table('fut_events').select('*').eq('coach_id', coach_id)
        if desde:
            sel = sel.gte('fecha', desde)
        if hasta:
            sel = sel.lte('fecha', hasta)
        return sel.order('fecha').execute().data or []
    return q(_go, [], 'eventos')


def eventos_para_jugador(player_id, desde=None, hasta=None):
    coach = entrenador_del_jugador(player_id)
    if not coach:
        return []
    return eventos_equipo(coach['id'], desde, hasta)


def asistencia_de(event_ids, player_id=None):
    if not event_ids:
        return []

    def _go():
        sel = _sb.table('fut_attendance').select('*').in_('event_id', event_ids)
        if player_id:
            sel = sel.eq('player_id', player_id)
        return sel.execute().data or []
    return q(_go, [], 'asistencia')


# ─── Atributos y evaluaciones ────────────────────────────────────────────────
ATRIBUTOS = ['tecnica', 'fisico', 'tactico', 'mental']


def atributos(player_id):
    a = one('fut_attributes', 'atributos', player_id=player_id)
    if not a:
        # Punto de partida neutro: 50/100 en todo, como hace la app al crear un jugador.
        return {k: 50 for k in ATRIBUTOS}
    return {k: (a.get(k) if a.get(k) is not None else 50) for k in ATRIBUTOS}


def media_atributos(player_id):
    a = atributos(player_id)
    return round(sum(a.values()) / len(a))


# ─── Perfil Dinámico: los 18 atributos ───────────────────────────────────────
#  Los 4 de arriba (ATRIBUTOS) no se borran — cada uno sigue vivo como la
#  media de su familia — pero la app real evalúa con dieciocho, repartidos en
#  tres familias, y de su media (1-10 cada uno) sale el `overall` 0-100 que se
#  ve en el círculo de cada tarjeta. Ver sql/schema_v3_perfil_dinamico.sql.
#
#  Sirve tanto para un jugador con cuenta (`player_id`) como sin cuenta
#  (`manual_player_id`) — nunca los dos a la vez; ese es el cambio que hizo
#  falta en el esquema para que el Perfil Dinámico también viva en un jugador
#  apuntado a mano, que es justo el caso de la pantalla «Nuevo Jugador».
ATRIBUTOS_TECNICOS = ['pase', 'control', 'regate', 'tiro', 'definicion', 'centros', 'vision_juego']
ATRIBUTOS_FISICOS = ['velocidad', 'resistencia', 'fuerza', 'agilidad', 'aceleracion']
ATRIBUTOS_MENTALES = ['liderazgo', 'disciplina', 'concentracion', 'confianza', 'trabajo_equipo', 'mentalidad']
ATRIBUTOS_18 = ATRIBUTOS_TECNICOS + ATRIBUTOS_FISICOS + ATRIBUTOS_MENTALES

_CAMPOS_ESTADO = ('fatiga', 'riesgo_sobrecarga', 'fortalezas', 'debilidades',
                  'evolucion_tecnica', 'lesiones_historial', 'posicion_secundaria')


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def dueno_filtro(player_id=None, manual_player_id=None):
    """Normaliza el par (con cuenta / sin cuenta): exactamente uno de los dos."""
    if player_id:
        return {'player_id': player_id}
    if manual_player_id:
        return {'manual_player_id': manual_player_id}
    return {}


def _upsert_dueno(table, dueno, datos, ctx=''):
    """Upsert manual sobre una tabla con «dueño» opcional (jugador con o sin
    cuenta). No se usa el `on_conflict` de Supabase porque la unicidad de
    estas tablas es con índices PARCIALES (uno para player_id, otro para
    manual_player_id) y PostgREST no sabe apuntar un ON CONFLICT a un índice
    parcial solo con nombres de columna — se resuelve leyendo primero.
    """
    existente = one(table, ctx, **dueno)
    if existente:
        return update(table, datos, ctx, **dueno) and {**existente, **datos}
    return insert(table, {**dueno, **datos}, ctx)


def fila_atributos(player_id=None, manual_player_id=None):
    """La fila cruda de fut_attributes, o None si el jugador nunca fue evaluado."""
    dueno = dueno_filtro(player_id, manual_player_id)
    if not dueno:
        return None
    return one('fut_attributes', 'fila atributos', **dueno)


#  Los 18 atributos van en escala 1-100, igual que en la app
#  (PlayerEvaluationScreen.tsx: «los 18 atributos son la fuente de verdad,
#  escala 1-100»). El overall es su media directa, sin convertir nada: por eso
#  un jugador con casi todo en 50 tiene overall 49 o 50.
ESCALA_MIN, ESCALA_MAX = 1, 100


def calcular_overall(valores):
    """Media de los 18 (escala 1-100). `None` si no hay ninguno."""
    vals = [valores.get(k) for k in ATRIBUTOS_18 if valores.get(k) is not None]
    if not vals:
        return None
    return max(ESCALA_MIN, min(ESCALA_MAX, round(sum(vals) / len(vals))))


def _media_familia(valores, claves):
    """Igual que calcular_overall pero para una sola familia (TÉC/FÍS/MEN)."""
    vals = [valores.get(k) for k in claves if valores.get(k) is not None]
    if not vals:
        return None
    return max(ESCALA_MIN, min(ESCALA_MAX, round(sum(vals) / len(vals))))


def ficha_atributos(player_id=None, manual_player_id=None):
    """Los 18 atributos + overall/potencial/estado, listos para pintar.

    Los huecos se muestran como 5/10 (punto de partida neutro), pero eso es
    solo para no dejar la pantalla en blanco — nunca se guarda un valor que
    nadie evaluó. `_tiene_perfil` distingue "aún sin evaluar" de verdad.
    """
    fila = fila_atributos(player_id, manual_player_id) or {}
    tiene_perfil = fila.get('overall') is not None

    ficha = {k: (fila.get(k) if fila.get(k) is not None else 50) for k in ATRIBUTOS_18}
    ficha['overall'] = fila.get('overall') if fila.get('overall') is not None else 50
    ficha['potencial'] = fila.get('potencial') if fila.get('potencial') is not None else ficha['overall']
    ficha['media_tecnica'] = _media_familia(fila, ATRIBUTOS_TECNICOS) or 50
    ficha['media_fisica'] = _media_familia(fila, ATRIBUTOS_FISICOS) or 50
    ficha['media_mental'] = _media_familia(fila, ATRIBUTOS_MENTALES) or 50
    ficha['fatiga'] = fila.get('fatiga')
    ficha['riesgo_sobrecarga'] = fila.get('riesgo_sobrecarga') or 'bajo'
    ficha['fortalezas'] = fila.get('fortalezas') or ''
    ficha['debilidades'] = fila.get('debilidades') or ''
    ficha['evolucion_tecnica'] = fila.get('evolucion_tecnica') or ''
    ficha['lesiones_historial'] = fila.get('lesiones_historial') or ''
    ficha['posicion_secundaria'] = fila.get('posicion_secundaria') or ''
    ficha['_tiene_perfil'] = tiene_perfil
    return ficha


def guardar_atributos(player_id=None, manual_player_id=None, **campos):
    """Upsert de la ficha de un jugador (con o sin cuenta).

    `campos` puede traer cualquiera de los 18 (escala 1-10), `potencial`
    (0-100) y los campos de `_CAMPOS_ESTADO`. El overall y las tres medias por
    familia (que alimentan tecnica/fisico/mental, los 4 de siempre) se
    recalculan siempre a partir de lo que quede guardado. Si es la primera
    vez que se evalúa y no llega `potencial`, se deja igual al overall recién
    calculado — es un techo estimado del entrenador, no algo que la fórmula
    deba inventar (eso lo hará la IA más adelante).
    """
    dueno = dueno_filtro(player_id, manual_player_id)
    if not dueno:
        return None

    actual = fila_atributos(player_id, manual_player_id) or {}
    fusion = dict(actual)
    fusion.update({k: v for k, v in campos.items()
                   if k in ATRIBUTOS_18 or k in _CAMPOS_ESTADO or k == 'potencial'})

    datos = {k: fusion[k] for k in ATRIBUTOS_18 if fusion.get(k) is not None}
    overall = calcular_overall(fusion)
    if overall is not None:
        datos['overall'] = overall
        datos['potencial'] = fusion.get('potencial') if fusion.get('potencial') is not None else overall
        for clave, familia in (('tecnica', ATRIBUTOS_TECNICOS),
                               ('fisico', ATRIBUTOS_FISICOS),
                               ('mental', ATRIBUTOS_MENTALES)):
            media = _media_familia(fusion, familia)
            if media is not None:
                datos[clave] = media
    for campo in _CAMPOS_ESTADO:
        if campo in fusion:
            datos[campo] = fusion[campo]
    datos['actualizado'] = _ahora()

    return _upsert_dueno('fut_attributes', dueno, datos, 'guardar atributos')


def guardar_familias(player_id, valores):
    """Escribe solo las 4 familias clásicas (0-100), sin tocar los 18.

    Lo usa evaluaciones.py cuando la marca de una prueba mueve la ficha del
    jugador. No puede ser un `upsert(on_conflict='player_id')`: desde
    schema_v3 la unicidad de fut_attributes es un índice PARCIAL, y Postgres
    no admite ON CONFLICT contra un índice parcial.
    """
    dueno = dueno_filtro(player_id=player_id)
    if not dueno:
        return None
    datos = {k: v for k, v in valores.items() if k in ATRIBUTOS}
    if not datos:
        return None
    datos['actualizado'] = _ahora()
    return _upsert_dueno('fut_attributes', dueno, datos, 'ficha por prueba')


# ─── Ficha médica ────────────────────────────────────────────────────────────
#  Los básicos son los que hacen falta a pie de campo el día del partido; los
#  avanzados, los del reconocimiento médico (ver sql/schema_v4_ficha_medica.sql).
#  Se separan porque el formulario esconde los segundos: a un entrenador de
#  formación no se le puede pedir el cribado cardiovascular de la FIFA.
CAMPOS_MEDICOS_BASICOS = ('grupo_sanguineo', 'alergias', 'medicacion', 'condiciones',
                          'contacto_nombre', 'contacto_tel', 'contacto_parentesco',
                          'seguro')

CAMPOS_MEDICOS_AVANZADOS = ('estatura_cm', 'peso_kg', 'apto', 'apto_competir',
                            'ultimo_chequeo', 'certificado_vence', 'cirugias',
                            'notas_medico', 'notas_fisio', 'notas_entrenador')

APTITUDES = (('apto', 'Apto', '#10b981'),
             ('precaucion', 'Apto con precaución', '#f59e0b'),
             ('no_apto', 'No apto', '#ef4444'))
APTITUD_META = {c: {'etiqueta': e, 'color': col} for c, e, col in APTITUDES}

#  Quién escribió la parte declarativa de la ficha (alergias, medicación,
#  condiciones). Un jugador con cuenta la escribe él: el cuerpo técnico la lee
#  pero no la pisa. Uno sin cuenta no puede, así que la firma el entrenador.
AUTOR_JUGADOR = 'jugador'
AUTOR_CUERPO_TECNICO = 'cuerpo_tecnico'

#  La fatiga se pregunta en tres niveles y no en una escala de diez. Un «7 de
#  10» no le dice nada a nadie, y el selector 1-10 que se usa para los
#  atributos etiqueta el 10 como «Élite»: para fatiga eso es al revés de lo que
#  significa. Se sigue guardando como número para no migrar la columna ni su
#  rango (1-10), pero se pregunta y se muestra en bajo/medio/alto.
NIVELES_FATIGA = (('bajo', 'Bajo', 3), ('medio', 'Medio', 6), ('alto', 'Alto', 9))
FATIGA_A_NUMERO = {clave: n for clave, _e, n in NIVELES_FATIGA}


def nivel_de_fatiga(valor):
    """El número guardado (1-10) traducido a bajo | medio | alto."""
    if valor in (None, ''):
        return None
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        return None
    if valor <= 4:
        return 'bajo'
    return 'medio' if valor <= 7 else 'alto'


def ficha_medica(player_id=None, manual_player_id=None):
    """La ficha médica de un jugador, con o sin cuenta. {} si no tiene."""
    dueno = dueno_filtro(player_id, manual_player_id)
    if not dueno:
        return {}
    return one('fut_medical', 'ficha medica', **dueno) or {}


def guardar_ficha_medica(player_id=None, manual_player_id=None,
                         actualizado_por=None, solo_basicos=False,
                         solo_clinicos=False, autor=None, **campos):
    """Upsert de la ficha médica.

    Dos fronteras, según quién escriba:

    · `solo_basicos` — lo usa el jugador con su propia ficha. Escribe lo suyo
      (alergias, medicación, condiciones, contacto), pero el veredicto de
      aptitud y el cribado médico los firma el cuerpo técnico, no el interesado.

    · `solo_clinicos` — lo usa el cuerpo técnico sobre un jugador CON cuenta.
      Puede leer la ficha entera y escribir la parte clínica, pero no pisa lo
      que declaró el jugador: ese dato es suyo y él lo mantiene.

    Sin ninguna de las dos (jugador sin cuenta) el entrenador escribe todo,
    porque no hay nadie más que pueda hacerlo.
    """
    dueno = dueno_filtro(player_id, manual_player_id)
    if not dueno:
        return None

    if solo_basicos:
        permitidos = set(CAMPOS_MEDICOS_BASICOS)
    elif solo_clinicos:
        permitidos = set(CAMPOS_MEDICOS_AVANZADOS)
    else:
        permitidos = set(CAMPOS_MEDICOS_BASICOS) | set(CAMPOS_MEDICOS_AVANZADOS)

    datos = {k: v for k, v in campos.items() if k in permitidos}
    if not datos:
        return None
    datos['actualizado'] = _ahora()
    if actualizado_por:
        datos['actualizado_por'] = actualizado_por
    if autor:
        datos['autor_declaracion'] = autor
    return _upsert_dueno('fut_medical', dueno, datos, 'guardar ficha medica')


def _lunes_de_esta_semana():
    hoy = date.today()
    return (hoy - timedelta(days=hoy.weekday())).isoformat()


def recalcular_evolucion_equipo(coach_id):
    """Botón «⟳ Recalcular evolución del equipo»: guarda la foto de esta
    semana de cada jugador (con o sin cuenta) y actualiza sus alertas.

    Devuelve cuántos jugadores tenían perfil y se pudieron recalcular.
    """
    uid = equipo_id(coach_id)
    semana = _lunes_de_esta_semana()
    tocados = 0
    for j in jugadores_del_entrenador(uid):
        tocados += _recalcular_uno(uid, semana, player_id=j['id'])
    for m in rows('fut_manual_players', 'manuales recalc', coach_id=uid, activo=True):
        tocados += _recalcular_uno(uid, semana, manual_player_id=m['id'])
    return tocados


def _recalcular_uno(coach_id, semana, player_id=None, manual_player_id=None):
    fila = fila_atributos(player_id, manual_player_id)
    if not fila or fila.get('overall') is None:
        return 0  # sin perfil todavía: nada que fotografiar

    dueno = dueno_filtro(player_id, manual_player_id)
    overall = fila['overall']

    historial = rows('fut_attribute_history', 'historial', _order='semana', _desc=True, **dueno)
    previa = next((h for h in historial if h.get('semana') != semana), None)
    delta = (overall - previa['overall']) if previa and previa.get('overall') is not None else 0

    snapshot = {k: fila.get(k) for k in ATRIBUTOS_18}
    _upsert_dueno('fut_attribute_history', {**dueno, 'semana': semana},
                  {'atributos': snapshot, 'overall': overall, 'origen': 'manual'},
                  'snapshot semana')

    _actualizar_alertas(coach_id, dueno, delta, fila)
    return 1


#  Las alertas que se recalculan cada semana. Las de otro tipo (si algún día
#  las hay) no se tocan: se resuelven solo estas antes de volver a crearlas.
_TIPOS_RECALCULADOS = ('caida', 'fisico', 'mental')


def _actualizar_alertas(coach_id, dueno, delta, fila):
    """Resuelve las alertas de la semana pasada y crea las que sigan aplicando.

    Mismas reglas, en el mismo orden, que TeamPlayersScreen.tsx:buildAlerts().
    """
    activas = rows('fut_player_alerts', 'alertas previas', activa=True, **dueno)
    for a in activas:
        if a.get('tipo') in _TIPOS_RECALCULADOS:
            update('fut_player_alerts', {'activa': False, 'resuelto': _ahora()},
                   'resolver alerta', id=a['id'])

    nuevas = []
    # Retroceso semanal
    if delta <= -2:
        nuevas.append(('caida', 'grave', f'Retroceso de {abs(delta)} pts esta semana'))
    elif delta == -1:
        nuevas.append(('caida', 'aviso', 'Leve retroceso esta semana'))
    # Condición física baja
    fisico = _media_familia(fila, ATRIBUTOS_FISICOS)
    if fisico is not None and fisico < 45:
        nuevas.append(('fisico', 'aviso', 'Condición física baja'))
    # Estado mental
    mental = _media_familia(fila, ATRIBUTOS_MENTALES)
    if mental is not None:
        if mental < 40:
            nuevas.append(('mental', 'grave', 'Estado mental crítico'))
        elif mental < 55:
            nuevas.append(('mental', 'aviso', 'Motivación reducida'))

    for tipo, severidad, mensaje in nuevas:
        insert('fut_player_alerts', {
            **dueno, 'coach_id': coach_id, 'tipo': tipo, 'severidad': severidad,
            'mensaje': mensaje, 'activa': True,
        }, 'crear alerta')


# ─── Utilidades de fecha ─────────────────────────────────────────────────────
def hoy_iso():
    return date.today().isoformat()


def edad_de(fecha_nacimiento=None, anio_nacimiento=None, hoy=None):
    """La edad de un jugador, exacta si se sabe el dia.

    Con la fecha completa se descuenta el cumpleaños que aun no ha llegado, que
    es la diferencia entre tener 15 y tener 16. No es cosmetico: la edad decide
    la categoria contra la que se comparan sus pruebas
    (`tests_catalogo.categoria_por_edad`), asi que equivocarse un año le cambia
    el baremo entero.

    Sin fecha se cae al año a secas, que es lo unico que se guardaba antes: da
    la edad que cumple ESTE año, no la que tiene hoy.
    """
    hoy = hoy or date.today()
    f = parse_fecha(fecha_nacimiento)
    if f:
        #  Resta un año si todavia no ha sido su cumpleaños.
        return max(0, hoy.year - f.year - ((hoy.month, hoy.day) < (f.month, f.day)))
    if anio_nacimiento:
        try:
            return max(0, hoy.year - int(anio_nacimiento))
        except (TypeError, ValueError):
            return None
    return None


def anio_de(fecha_nacimiento=None, anio_nacimiento=None):
    """El año de nacimiento, saliendo de la fecha si la hay.

    Se sigue guardando aparte porque media app lo lee —solicitudes, la ficha
    del jugador, el registro— y porque de los jugadores antiguos es lo unico
    que se sabe.
    """
    f = parse_fecha(fecha_nacimiento)
    if f:
        return f.year
    try:
        return int(anio_nacimiento) if anio_nacimiento else None
    except (TypeError, ValueError):
        return None


def parse_fecha(s, por_defecto=None):
    """Acepta 'YYYY-MM-DD' o ISO completo; devuelve date o `por_defecto`."""
    if not s:
        return por_defecto
    try:
        return datetime.fromisoformat(str(s)[:19]).date()
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], '%Y-%m-%d').date()
        except Exception:
            return por_defecto
