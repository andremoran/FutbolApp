-- ============================================================================
--  FutbolApp (ProFoot Assistant) — esquema completo
-- ============================================================================
--  Base de datos PROPIA del proyecto. No comparte nada con ninguna otra app.
--
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.
--    Es idempotente: se puede correr varias veces sin romper nada.
--
--  Roles (los nombres vienen de la app y se conservan en toda la base):
--    'especialista' = entrenador      'paciente' = jugador
-- ============================================================================

-- ─── 1. USUARIOS ────────────────────────────────────────────────────────────
create table if not exists usuarios (
  id                  uuid primary key default gen_random_uuid(),
  nombre              text not null,
  correo              text not null unique,
  password            text not null,             -- scrypt, nunca en claro
  rol                 text not null default 'paciente',   -- especialista | paciente
  telefono            text,
  foto                text,
  genero              text,
  anio_nacimiento     int,
  estatura            numeric,
  peso                numeric,

  -- Solo entrenadores
  codigo_equipo       text unique,               -- con esto se unen los jugadores
  club                text,

  -- Suscripción
  activo              boolean default false,
  plan                text default 'basico',
  suscripcion_id      text,
  suscripcion_estado  text,
  suscripcion_desde   timestamptz,

  creado              timestamptz default now()
);
create index if not exists usuarios_correo_idx on usuarios(lower(correo));
create index if not exists usuarios_codigo_idx on usuarios(codigo_equipo);
create index if not exists usuarios_sub_idx    on usuarios(suscripcion_id);

-- ─── 2. PLANTILLA (entrenador ↔ jugador) ────────────────────────────────────
create table if not exists fut_plantilla (
  id         uuid primary key default gen_random_uuid(),
  coach_id   uuid not null references usuarios(id) on delete cascade,
  player_id  uuid not null references usuarios(id) on delete cascade,
  activo     boolean default true,
  dorsal     int,
  creado     timestamptz default now()
);
-- Un jugador pertenece a un equipo a la vez
create unique index if not exists fut_plantilla_player_uidx on fut_plantilla(player_id);
create index if not exists fut_plantilla_coach_idx on fut_plantilla(coach_id, activo);

-- ─── 3. EQUIPO ──────────────────────────────────────────────────────────────
create table if not exists fut_teams (
  id          uuid primary key default gen_random_uuid(),
  coach_id    uuid not null references usuarios(id) on delete cascade,
  nombre      text not null default 'Mi equipo',
  categoria   text default '',
  codigo      text,
  escudo_url  text,
  creado      timestamptz default now()
);
create unique index if not exists fut_teams_coach_uidx on fut_teams(coach_id);

-- ─── 4. FICHA FUTBOLÍSTICA ──────────────────────────────────────────────────
create table if not exists fut_player_profile (
  user_id     uuid primary key references usuarios(id) on delete cascade,
  posicion    text default '',
  dorsal      int,
  pie_habil   text default '',
  notas       text default '',
  actualizado timestamptz default now()
);

-- ─── 5-6. HÁBITOS ───────────────────────────────────────────────────────────
create table if not exists fut_habits (
  id        uuid primary key default gen_random_uuid(),
  player_id uuid not null references usuarios(id) on delete cascade,
  nombre    text not null,
  icono     text default 'check',
  activo    boolean default true,
  creado    timestamptz default now()
);
create index if not exists fut_habits_player_idx on fut_habits(player_id, activo);

create table if not exists fut_habit_completions (
  id        uuid primary key default gen_random_uuid(),
  habit_id  uuid not null references fut_habits(id) on delete cascade,
  player_id uuid not null references usuarios(id) on delete cascade,
  fecha     date not null default current_date,
  hecho     boolean default true
);
create unique index if not exists fut_habit_comp_uidx on fut_habit_completions(habit_id, fecha);
create index if not exists fut_habit_comp_player_idx  on fut_habit_completions(player_id, fecha);

-- ─── 7. METAS ───────────────────────────────────────────────────────────────
create table if not exists fut_goals (
  id            uuid primary key default gen_random_uuid(),
  player_id     uuid not null references usuarios(id) on delete cascade,
  titulo        text not null,
  descripcion   text default '',
  categoria     text default 'general',
  objetivo_num  numeric,
  progreso      int default 0,
  fecha_limite  date,
  estado        text default 'activa',
  creado_por    uuid references usuarios(id) on delete set null,
  creado        timestamptz default now()
);
create index if not exists fut_goals_player_idx on fut_goals(player_id, estado);

