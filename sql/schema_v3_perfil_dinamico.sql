-- ============================================================================
--  FutbolApp (ProFoot Assistant) — Perfil dinámico del jugador
-- ============================================================================
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.
--    Es idempotente: se puede correr varias veces sin romper nada.
--
--  Qué añade y por qué
--  ───────────────────
--  Hasta ahora `fut_attributes` guardaba cuatro números por jugador: técnica,
--  físico, táctico y mental. La app original trabaja con DIECIOCHO, repartidos
--  en tres familias, y de ahí saca el overall, el potencial y la evolución
--  semanal que se ve en la pantalla de Equipo.
--
--  Los cuatro de antes NO se borran. Siguen siendo la media de su familia y
--  todo el código que los lee sigue funcionando mientras se migra pantalla a
--  pantalla. Rellenarlos a partir de los dieciocho es trabajo de la app, no
--  de este script.
--
--  Las columnas nuevas nacen en NULL a propósito: NULL significa «no evaluado
--  todavía», que no es lo mismo que 50. La app ya trata el hueco como 50 al
--  mostrarlo, pero guardar 50 aquí sería inventarse una evaluación.
--
--  También un jugador SIN CUENTA (fut_manual_players) tiene Perfil Dinámico:
--  la pantalla de Equipo y el alta de «Nuevo Jugador» son justo sobre ellos.
--  `fut_attributes` nació con `player_id` como clave primaria — eso solo
--  admite jugadores con cuenta. La sección 0 lo arregla, con el mismo patrón
--  que ya usan `fut_eval_results` y `fut_attendance` (columna
--  `manual_player_id` en paralelo, sin exigir que `player_id` esté relleno).
-- ============================================================================

-- ─── 0. `fut_attributes` también para jugadores sin cuenta ───────────────────
--  `player_id` deja de ser la clave primaria (un jugador manual no tiene) y
--  pasa a ser una columna más, nullable, con `id` propio como clave. Se
--  mantiene como mucho una ficha por jugador con un índice único parcial en
--  vez de la vieja restricción PRIMARY KEY.
alter table public.fut_attributes add column if not exists id uuid default gen_random_uuid();
update public.fut_attributes set id = gen_random_uuid() where id is null;
alter table public.fut_attributes alter column id set not null;

do $$
begin
  if exists (select 1 from pg_constraint where conname = 'fut_attributes_pkey') then
    alter table public.fut_attributes drop constraint fut_attributes_pkey;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fut_attributes_pkey_id') then
    alter table public.fut_attributes add constraint fut_attributes_pkey_id primary key (id);
  end if;
end $$;

alter table public.fut_attributes alter column player_id drop not null;
alter table public.fut_attributes add column if not exists manual_player_id uuid;  -- jugador sin cuenta

create unique index if not exists fut_attributes_player_uidx
  on public.fut_attributes (player_id) where player_id is not null;
create unique index if not exists fut_attributes_manual_uidx
  on public.fut_attributes (manual_player_id) where manual_player_id is not null;

-- ─── 0b. Estadísticas competitivas de jugadores sin cuenta ───────────────────
--  Para un jugador con cuenta, goles/asistencias salen de fut_match_stats (ver
--  futbol/coach.py:c_jugador). Uno sin cuenta puede no tener partidos cargados
--  todavía, así que el alta permite sembrar sus cifras de la temporada a mano.
alter table public.fut_manual_players add column if not exists goles              int;
alter table public.fut_manual_players add column if not exists asistencias        int;
alter table public.fut_manual_players add column if not exists minutos_jugados    int;
alter table public.fut_manual_players add column if not exists jugadas_clave      int;
alter table public.fut_manual_players add column if not exists valoracion_promedio smallint;

-- ─── 1. Los 18 atributos ─────────────────────────────────────────────────────
-- Técnicos (7)
alter table public.fut_attributes add column if not exists pase           smallint;
alter table public.fut_attributes add column if not exists control        smallint;
alter table public.fut_attributes add column if not exists regate         smallint;
alter table public.fut_attributes add column if not exists tiro           smallint;
alter table public.fut_attributes add column if not exists definicion     smallint;
alter table public.fut_attributes add column if not exists centros        smallint;
alter table public.fut_attributes add column if not exists vision_juego   smallint;

-- Físicos (5)
alter table public.fut_attributes add column if not exists velocidad      smallint;
alter table public.fut_attributes add column if not exists resistencia    smallint;
alter table public.fut_attributes add column if not exists fuerza         smallint;
alter table public.fut_attributes add column if not exists agilidad       smallint;
alter table public.fut_attributes add column if not exists aceleracion    smallint;

