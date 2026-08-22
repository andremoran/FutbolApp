-- ============================================================================
--  FutbolApp (ProFoot Assistant) — Pasar lista a jugadores sin cuenta
-- ============================================================================
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.   Es idempotente.
--
--  Qué arregla
--  ───────────
--  `fut_attendance.player_id` era NOT NULL, pero al pasar lista a un jugador
--  SIN CUENTA la fila se escribe con `player_id = NULL` y el nombre en
--  `manual_player_id` (futbol/calendario.py › api_pasar_lista). El insert
--  fallaba con 23502 y la asistencia no se guardaba.
--
--  Y fallaba EN SILENCIO: `db.insert` registra el error y devuelve None, pero
--  la vista contaba el jugador igual, asi que la pantalla decia «Lista
--  guardada: 19 jugador(es)» sin haber guardado ni una. Por eso la tabla estaba
--  vacia en toda la base pese a haberse pasado lista.
--
--  En un equipo de formación casi nadie tiene cuenta, asi que en la practica
--  la asistencia no funcionaba para nadie.
--
--  Es una excepción de esta tabla, no el criterio del proyecto: en
--  `fut_attributes`, `fut_medical`, `fut_eval_results` y `fut_injuries` las dos
--  columnas ya admiten NULL, que es como debe ser cuando la fila puede colgar
--  de un jugador con cuenta o de uno apuntado a mano.
-- ============================================================================

ALTER TABLE fut_attendance
  ALTER COLUMN player_id DROP NOT NULL;

COMMENT ON COLUMN fut_attendance.player_id IS
  'Jugador con cuenta. NULL cuando la fila es de un jugador sin cuenta: entonces manda manual_player_id.';

-- ─── Comprobación ───────────────────────────────────────────────────────────
--  Las dos columnas deben salir con is_nullable = YES.
SELECT column_name, is_nullable
  FROM information_schema.columns
 WHERE table_name = 'fut_attendance'
   AND column_name IN ('player_id', 'manual_player_id')
 ORDER BY column_name;