-- ─── 8. ENTRENAMIENTOS DEL JUGADOR ──────────────────────────────────────────
create table if not exists fut_trainings (
  id           uuid primary key default gen_random_uuid(),
  player_id    uuid not null references usuarios(id) on delete cascade,
  fecha        date not null default current_date,
  tipo         text default 'general',
  duracion_min int default 0,
  intensidad   text default 'media',
  rpe          int,
  notas        text default '',
  creado       timestamptz default now()
);
create index if not exists fut_trainings_player_idx on fut_trainings(player_id, fecha desc);

-- ─── 9-10. PARTIDOS ─────────────────────────────────────────────────────────
create table if not exists fut_matches (
  id           uuid primary key default gen_random_uuid(),
  coach_id     uuid not null references usuarios(id) on delete cascade,
  rival        text not null default 'Rival',
  fecha        date not null default current_date,
  local        boolean default true,
  goles_favor  int default 0,
  goles_contra int default 0,
  competicion  text default '',
  creado       timestamptz default now()
);
create index if not exists fut_matches_coach_idx on fut_matches(coach_id, fecha desc);

create table if not exists fut_match_stats (
  id          uuid primary key default gen_random_uuid(),
  match_id    uuid not null references fut_matches(id) on delete cascade,
  player_id   uuid not null references usuarios(id) on delete cascade,
  minutos     int default 0,
  goles       int default 0,
  asistencias int default 0,
  tarjetas_a  int default 0,
  tarjetas_r  int default 0,
  valoracion  int
);
create unique index if not exists fut_match_stats_uidx on fut_match_stats(match_id, player_id);

-- ─── 11-12. AGENDA Y ASISTENCIA ─────────────────────────────────────────────
create table if not exists fut_events (
  id          uuid primary key default gen_random_uuid(),
  coach_id    uuid not null references usuarios(id) on delete cascade,
  tipo        text default 'entreno',
  titulo      text not null,
  fecha       date not null default current_date,
  hora        time,
  lugar       text default '',
  descripcion text default '',
  creado      timestamptz default now()
);
create index if not exists fut_events_coach_idx on fut_events(coach_id, fecha);

create table if not exists fut_attendance (
  id        uuid primary key default gen_random_uuid(),
  event_id  uuid not null references fut_events(id) on delete cascade,
  player_id uuid not null references usuarios(id) on delete cascade,
  estado    text default 'duda',
  motivo    text default '',
  creado    timestamptz default now()
);
create unique index if not exists fut_attendance_uidx on fut_attendance(event_id, player_id);

-- ─── 13-14. ATRIBUTOS Y EVALUACIONES ────────────────────────────────────────
create table if not exists fut_attributes (
  player_id   uuid primary key references usuarios(id) on delete cascade,
  tecnica     int default 50,
  fisico      int default 50,
  tactico     int default 50,
  mental      int default 50,
  actualizado timestamptz default now()
);

create table if not exists fut_evaluations (
  id           uuid primary key default gen_random_uuid(),
  player_id    uuid not null references usuarios(id) on delete cascade,
  coach_id     uuid references usuarios(id) on delete set null,
  fecha        date not null default current_date,
  notas        text default '',
  puntuaciones jsonb default '{}'::jsonb,
  informe_ia   text default '',
  creado       timestamptz default now()
);
create index if not exists fut_evals_player_idx on fut_evaluations(player_id, fecha desc);

-- ─── 15-16. PRUEBAS FÍSICAS ─────────────────────────────────────────────────
create table if not exists fut_tests (
  id       uuid primary key default gen_random_uuid(),
  coach_id uuid not null references usuarios(id) on delete cascade,
  nombre   text not null,
  tipo     text default 'distancia',
  unidad   text default '',
  fecha    date not null default current_date,
  creado   timestamptz default now()
);
create index if not exists fut_tests_coach_idx on fut_tests(coach_id, fecha desc);

create table if not exists fut_test_results (
  id        uuid primary key default gen_random_uuid(),
  test_id   uuid not null references fut_tests(id) on delete cascade,
  player_id uuid not null references usuarios(id) on delete cascade,
  valor     numeric,
  nivel     text default '',
  creado    timestamptz default now()
);
create unique index if not exists fut_test_results_uidx   on fut_test_results(test_id, player_id);
create index        if not exists fut_test_results_pl_idx on fut_test_results(player_id);

-- ─── 17. PIZARRA TÁCTICA ────────────────────────────────────────────────────
create table if not exists fut_tactical_plays (
  id        uuid primary key default gen_random_uuid(),
  coach_id  uuid not null references usuarios(id) on delete cascade,
  nombre    text not null default 'Jugada',
  formacion text default '',
  datos     jsonb default '{}'::jsonb,
  carpeta   text default '',
  creado    timestamptz default now()
);
create index if not exists fut_plays_coach_idx on fut_tactical_plays(coach_id, creado desc);

