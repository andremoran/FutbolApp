-- ============================================================================
--  FutbolApp (ProFoot Assistant) — Fecha de nacimiento completa
-- ============================================================================
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.   Es idempotente.
--
--  Qué añade y por qué
--  ───────────────────
--  Hasta ahora de un jugador solo se guardaba el AÑO de nacimiento, y la edad
--  se calculaba como `año_actual - año_nacimiento`. Eso falla en dos cosas:
--
--    · Se equivoca hasta en un año entero. Un chico nacido en diciembre de
--      2011 figura con 15 años desde el 1 de enero, cuando en realidad los
--      cumple once meses después.
--    · Y esa edad NO es cosmética: `tests_catalogo.categoria_por_edad()` la
--      usa para decidir contra qué baremo se compara cada prueba. Un error de
--      un año mueve al jugador de categoría entera —de sub-15 a sub-16— y
--      cambia el veredicto de todas sus marcas.
--
--  Con el día y el mes la edad es exacta y se actualiza sola: el jugador
--  cambia de categoría el día que cumple años, no el 1 de enero.
--
--  El `anio_nacimiento` de siempre NO se retira: sigue ahí para los jugadores
--  antiguos, de los que solo se sabe el año, y el código lo usa de respaldo
--  cuando no hay fecha completa. Los dos conviven.
-- ============================================================================

-- ─── Jugadores sin cuenta ───────────────────────────────────────────────────
ALTER TABLE fut_manual_players
  ADD COLUMN IF NOT EXISTS fecha_nacimiento date;

COMMENT ON COLUMN fut_manual_players.fecha_nacimiento IS
  'Fecha completa. Manda sobre anio_nacimiento cuando existe: da la edad exacta y por tanto la categoría de baremo correcta.';

-- ─── Jugadores con cuenta ───────────────────────────────────────────────────
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS fecha_nacimiento date;

COMMENT ON COLUMN usuarios.fecha_nacimiento IS
  'Fecha completa. Manda sobre anio_nacimiento cuando existe.';

-- ─── Rellenar lo que se pueda de lo que ya hay ──────────────────────────────
--  De un jugador antiguo solo se sabe el año, así que NO se le inventa un día:
--  se deja en NULL y el código sigue usando su `anio_nacimiento`. Poner un
--  1 de enero de mentira lo cambiaría de categoría sin que nadie lo pidiera.
--  Este bloque queda a propósito vacío; se documenta para que no se añada
--  luego pensando que se olvidó.

-- ─── Comprobación ───────────────────────────────────────────────────────────
--  Debe devolver dos filas, una por tabla.
SELECT table_name, column_name, data_type
  FROM information_schema.columns
 WHERE column_name = 'fecha_nacimiento'
   AND table_name IN ('fut_manual_players', 'usuarios')
 ORDER BY table_name;
