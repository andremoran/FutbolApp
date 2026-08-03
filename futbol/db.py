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
from datetime import date, datetime, timedelta

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


def insert(table, data, ctx=''):
    def _go():
        return (_sb.table(table).insert(data).execute().data or [None])[0]
    return q(_go, None, ctx or ('insert ' + table))


def update(table, data, ctx='', **filters):
    def _go():
        upd = _sb.table(table).update(data)
        for k, v in filters.items():
            upd = upd.eq(k, v)
        return upd.execute().data
    return q(_go, None, ctx or ('update ' + table))


def upsert(table, data, ctx='', on_conflict=None):
    def _go():
        t = _sb.table(table)
        res = t.upsert(data, on_conflict=on_conflict) if on_conflict else t.upsert(data)
        return (res.execute().data or [None])[0]
    return q(_go, None, ctx or ('upsert ' + table))


def delete(table, ctx='', **filters):
    def _go():
        d = _sb.table(table).delete()
        for k, v in filters.items():
            d = d.eq(k, v)
        return d.execute().data
    return q(_go, None, ctx or ('delete ' + table))


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


def entrenador_del_jugador(player_id):
    """Entrenador vinculado al jugador (o None si aún no se unió a un equipo)."""
    v = one('fut_plantilla', 'mi coach', player_id=player_id, activo=True)
    if not v:
        return None
    return _normalizar_usuario(one('usuarios', 'coach del jugador', id=v['coach_id']))


def perfil_jugador(player_id):
    """Ficha futbolística: posición, dorsal, pie hábil…"""
    return one('fut_player_profile', 'perfil jugador', user_id=player_id) or {}


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


# ─── Utilidades de fecha ─────────────────────────────────────────────────────
def hoy_iso():
    return date.today().isoformat()


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
