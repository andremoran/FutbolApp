-- v11 · Lo que avisa el jugador NO es la asistencia
--
-- El boton «Voy / No voy» de la agenda escribia en `estado`: la misma casilla
-- que usa el entrenador para pasar lista. O sea que el jugador se apuntaba a
-- si mismo como presente y eso contaba en su porcentaje de asistencia, en el
-- contexto de la IA y en todo lo demas.
--
-- Son dos cosas distintas y ahora viven en columnas distintas:
--
--   · `aviso`         lo que el jugador dice ANTES. Es una intencion.
--   · `aviso_motivo`  por que va a llegar tarde o por que no puede ir.
--   · `estado`        lo que el entrenador marca DESPUES de ver quien vino.
--                     Esto es lo unico que cuenta como asistencia.
--
-- La marca del entrenador manda siempre. El aviso solo sirve para que pueda
-- contar con el jugador y para saber el motivo sin tener que preguntar.

alter table fut_attendance
  add column if not exists aviso        text,
  add column if not exists aviso_motivo text,
  add column if not exists aviso_en     timestamptz;

-- Los tres valores que puede mandar el jugador. Se deja abierto a nulo porque
-- la mayoria de las filas las crea el entrenador al pasar lista y ahi no hay
-- aviso ninguno.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_attendance_aviso') then
    alter table fut_attendance
      add constraint ck_attendance_aviso check (
        aviso is null or aviso in ('ire', 'tarde', 'no_ire')
      );
  end if;
end $$;

comment on column fut_attendance.aviso is
  'Lo que dijo el JUGADOR antes: ire / tarde / no_ire. Es un aviso, no cuenta '
  'como asistencia.';
comment on column fut_attendance.aviso_motivo is
  'Por que llega tarde o por que no puede ir. Lo escribe el jugador.';
comment on column fut_attendance.estado is
  'La asistencia de verdad, la que marca el ENTRENADOR despues del '
  'entrenamiento. Es la unica que cuenta en las estadisticas.';

-- ── v11b ──────────────────────────────────────────────────────────────────
-- `estado` tenia DEFAULT 'duda', un valor heredado que ni siquiera esta entre
-- los estados validos del codigo (presente / ausente / tarde / justificado /
-- pendiente). Mientras las filas las creaba siempre el entrenador con un
-- estado explicito no se notaba; en cuanto el jugador empezo a crear filas
-- solo con su aviso, cada una nacia con «duda» puesta — o sea con una
-- asistencia que nadie habia marcado.
--
-- Sin defecto, una fila sin marcar es NULL, que es justo lo que el codigo
-- entiende como «todavia no se ha pasado lista».
alter table fut_attendance alter column estado drop default;
