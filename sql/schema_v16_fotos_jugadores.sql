-- v16 · La foto del jugador
--
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.   Es idempotente.
--    O bien:   python aplicar_sql.py sql/schema_v16_fotos_jugadores.sql
--
--  Qué añade y por qué
--  ───────────────────
--  En la pantalla Equipo todos los jugadores eran un círculo con un número.
--  Un entrenador de formación lleva veinte chavales y a varios los conoce de
--  cara antes que de nombre; con la lista ordenada por overall, además, el
--  orden cambia cada semana y no hay dónde agarrarse.
--
--  Por qué una tabla y no la columna `usuarios.foto` que ya existe
--  ───────────────────────────────────────────────────────────────
--  Esa columna se lee en CASI TODAS las pantallas: `jugadores_del_entrenador`
--  hace `select('*')` sobre usuarios y esa lista la usan el panel, la agenda,
--  la evaluación, el partido… Meter ahí la imagen en base64 sería arrastrar
--  medio megabyte por consulta para pintar un círculo de 54 píxeles.
--
--  Aquí la imagen vive aparte y solo se lee cuando se va a enseñar: la lista
--  pide únicamente QUIÉN tiene foto y de cuándo es, y los bytes se sirven en
--  su propia dirección, que el navegador cachea.
--
--  `usuarios.foto` se respeta: si ya trae una URL —la escribe la app nativa—
--  esa manda y esta tabla ni se toca.

create table if not exists public.fut_player_photos (
  id                uuid primary key default gen_random_uuid(),
  coach_id          uuid not null references public.usuarios(id) on delete cascade,

  -- Uno de los dos, nunca los dos: con cuenta o sin ella.
  player_id         uuid references public.usuarios(id) on delete cascade,
  manual_player_id  uuid references public.fut_manual_players(id) on delete cascade,

  mime              text not null default 'image/jpeg',
  datos             text not null,          -- la imagen en base64, ya recortada
  bytes             integer,                -- tamaño real, para poder vigilarlo
  actualizado       timestamptz default now(),

  constraint fut_player_photos_un_dueno check (
    (player_id is not null and manual_player_id is null) or
    (player_id is null and manual_player_id is not null)
  )
);

-- Una foto por jugador. Índices PARCIALES porque el dueño es una columna u
-- otra, igual que en fut_attributes: un único índice sobre las dos dejaría
-- pasar dos filas con el mismo player_id y manual_player_id nulo.
create unique index if not exists ux_player_photos_jugador
  on public.fut_player_photos (player_id) where player_id is not null;
create unique index if not exists ux_player_photos_manual
  on public.fut_player_photos (manual_player_id) where manual_player_id is not null;

-- La pantalla Equipo pregunta «de este equipo, ¿quién tiene foto?».
create index if not exists idx_player_photos_equipo
  on public.fut_player_photos (coach_id);

-- ─── Seguridad ──────────────────────────────────────────────────────────────
--  Mismo candado que el resto de las tablas fut_*: RLS activado y NINGUNA
--  política, así queda cerrada a la clave pública y solo la atraviesa
--  `service_role`, que es con la que habla Flask. Aquí importa más que en
--  otras tablas: son caras de chavales, y varias de menores.
alter table public.fut_player_photos enable row level security;

comment on table public.fut_player_photos is
  'Foto de cada jugador (con cuenta o sin ella), en base64. La sirve Flask en /foto/jugador/<id>, nunca el navegador directamente.';
comment on column public.fut_player_photos.datos is
  'La imagen ya recortada y encogida en el navegador antes de subirla: cuadrada, 400 px de lado como mucho.';
comment on column public.fut_player_photos.actualizado is
  'Sirve de ETag: si no cambia, el navegador no vuelve a descargar la foto.';
