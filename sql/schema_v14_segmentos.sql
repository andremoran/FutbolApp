-- ============================================================================
--  FutbolApp (ProFoot Assistant) — Segmentos (a quién entrena cada entrenador)
-- ============================================================================
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.   Es idempotente.
--
--  Qué añade y por qué
--  ───────────────────
--  Hasta aquí la app daba por hecho una sola realidad: un club profesional con
--  cuerpo técnico completo, sesión diaria y partido cada fin de semana. Toda la
--  periodización (futbol/microciclos.py) está escrita sobre esa realidad, y con
--  razón — es de donde sale la evidencia.
--
--  Pero la mayor parte de quien va a usar esto NO vive ahí. Un equipo de
--  Segunda Categoría entrena tres tardes porque sus jugadores trabajan; un
--  colegio entrena dos veces entre clases y su objetivo no es ganar el domingo,
--  es que el chico siga jugando a los veinte. Darles la planilla del club
--  profesional no es «darles más»: es darles algo que no pueden cumplir, y una
--  guía que no se puede cumplir se ignora entera.
--
--  De ahí el `segmento`. No es una etiqueta decorativa: decide qué
--  periodización se le ofrece al entrenador, con qué vocabulario, contra qué
--  evidencia se le avisa y qué objetivos se le proponen.
--
--      profesional   Club profesional o de élite.  ← TODO lo que había hasta hoy
--      semipro       Segunda categoría, ascenso, liga provincial, universitario.
--      colegio       Colegios y escuelas de formación. Intercolegial.
--
--  Vive en el EQUIPO y no en el jugador a propósito. El jugador no elige nada:
--  entra con el código de su entrenador y hereda el segmento de ese equipo. Si
--  estuviera en cada persona habría que mantenerlo sincronizado en toda la
--  plantilla cada vez que un club cambia de categoría, y bastaría una fila mal
--  puesta para que a un chico se le midiera con el baremo equivocado.
--
--  El valor por defecto es `profesional` A PROPÓSITO: todos los equipos que ya
--  existen se crearon con la app profesional y tienen que seguir viéndola
--  exactamente igual. Nadie se despierta con la plataforma cambiada.
-- ============================================================================

alter table public.fut_teams
  add column if not exists segmento text not null default 'profesional';

-- Los tres, y nada más. Si un día entra un cuarto se añade aquí y en
-- futbol/segmentos.py › SEGMENTOS; que la base lo vigile evita que un typo en
-- un formulario deje equipos en un segmento que no existe y que la app
-- resolvería en silencio al de por defecto.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fut_teams_segmento_valido') then
    alter table public.fut_teams add constraint fut_teams_segmento_valido check (
      segmento in ('profesional', 'semipro', 'colegio')
    );
  end if;
end $$;

-- El listado del panel de administración agrupa por segmento para ver cómo se
-- reparte la base de entrenadores. Sin índice es un scan de la tabla entera.
create index if not exists fut_teams_segmento_idx
  on public.fut_teams (segmento);

comment on column public.fut_teams.segmento is
  'A quién entrena este equipo: profesional | semipro | colegio. Decide la '
  'periodización, el vocabulario y los objetivos. Ver futbol/segmentos.py.';

-- ─── El microciclo recuerda con qué modelo se escribió ──────────────────────
--  Un entrenador puede cambiar de segmento (un colegio que federa su equipo,
--  un semipro que asciende). Sus microciclos viejos se escribieron contra otra
--  periodización: si al abrirlos se leyeran con el modelo nuevo, los días
--  aparecerían sin guía y los avisos dirían cosas que no tocan.
--
--  Guardar el segmento EN el microciclo lo deja congelado con el modelo con el
--  que se planificó, que es lo honesto: esa semana se pensó así.
alter table public.fut_microcycles
  add column if not exists segmento text not null default 'profesional';

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fut_micro_segmento_valido') then
    alter table public.fut_microcycles add constraint fut_micro_segmento_valido check (
      segmento in ('profesional', 'semipro', 'colegio')
    );
  end if;
end $$;

comment on column public.fut_microcycles.segmento is
  'Modelo de periodización con el que se escribió esta semana. No cambia '
  'aunque el equipo cambie de segmento después.';
