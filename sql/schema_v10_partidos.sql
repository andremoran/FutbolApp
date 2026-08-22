-- v10 · El partido de la agenda se une con su hoja de estadisticas
--
-- Tres agujeros que dejaban la funcion a medias:
--
--  1. Un partido de la agenda (fut_events, tipo='partido') y un partido con
--     estadisticas (fut_matches) eran dos cosas sin relacion. Desde la ficha
--     del partido en la agenda no se podia apuntar quien marco.
--
--  2. fut_match_stats solo admitia player_id, o sea jugadores CON cuenta. En
--     un equipo de formacion casi nadie la tiene: la pantalla de estadisticas
--     salia vacia y no se podia apuntar nada de nadie. Es el mismo fallo que
--     tenia la asistencia antes de la v8.
--
--  3. No habia donde apuntar las jugadas clave ni quien fue titular.

alter table fut_matches
  add column if not exists event_id uuid
      references fut_events(id) on delete set null;

create index if not exists idx_matches_evento
  on fut_matches(event_id);

alter table fut_match_stats
  add column if not exists manual_player_id uuid
      references fut_manual_players(id) on delete cascade,
  add column if not exists jugadas_clave integer,
  add column if not exists titular boolean,
  add column if not exists notas text;

-- Un jugador, una fila por partido. Sin esto, guardar dos veces el mismo
-- campo creaba filas duplicadas y los totales del perfil salian inflados.
create unique index if not exists ux_match_stats_jugador
  on fut_match_stats(match_id, player_id) where player_id is not null;
create unique index if not exists ux_match_stats_manual
  on fut_match_stats(match_id, manual_player_id) where manual_player_id is not null;

-- La fila es de alguien: o de un jugador con cuenta o de uno sin ella, nunca
-- de los dos ni de ninguno.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_match_stats_dueno') then
    alter table fut_match_stats
      add constraint ck_match_stats_dueno check (
        (player_id is not null and manual_player_id is null) or
        (player_id is null and manual_player_id is not null)
      );
  end if;
end $$;

comment on column fut_matches.event_id is
  'Partido de la agenda del que sale. Nulo = apuntado a mano sin agenda.';
comment on column fut_match_stats.manual_player_id is
  'Jugador sin cuenta. Va uno u otro, nunca los dos (ck_match_stats_dueno).';
comment on column fut_match_stats.jugadas_clave is
  'Acciones decisivas que no son gol ni asistencia: ultimo pase, robo, parada.';

-- ── v10b ──────────────────────────────────────────────────────────────────
-- player_id era NOT NULL, asi que la fila de un jugador sin cuenta se
-- rechazaba entera. Exactamente lo mismo que le pasaba a fut_attendance antes
-- de la v8: se anadio manual_player_id y se olvido soltar la obligatoriedad
-- del otro. Quien manda ahora es ck_match_stats_dueno, que exige uno de los
-- dos y solo uno.
alter table fut_match_stats alter column player_id drop not null;
