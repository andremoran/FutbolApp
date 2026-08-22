-- v9 · Las observaciones se atan al entrenamiento y guardan la nota de voz
--
-- Dos cosas que faltaban y que se notaban:
--
--  1. calendario.py ya pedia la observacion del evento por event_id, pero la
--     columna no existia. Como db.one() se traga los errores, devolvia None
--     siempre: la pantalla del evento nunca decia «ya hay una observacion» y
--     al entrar desde el entreno parecia que habia que empezar de cero.
--
--  2. La pantalla promete «Observacion con IA» y que la IA resume la sesion.
--     No habia donde guardar ni lo dictado ni el analisis.

alter table fut_observaciones
  add column if not exists event_id uuid
      references fut_events(id) on delete set null,
  add column if not exists transcripcion  text,
  add column if not exists analisis_ia    text,
  add column if not exists audio_segundos integer;

-- Se consulta siempre por evento + entrenador.
create index if not exists idx_obs_evento
  on fut_observaciones(event_id);

comment on column fut_observaciones.event_id is
  'Entreno o partido al que pertenece. Nulo = observacion suelta.';
comment on column fut_observaciones.transcripcion is
  'Lo que el entrenador dicto por voz, tal cual lo transcribio la IA.';
comment on column fut_observaciones.analisis_ia is
  'Lectura de la IA sobre esas notas: que sacar en claro de la sesion.';