-- ─── 18. MENSAJES ───────────────────────────────────────────────────────────
create table if not exists fut_messages (
  id        uuid primary key default gen_random_uuid(),
  coach_id  uuid not null references usuarios(id) on delete cascade,
  player_id uuid references usuarios(id) on delete cascade,   -- NULL = a todo el equipo
  texto     text not null,
  leido     boolean default false,
  creado    timestamptz default now()
);
create index if not exists fut_messages_coach_idx  on fut_messages(coach_id, creado desc);
create index if not exists fut_messages_player_idx on fut_messages(player_id, leido);

-- ─── 19-20. SALUD MENTAL ────────────────────────────────────────────────────
-- `respuestas` es CONFIDENCIAL: el entrenador solo consulta semaforo/puntaje.
-- La app nunca selecciona esta columna en las vistas del coach.
create table if not exists fut_checkins (
  id         uuid primary key default gen_random_uuid(),
  player_id  uuid not null references usuarios(id) on delete cascade,
  fecha      date not null default current_date,
  respuestas jsonb default '{}'::jsonb,
  puntaje    int,
  semaforo   text default 'verde',
  creado     timestamptz default now()
);
create index if not exists fut_checkins_player_idx on fut_checkins(player_id, fecha desc);

create table if not exists fut_mental_asignaciones (
  id           uuid primary key default gen_random_uuid(),
  coach_id     uuid not null references usuarios(id) on delete cascade,
  player_id    uuid not null references usuarios(id) on delete cascade,
  mensaje      text default '',
  fecha_limite date,
  estado       text default 'pendiente',       -- pendiente | respondido
  respondido   timestamptz,
  creado       timestamptz default now()
);
create index if not exists fut_mental_asig_idx on fut_mental_asignaciones(player_id, estado);

-- ─── 21. OBSERVACIONES DE ENTRENAMIENTO ─────────────────────────────────────
create table if not exists fut_observaciones (
  id        uuid primary key default gen_random_uuid(),
  coach_id  uuid not null references usuarios(id) on delete cascade,
  player_id uuid references usuarios(id) on delete cascade,   -- NULL = del grupo
  fecha     date not null default current_date,
  titulo    text default 'Sesión',
  texto     text not null,
  creado    timestamptz default now()
);
create index if not exists fut_obs_coach_idx on fut_observaciones(coach_id, fecha desc);

-- ─── 22. CONVERSACIONES CON LA IA ───────────────────────────────────────────
create table if not exists fut_ia_chat (
  id        uuid primary key default gen_random_uuid(),
  user_id   uuid not null references usuarios(id) on delete cascade,
  rol       text default 'paciente',
  pregunta  text not null,
  respuesta text default '',
  creado    timestamptz default now()
);
create index if not exists fut_ia_chat_user_idx on fut_ia_chat(user_id, creado);

-- ─── 23. PAGOS ──────────────────────────────────────────────────────────────
create table if not exists fut_pagos (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references usuarios(id) on delete cascade,
  plan           text,
  suscripcion_id text,
  estado         text,
  proveedor      text default 'paypal',
  bruto          text,                          -- respuesta cruda, para auditar
  creado         timestamptz default now()
);
create index if not exists fut_pagos_user_idx on fut_pagos(user_id, creado desc);


-- ============================================================================
--  SEGURIDAD A NIVEL DE FILA
-- ============================================================================
--  La app entra siempre desde el servidor con la clave de servicio, que salta
--  RLS por diseño, y comprueba permisos en cada endpoint (un entrenador solo
--  escribe sobre jugadores de SU plantilla).
--
--  Activamos RLS SIN políticas públicas: así, si alguien consigue la clave
--  anónima, no puede leer ni escribir absolutamente nada desde el navegador.
-- ============================================================================
do $$
declare t text;
begin
  foreach t in array array[
    'usuarios','fut_plantilla','fut_teams','fut_player_profile','fut_habits',
    'fut_habit_completions','fut_goals','fut_trainings','fut_matches',
    'fut_match_stats','fut_events','fut_attendance','fut_attributes',
    'fut_evaluations','fut_tests','fut_test_results','fut_tactical_plays',
    'fut_messages','fut_checkins','fut_mental_asignaciones','fut_observaciones',
    'fut_ia_chat','fut_pagos'
  ]
  loop
    execute format('alter table %I enable row level security', t);
  end loop;
end $$;

-- ============================================================================
--  Comprobación:
--    select table_name from information_schema.tables
--    where table_schema='public' order by 1;
--  Deben aparecer 23 tablas.
-- ============================================================================
