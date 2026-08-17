-- ============================================================================
--  FutbolApp (ProFoot Assistant) — Crear entrenamiento
-- ============================================================================
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.   Es idempotente.
--
--  Qué añade y por qué
--  ───────────────────
--  `fut_training_plans` guardaba nombre, objetivo, tipo e intensidad. La
--  pantalla «Crear Entrenamiento» de la app (CreateTrainingPlanScreen.tsx)
--  pide tres cosas más que no tenían dónde guardarse:
--
--    · `subtipo` — dentro de Físico no es lo mismo «Pesas y Fuerza» que
--      «Flexibilidad y Movilidad». Son ocho por familia y es lo que de verdad
--      describe la sesión.
--    · `descripcion` — hasta ahora solo existía `objetivo`, y en la app son
--      dos campos distintos: qué se va a hacer y qué se quiere conseguir.
--    · `carga_fisica` — el 0-100 del deslizador. No se deduce de la
--      intensidad: dos sesiones «media» pueden cargar muy distinto según su
--      duración y su contenido.
-- ============================================================================

alter table public.fut_training_plans add column if not exists subtipo      text;
alter table public.fut_training_plans add column if not exists descripcion  text;
alter table public.fut_training_plans add column if not exists carga_fisica smallint;

-- El deslizador va de 0 a 100: que nadie guarde un 150.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fut_plans_carga_valida') then
    alter table public.fut_training_plans add constraint fut_plans_carga_valida check (
      carga_fisica is null or carga_fisica between 0 and 100
    );
  end if;
end $$;

comment on column public.fut_training_plans.subtipo is
  'Uno de los ocho de su familia — ver futbol/calendario.py › SUBTIPOS';
