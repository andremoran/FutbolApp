-- v15 · Una jugada se puede asignar a un entrenamiento o a un partido
--
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.   Es idempotente.
--    O bien:   python aplicar_sql.py sql/schema_v15_jugadas_en_eventos.sql
--
--  Qué añade y por qué
--  ───────────────────
--  La pizarra guardaba jugadas, rondos y ruedas de pases, y la agenda guardaba
--  entrenamientos y partidos, pero eran dos cajones sin conexión: el entrenador
--  montaba el rondo del martes y el martes tenía que acordarse de cuál era.
--
--  Ahora una sesión lleva su táctica pegada, y el jugador la ve al abrir el
--  entrenamiento en su agenda — que es donde de verdad la va a mirar.
--
--  Por qué una tabla y no una columna en `fut_events`
--  ──────────────────────────────────────────────────
--  Un entrenamiento lleva VARIAS tareas —dos rondos y una rueda— y la misma
--  jugada se repite en muchas sesiones. Con una columna `jugada_id` habría que
--  elegir una sola, y duplicar la jugada para poder repetirla; con la tabla,
--  cada una se guarda una vez y se cuelga donde haga falta.
--
--  `orden` es el orden dentro de la sesión: un calentamiento no va después del
--  partidillo, y esa secuencia es media planificación.

create table if not exists public.fut_event_plays (
  id        uuid primary key default gen_random_uuid(),
  coach_id  uuid not null references public.usuarios(id) on delete cascade,
  event_id  uuid not null references public.fut_events(id) on delete cascade,
  play_id   uuid not null references public.fut_tactical_plays(id) on delete cascade,

  orden     smallint default 0,
  nota      text,                       -- «15 min, dos toques» — lo del día
  creado    timestamptz default now()
);

-- La misma jugada no se cuelga dos veces del mismo evento. Sin esto, dos
-- toques seguidos en el botón la dejaban repetida en la lista.
create unique index if not exists ux_event_plays
  on public.fut_event_plays (event_id, play_id);

-- Se lee siempre por evento (la ficha del entreno) y a veces por jugada
-- («¿dónde estoy usando esto?»).
create index if not exists idx_event_plays_evento
  on public.fut_event_plays (event_id, orden);
create index if not exists idx_event_plays_jugada
  on public.fut_event_plays (play_id);

-- ─── Seguridad ──────────────────────────────────────────────────────────────
--  Mismo candado que el resto de las tablas fut_*: RLS activado y NINGUNA
--  política, así queda cerrada a la clave pública y solo la atraviesa
--  `service_role`, que es con la que habla Flask. Quién ve qué lo decide la
--  app (flask_login + db.equipo_id), no Postgres: el navegador nunca habla
--  directamente con Supabase.
alter table public.fut_event_plays enable row level security;

comment on table public.fut_event_plays is
  'Qué jugadas, rondos o ruedas se trabajan en cada entrenamiento o partido.';
comment on column public.fut_event_plays.orden is
  'Orden dentro de la sesión. El calentamiento no va después del partidillo.';
comment on column public.fut_event_plays.nota is
  'Lo que cambia ESE día: duración, número de toques, variante.';
