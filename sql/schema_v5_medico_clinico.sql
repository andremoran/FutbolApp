-- ============================================================================
--  FutbolApp (ProFoot Assistant) — Ficha médica clínica del cuerpo técnico
-- ============================================================================
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.
--    Es idempotente: se puede correr varias veces sin romper nada.
--
--  Qué añade y por qué
--  ───────────────────
--  schema_v4 dejó la ficha médica que rellena el entrenador al dar de alta a
--  un jugador. Falta la parte que en la app lleva el CUERPO TÉCNICO durante la
--  temporada (screens/PlayerMedicalScreen.tsx):
--
--    · El veredicto de aptitud ya existe (`apto`), pero no el permiso de
--      competir, que es distinto: un jugador puede estar «apto con precaución»
--      y aun así no tener el alta para jugar el domingo.
--    · Tres notas separadas por quién las escribe. En la app son bloques
--      distintos (🏥 médico, ⚕️ fisio, 📋 entrenador) a propósito: mezclarlas
--      en un campo hace que nadie sepa quién dijo qué ni con qué autoridad.
--
--  Lo que NO se duplica
--  ────────────────────
--  La app guarda `current_fatigue` y `overload_risk` dentro de la ficha
--  médica. Aquí ya viven en `fut_attributes` desde schema_v3, porque son parte
--  del Perfil Dinámico y los mueve la evaluación semanal. Tenerlos dos veces
--  garantizaría que un día no coincidan, así que la pantalla médica lee y
--  escribe los de `fut_attributes`.
-- ============================================================================

-- ─── 1. Permiso de competir ──────────────────────────────────────────────────
--  Separado de `apto`: aquel es el diagnóstico, este es la autorización.
alter table public.fut_medical add column if not exists apto_competir boolean;

-- ─── 2. Las tres notas, por autor ────────────────────────────────────────────
--  `observaciones` nació en schema_v4 como cajón de sastre. Pasa a ser la nota
--  del médico, que es para lo que se estaba usando, y se le suman las otras
--  dos. Se renombra en vez de crear una cuarta columna para no dejar dos
--  campos que signifiquen lo mismo.
do $$
begin
  if exists (select 1 from information_schema.columns
             where table_schema = 'public' and table_name = 'fut_medical'
               and column_name = 'observaciones')
     and not exists (select 1 from information_schema.columns
                     where table_schema = 'public' and table_name = 'fut_medical'
                       and column_name = 'notas_medico') then
    alter table public.fut_medical rename column observaciones to notas_medico;
  end if;
end $$;

alter table public.fut_medical add column if not exists notas_medico     text;
alter table public.fut_medical add column if not exists notas_fisio      text;
alter table public.fut_medical add column if not exists notas_entrenador text;

-- ─── 3. Quién puede firmar la ficha ──────────────────────────────────────────
--  `actualizado_por` (schema_v4) dice quién la tocó. Falta saber si lo que
--  hay dentro lo escribió el jugador o el cuerpo técnico: de eso depende que
--  el entrenador pueda sobreescribirlo o solo leerlo.
alter table public.fut_medical add column if not exists autor_declaracion text;  -- jugador|cuerpo_tecnico

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fut_medical_autor_valido') then
    alter table public.fut_medical add constraint fut_medical_autor_valido check (
      autor_declaracion is null or autor_declaracion in ('jugador', 'cuerpo_tecnico')
    );
  end if;
end $$;

-- ─── 4. Lesiones crónicas ────────────────────────────────────────────────────
--  `estado` admitía activa|recuperando|alta. Una rodilla que se arrastra desde
--  hace años no es ninguna de las tres: no está de baja, pero tampoco curada.
--  La columna es `text` y no tiene restricción, así que basta con que la app
--  lo contemple (futbol/salud.py › ESTADOS). Se deja anotado aquí para que al
--  leer solo este archivo se sepa que 'cronico' es un valor válido.
comment on column public.fut_injuries.estado is
  'activa | recuperando | alta | cronico';

comment on column public.fut_injuries.tratamiento is
  'Protocolo indicado: fisioterapia, reposo, medicacion (schema_v4)';