-- Mentales (6)
alter table public.fut_attributes add column if not exists liderazgo      smallint;
alter table public.fut_attributes add column if not exists disciplina     smallint;
alter table public.fut_attributes add column if not exists concentracion  smallint;
alter table public.fut_attributes add column if not exists confianza      smallint;
alter table public.fut_attributes add column if not exists trabajo_equipo smallint;
alter table public.fut_attributes add column if not exists mentalidad     smallint;

-- ─── 2. Overall y potencial ──────────────────────────────────────────────────
--  `overall` es la media de los dieciocho: lo que se ve en el círculo naranja
--  de cada tarjeta. `potencial` es el techo estimado del jugador (el POT),
--  que pone el entrenador — no se calcula solo.
alter table public.fut_attributes add column if not exists overall    smallint;
alter table public.fut_attributes add column if not exists potencial  smallint;

-- ─── 3. Estado del jugador ───────────────────────────────────────────────────
--  Lo que la pantalla de Equipo pinta como avisos: fatiga alta, riesgo de
--  sobrecarga y las notas de texto del entrenador.
alter table public.fut_attributes add column if not exists fatiga             smallint;
alter table public.fut_attributes add column if not exists riesgo_sobrecarga  text;
alter table public.fut_attributes add column if not exists fortalezas         text;
alter table public.fut_attributes add column if not exists debilidades        text;
alter table public.fut_attributes add column if not exists evolucion_tecnica  text;
alter table public.fut_attributes add column if not exists lesiones_historial text;
alter table public.fut_attributes add column if not exists posicion_secundaria text;

-- Que nadie guarde un 11 en una escala de 1 a 10, ni un 150 en una de 1 a 100.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fut_attributes_rangos') then
    alter table public.fut_attributes add constraint fut_attributes_rangos check (
      (overall   is null or overall   between 1 and 100) and
      (potencial is null or potencial between 1 and 100) and
      (fatiga    is null or fatiga    between 1 and 10)  and
      (riesgo_sobrecarga is null or riesgo_sobrecarga in ('bajo','medio','alto'))
    );
  end if;
end $$;

-- ─── 4. Histórico semanal ────────────────────────────────────────────────────
--  Sin esto no hay «cambio semanal» ni flechas de subiendo/bajando: harían
--  falta dos fotos del mismo jugador en momentos distintos y solo hay una.
--  Una fila por jugador y semana — con o sin cuenta, igual que fut_attributes.
create table if not exists public.fut_attribute_history (
  id                uuid primary key default gen_random_uuid(),
  player_id         uuid references public.usuarios(id) on delete cascade,
  manual_player_id  uuid,                      -- jugador sin cuenta
  semana            date not null,             -- lunes de la semana medida
  atributos         jsonb not null default '{}', -- foto de los 18 en ese momento
  overall           smallint,
  origen            text default 'manual',     -- 'manual' | 'prueba' | 'ia'
  creado            timestamptz not null default now()
);

create unique index if not exists fut_attribute_history_player_uidx
  on public.fut_attribute_history (player_id, semana) where player_id is not null;
create unique index if not exists fut_attribute_history_manual_uidx
  on public.fut_attribute_history (manual_player_id, semana) where manual_player_id is not null;

create index if not exists fut_attribute_history_jugador
  on public.fut_attribute_history (player_id, semana desc);
create index if not exists fut_attribute_history_manual
  on public.fut_attribute_history (manual_player_id, semana desc);

-- ─── 5. Alertas del jugador ──────────────────────────────────────────────────
--  «Motivación reducida», «2 jugadores con alertas». Se guardan en vez de
--  recalcularse al vuelo para poder decir desde cuándo pasa y no repetir el
--  mismo aviso cada vez que se abre la pantalla.
create table if not exists public.fut_player_alerts (
  id                uuid primary key default gen_random_uuid(),
  player_id         uuid references public.usuarios(id) on delete cascade,
  manual_player_id  uuid,                      -- jugador sin cuenta
  coach_id          uuid not null references public.usuarios(id) on delete cascade,
  tipo              text not null,             -- 'motivacion' | 'fatiga' | 'caida' | ...
  severidad         text not null default 'aviso', -- 'aviso' | 'grave'
  mensaje           text not null,
  activa            boolean not null default true,
  creado            timestamptz not null default now(),
  resuelto          timestamptz
);

create index if not exists fut_player_alerts_activas
  on public.fut_player_alerts (coach_id, activa);
create index if not exists fut_player_alerts_jugador
  on public.fut_player_alerts (player_id, activa);
create index if not exists fut_player_alerts_manual
  on public.fut_player_alerts (manual_player_id, activa);

-- ─── 6. Seguridad ────────────────────────────────────────────────────────────
--  RLS activado sin políticas públicas, igual que el resto del esquema: solo
--  se llega a estas tablas desde el servidor con la clave de servicio.
alter table public.fut_attribute_history enable row level security;
alter table public.fut_player_alerts     enable row level security;
