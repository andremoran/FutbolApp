-- ============================================================================
--  FutbolApp (ProFoot Assistant) — Microciclos (planificación semanal)
-- ============================================================================
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.   Es idempotente.
--
--  Qué añade y por qué
--  ───────────────────
--  `fut_training_plans` guarda UNA sesión. Lo que el cuerpo técnico maneja de
--  verdad es la SEMANA entera: la planilla que se imprime y se cuelga en el
--  vestuario, con los días en columnas y las capacidades en filas.
--
--  La forma de la tabla sale de una planilla real (Cantera Orense, «MICRO 7»):
--  cada día lleva lugar, hora, capacidad física del día y el contenido partido
--  en tres bloques — parte inicial, parte principal (físico / técnico /
--  táctico / estratégico / psicológico) y parte final. Debajo, las
--  recomendaciones, las observaciones y la firma del cuerpo técnico.
--
--  Encima de esa planilla se monta la capa de periodización: cada día sabe qué
--  posición ocupa respecto al partido (MD-4, MD-2, MD+1…) y qué carga lleva.
--  De ahí salen la gráfica de carga de la semana y los avisos de la guía.
--
--  `dias` es jsonb y no una tabla aparte a propósito: un microciclo se lee y
--  se guarda SIEMPRE entero, nunca un día suelto. Es el mismo criterio que ya
--  usa fut_training_plans.bloques.
--
--  Forma de cada elemento de `dias`:
--    {
--      "fecha": "2026-05-11", "etiqueta": "LUNES 11",
--      "md": "MD+1",                       -- posición respecto al partido
--      "carga": "baja",                    -- partido|alta|media|baja|descanso
--      "lugar": "CANCHA #1", "hora": "08:30", "duracion": 90,
--      "capacidad": "REGENERATIVO PREVENTIVO",
--      "inicial": "…", "fisico": "…", "tecnico": "…", "tactico": "…",
--      "estrategico": "…", "psicologico": "…", "final": "…"
--    }
-- ============================================================================

create table if not exists public.fut_microcycles (
  id               uuid primary key default gen_random_uuid(),
  coach_id         uuid not null references public.usuarios(id) on delete cascade,

  nombre           text not null,
  lugar            text,                       -- complejo / sede de la semana
  desde            date,
  hasta            date,

  -- Días entre partido y partido. Manda sobre la plantilla que sugiere la guía:
  -- una rotación de 4 días no admite sesión de alta intensidad y el planificador
  -- lo avisa. Ver futbol/microciclos.py › ROTACIONES.
  rotacion         smallint default 7,

  dias             jsonb not null default '[]'::jsonb,

  recomendaciones  text,
  observaciones    text,
  cuerpo_tecnico   text,                       -- la línea de firmas del pie

  creado           timestamptz default now(),
  actualizado      timestamptz
);

-- Un entrenador abre su lista de microciclos ordenada por fecha: sin este
-- índice es un scan de la tabla entera en cada carga de la pantalla.
create index if not exists fut_microcycles_coach_idx
  on public.fut_microcycles (coach_id, desde desc);

-- Rotaciones de 3 a 8 días: es el rango que cubre la evidencia (Buchheit 2023a)
-- y fuera de él la guía no tiene nada que decir.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fut_micro_rotacion_valida') then
    alter table public.fut_microcycles add constraint fut_micro_rotacion_valida check (
      rotacion is null or rotacion between 3 and 8
    );
  end if;
end $$;

-- ─── Seguridad ──────────────────────────────────────────────────────────────
--  Mismo candado que las otras 38 tablas fut_*: RLS activado y NINGUNA política.
--  Con eso la tabla queda cerrada a la clave pública (`anon`) y solo la
--  atraviesa `service_role`, que es con la que habla el servidor Flask.
--
--  No es un descuido que no haya políticas: en esta app quien decide qué puede
--  ver cada entrenador es Flask (flask_login + db.equipo_id), no Postgres. El
--  navegador nunca habla directamente con Supabase, así que una política por
--  usuario no tendría a quién mirar — no hay sesión de Supabase Auth.
alter table public.fut_microcycles enable row level security;

comment on table  public.fut_microcycles is
  'Planificación semanal del equipo. Un microciclo = una semana entre partidos.';
comment on column public.fut_microcycles.dias is
  'Array de días. Forma en la cabecera de este archivo y en futbol/microciclos.py';
comment on column public.fut_microcycles.rotacion is
  'Días entre partidos (3-8). Decide qué plantilla sugiere la guía de periodización.';
