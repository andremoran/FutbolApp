-- v12 · Donde se guarda la lectura que hace la IA de un jugador
--
-- La pantalla de evaluar lleva desde el principio una tarjeta que dice
-- «Reporte IA semanal» y que nunca ha tenido nada dentro: la ruta pasaba
-- `reporte=None` a pelo. No era un fallo de la IA — es que no habia ni quien
-- lo generara ni donde guardarlo.
--
-- Guardarlo importa por dos motivos. Uno, cuesta dinero y segundos: no se
-- puede rehacer cada vez que alguien abre la pantalla. Y dos, el entrenador
-- tiene que poder volver a leerlo, y ver DE CUANDO es — un analisis de hace
-- tres meses dice otra cosa que el de ayer.
--
-- Una fila por jugador y periodo: pedir «el ultimo mes» dos veces actualiza
-- la lectura del mes, no crea otra.

create table if not exists fut_ia_analisis (
  id                uuid primary key default gen_random_uuid(),
  coach_id          uuid not null references usuarios(id) on delete cascade,
  player_id         uuid references usuarios(id) on delete cascade,
  manual_player_id  uuid references fut_manual_players(id) on delete cascade,

  periodo   text not null default '30',
  resumen   text,
  -- {fuerte: [...], mejorar: [...], plan: [...]}
  puntos    jsonb,
  -- Los numeros con los que se escribio, para saber si sigue valiendo.
  cifras    jsonb,

  creado    timestamptz default now(),
  creado_por uuid references usuarios(id) on delete set null
);

-- La fila es de alguien: o de un jugador con cuenta o de uno sin ella, nunca
-- de los dos ni de ninguno. Mismo criterio que fut_match_stats (v10).
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_ia_analisis_dueno') then
    alter table fut_ia_analisis
      add constraint ck_ia_analisis_dueno check (
        (player_id is not null and manual_player_id is null) or
        (player_id is null and manual_player_id is not null)
      );
  end if;
end $$;

create unique index if not exists ux_ia_analisis_jugador
  on fut_ia_analisis(player_id, periodo) where player_id is not null;
create unique index if not exists ux_ia_analisis_manual
  on fut_ia_analisis(manual_player_id, periodo) where manual_player_id is not null;

comment on table  fut_ia_analisis is
  'Lectura de la IA sobre como va un jugador. Una por jugador y periodo.';
comment on column fut_ia_analisis.cifras is
  'Foto de los numeros con los que se escribio el analisis: sirve para saber '
  'si el texto sigue cuadrando con lo que hoy dice la pantalla.';
