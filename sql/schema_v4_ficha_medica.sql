-- ============================================================================
--  FutbolApp (ProFoot Assistant) — Ficha médica completa
-- ============================================================================
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.
--    Es idempotente: se puede correr varias veces sin romper nada.
--
--  Qué añade y por qué
--  ───────────────────
--  `fut_medical` guardaba siete datos y solo servía para jugadores CON cuenta
--  (`player_id` era la clave primaria). Eso deja fuera justo a quien más lo
--  necesita: el chico de once años que el entrenador apunta a mano y cuya
--  ficha médica la da el representante, no él.
--
--  La sección 1 lo arregla con el mismo patrón de schema_v3 (una columna
--  `manual_player_id` en paralelo, ninguna de las dos obligatoria) y la 2 suma
--  los campos que piden de verdad los clubes y federaciones:
--
--    · Ficha médica deportiva de club/federación — tipo de sangre, alergias,
--      condiciones previas, medicación, vacunas, contacto de emergencia,
--      seguro médico y certificado médico firmado.
--    · FIFA PCMA (Pre-Competition Medical Assessment) — antecedentes
--      personales y FAMILIARES de cardiopatía o muerte súbita, que es el
--      cribado que de verdad salva vidas en un campo, más talla y peso.
--
--  Todo lo clínico nace NULL: vacío significa «no preguntado», que no es lo
--  mismo que «no tiene». Un cero o un «ninguna» inventados aquí serían una
--  respuesta médica que nadie dio.
-- ============================================================================

-- ─── 1. La ficha médica también para jugadores sin cuenta ────────────────────
--  `player_id` deja de ser clave primaria y pasa a ser una columna más. Se
--  mantiene «como mucho una ficha por jugador» con índices únicos PARCIALES.
--
--  OJO: al desaparecer la restricción PRIMARY KEY, un `upsert` con
--  `on_conflict='player_id'` deja de funcionar (PostgREST no sabe apuntar a un
--  índice parcial). Por eso futbol/salud.py pasa a guardar con
--  db.guardar_ficha_medica(), que lee y luego escribe.
alter table public.fut_medical add column if not exists id uuid default gen_random_uuid();
update public.fut_medical set id = gen_random_uuid() where id is null;
alter table public.fut_medical alter column id set not null;

do $$
begin
  if exists (select 1 from pg_constraint where conname = 'fut_medical_pkey') then
    alter table public.fut_medical drop constraint fut_medical_pkey;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fut_medical_pkey_id') then
    alter table public.fut_medical add constraint fut_medical_pkey_id primary key (id);
  end if;
end $$;

alter table public.fut_medical alter column player_id drop not null;
alter table public.fut_medical add column if not exists manual_player_id uuid;

create unique index if not exists fut_medical_player_uidx
  on public.fut_medical (player_id) where player_id is not null;
create unique index if not exists fut_medical_manual_uidx
  on public.fut_medical (manual_player_id) where manual_player_id is not null;

-- ─── 2. Lo que piden los clubes ──────────────────────────────────────────────
-- 2.1 Básicos — lo que hace falta saber a pie de campo el día del partido.
--     (`grupo_sanguineo`, `alergias`, `medicacion`, `condiciones`,
--      `contacto_nombre`, `contacto_tel` y `seguro` ya existían.)
alter table public.fut_medical add column if not exists contacto_parentesco text;

-- 2.2 Avanzados — los que solo rellena un club con cuerpo médico. Opcionales.
alter table public.fut_medical add column if not exists estatura_cm  numeric;
alter table public.fut_medical add column if not exists peso_kg      numeric;

--  Aptitud deportiva: el veredicto del reconocimiento médico.
alter table public.fut_medical add column if not exists apto              text;  -- apto|precaucion|no_apto
alter table public.fut_medical add column if not exists ultimo_chequeo    date;
alter table public.fut_medical add column if not exists certificado_vence date;
alter table public.fut_medical add column if not exists vacunas           text;

--  Cribado cardiovascular del PCMA de la FIFA. El familiar importa tanto como
--  el personal: una muerte súbita antes de los 50 en la familia es la señal de
--  alarma que obliga a mirar el corazón del jugador antes de dejarlo competir.
alter table public.fut_medical add column if not exists antecedentes_personales text;
alter table public.fut_medical add column if not exists antecedentes_familiares text;
alter table public.fut_medical add column if not exists cirugias                text;
alter table public.fut_medical add column if not exists observaciones           text;

--  Quién tocó la ficha por última vez: en una ficha médica hace falta saberlo.
alter table public.fut_medical add column if not exists actualizado_por uuid
  references public.usuarios(id) on delete set null;

-- Que nadie invente un veredicto que no existe.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fut_medical_apto_valido') then
    alter table public.fut_medical add constraint fut_medical_apto_valido check (
      apto is null or apto in ('apto', 'precaucion', 'no_apto')
    );
  end if;
end $$;

-- ─── 3. Lesiones: estado crónico y tratamiento ───────────────────────────────
--  `fut_injuries` solo admitía activa|recuperando|alta. Una condición crónica
--  (una rodilla que arrastra desde hace años) no es ninguna de las tres, y sin
--  el tratamiento anotado el parte de lesión no le sirve al fisio.
alter table public.fut_injuries add column if not exists tratamiento text;
alter table public.fut_injuries add column if not exists dias_estimados int;

-- ─── 4. Seguridad ────────────────────────────────────────────────────────────
--  RLS ya estaba activado en fut_medical por el esquema base; se deja dicho
--  aquí para que no se pierda al leer solo este archivo.
alter table public.fut_medical enable row level security;
