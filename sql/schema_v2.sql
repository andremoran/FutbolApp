-- ============================================================================
--  FutbolApp (ProFoot Assistant) — esquema v2
-- ============================================================================
--  Añade sobre sql/schema.sql:
--    · Los 5 roles  (rol × tier + administradores)
--    · Códigos de suscripción y sus canjes
--    · Evaluaciones con plantillas propias y resultados con baremo
--    · Calendario de verdad: tipo de evento, carga, rival, resultado
--    · Asistencia con cuatro estados
--    · Planes de entrenamiento, jugadores sin cuenta, solicitudes de ingreso,
--      ficha médica, avisos a los administradores y ajustes de la app
--
--  Cómo se usa:
--    Supabase → SQL Editor → pegar todo → Run.   (o `python aplicar_sql.py`)
--    Es idempotente: se puede correr las veces que haga falta.
-- ============================================================================


-- ════════════════════════════════════════════════════════════════════════════
--  1. LOS 5 ROLES
-- ════════════════════════════════════════════════════════════════════════════
--  El rol dice QUÉ ES el usuario y el tier CUÁNTO PAGA. De la combinación
--  salen los cinco roles del producto:
--
--     rol='paciente'    + tier='free'  → Jugador
--     rol='paciente'    + tier='pro'   → Jugador Pro
--     rol='especialista'+ tier='free'  → Entrenador
--     rol='especialista'+ tier='pro'   → Coach Pro
--     es_admin=true                    → Administrador  (3 personas)
--
--  Se separó así en vez de meter cinco valores en `rol` porque el rol no
--  cambia nunca y el tier cambia cada mes: mezclarlos obligaría a reescribir
--  el rol en cada cobro y en cada impago.
-- ────────────────────────────────────────────────────────────────────────────
alter table usuarios add column if not exists tier         text    default 'free';
alter table usuarios add column if not exists es_admin     boolean default false;
alter table usuarios add column if not exists pro_hasta    timestamptz;
alter table usuarios add column if not exists pro_origen   text;      -- paypal | deuna | codigo | admin
alter table usuarios add column if not exists codigo_promo text;
alter table usuarios add column if not exists ultimo_acceso timestamptz;
alter table usuarios add column if not exists bloqueado    boolean default false;

create index if not exists usuarios_tier_idx  on usuarios(tier);
create index if not exists usuarios_admin_idx on usuarios(es_admin) where es_admin;

-- Las cuentas que ya estaban activas de antes se quedan en Pro.
update usuarios set tier = 'pro'
 where tier is distinct from 'pro' and activo = true;


-- ════════════════════════════════════════════════════════════════════════════
--  2. CÓDIGOS DE SUSCRIPCIÓN
-- ════════════════════════════════════════════════════════════════════════════
--  Un código regala meses de Pro. Lo crea un administrador desde el panel.
--  `usos` y `max_usos` permiten tanto el código personal (1 uso) como el
--  código de club (30 usos).
create table if not exists fut_promo_codes (
  id           uuid primary key default gen_random_uuid(),
  codigo       text not null unique,
  meses        int  not null default 3 check (meses between 1 and 24),
  max_usos     int  not null default 1 check (max_usos >= 1),
  usos         int  not null default 0,
  para_rol     text default 'cualquiera',       -- cualquiera | paciente | especialista
  vence        timestamptz,                     -- caducidad del código en sí
  activo       boolean not null default true,
  nota         text,                            -- "Club San Martín, oct-2026"
  creado_por   uuid references usuarios(id) on delete set null,
  creado       timestamptz default now()
);
create index if not exists fut_promo_codes_idx on fut_promo_codes(codigo);

create table if not exists fut_promo_uses (
  id         uuid primary key default gen_random_uuid(),
  code_id    uuid not null references fut_promo_codes(id) on delete cascade,
  user_id    uuid not null references usuarios(id) on delete cascade,
  codigo     text,
  pro_hasta  timestamptz not null,
  creado     timestamptz default now()
);
-- Un canje vigente por usuario: al vencer se puede canjear otro (upsert).
create unique index if not exists fut_promo_uses_user_uidx on fut_promo_uses(user_id);
create index        if not exists fut_promo_uses_code_idx  on fut_promo_uses(code_id);


-- ════════════════════════════════════════════════════════════════════════════
--  3. EVALUACIONES
-- ════════════════════════════════════════════════════════════════════════════
--  El catálogo de pruebas estándar y sus baremos viven en el código
--  (futbol/tests_catalogo.py) porque son constantes publicadas, no datos del
--  cliente: así no hay que sembrar nada y no se desincronizan entre entornos.
--  Aquí solo van las pruebas QUE INVENTA EL ENTRENADOR y los RESULTADOS.

-- 3.0 Contexto competitivo del equipo
--  Sin esto no se puede evaluar bien: 2.400 m en Cooper es excelente para un
--  sub-14 de escuelita y flojo para un profesional. El baremo con el que se
--  compara sale de aquí.
alter table fut_teams add column if not exists categoria_edad text default 'general';
alter table fut_teams add column if not exists nivel          text default 'general';

-- 3.1 Pruebas propias del entrenador
create table if not exists fut_eval_templates (
  id           uuid primary key default gen_random_uuid(),
  coach_id     uuid references usuarios(id) on delete cascade,
  clave        text not null,                   -- 'custom:<uuid corto>'
  nombre       text not null,
  categoria    text not null default 'fisico',  -- fisico|tecnico|tactico|mental|antropometria
  descripcion  text default '',
  protocolo    text default '',                 -- cómo se toma la prueba
  campos       jsonb not null default '[]'::jsonb,
  icono        text default 'activity',
  creado       timestamptz default now()
);
create unique index if not exists fut_eval_templates_clave_uidx on fut_eval_templates(clave);
create index        if not exists fut_eval_templates_coach_idx  on fut_eval_templates(coach_id);

-- 3.2 Baremos propios: el entrenador puede ajustar el listón a su realidad
create table if not exists fut_eval_ranges (
  id          uuid primary key default gen_random_uuid(),
  coach_id    uuid not null references usuarios(id) on delete cascade,
  test_clave  text not null,
  campo       text not null default 'valor',
  categoria   text not null default 'general',  -- sub_12…adulto | general
  nivel       text not null default 'general',  -- juvenil…elite | general
  direccion   text not null default 'mayor_mejor',
  elite       numeric,
  bueno       numeric,
  promedio    numeric,
  debil       numeric,
  fuente      text default 'Baremo propio del entrenador',
  creado      timestamptz default now()
);
create unique index if not exists fut_eval_ranges_uidx
  on fut_eval_ranges(coach_id, test_clave, campo, categoria, nivel);

-- 3.3 Resultados
--  `valores` guarda {campo: número} porque una prueba puede medir varias
--  cosas (Yo-Yo devuelve nivel Y distancia) y añadir una columna por medida
--  obligaría a migrar la tabla con cada prueba nueva.
create table if not exists fut_eval_results (
  id                uuid primary key default gen_random_uuid(),
  coach_id          uuid references usuarios(id) on delete set null,
  player_id         uuid references usuarios(id) on delete cascade,
  manual_player_id  uuid,                        -- jugador sin cuenta
  jugador_nombre    text not null default '',
  test_clave        text not null,
  test_nombre       text not null default '',
  categoria         text default 'fisico',
  fecha             date not null default current_date,
  valores           jsonb not null default '{}'::jsonb,
  niveles           jsonb default '{}'::jsonb,   -- {campo: 'elite'|'bueno'|…}
  puntaje           int,                          -- 0-100, comparable entre pruebas
  contexto_edad     text default 'general',
  contexto_nivel    text default 'general',
  notas             text default '',
  informe_ia        text default '',
  creado            timestamptz default now()
);
create index if not exists fut_eval_res_player_idx on fut_eval_results(player_id, fecha desc);
create index if not exists fut_eval_res_coach_idx  on fut_eval_results(coach_id, fecha desc);
create index if not exists fut_eval_res_test_idx   on fut_eval_results(test_clave, fecha desc);
create index if not exists fut_eval_res_manual_idx on fut_eval_results(manual_player_id);


-- ════════════════════════════════════════════════════════════════════════════
--  4. CALENDARIO DE VERDAD
-- ════════════════════════════════════════════════════════════════════════════
--  fut_events nació como "agenda": título, fecha y poco más. Para que sirva de
--  calendario necesita saber QUÉ es cada cosa y CUÁNTO carga.
alter table fut_events add column if not exists tipo_entreno   text;    -- fisico|tecnico|tactico|mental|mixto
alter table fut_events add column if not exists intensidad     text default 'media';
alter table fut_events add column if not exists duracion_min   int  default 90;
alter table fut_events add column if not exists rival          text;
alter table fut_events add column if not exists local          boolean default true;
alter table fut_events add column if not exists resultado      text;
alter table fut_events add column if not exists estado         text default 'programado';  -- programado|hecho|cancelado
alter table fut_events add column if not exists plan_id        uuid;
alter table fut_events add column if not exists hora_fin       time;

create index if not exists fut_events_tipo_idx on fut_events(coach_id, tipo, fecha);

-- La asistencia pasa de 3 estados a los 4 del estándar del MVP.
alter table fut_attendance add column if not exists manual_player_id uuid;
alter table fut_attendance add column if not exists jugador_nombre   text default '';
alter table fut_attendance add column if not exists registrado_por   uuid references usuarios(id) on delete set null;
alter table fut_attendance add column if not exists actualizado      timestamptz default now();

--  'asiste' → 'presente', 'falta' → 'ausente', 'duda' → 'pendiente'.
update fut_attendance set estado = 'presente' where estado = 'asiste';
update fut_attendance set estado = 'ausente'  where estado = 'falta';
update fut_attendance set estado = 'pendiente' where estado = 'duda';

-- El índice único original no contempla al jugador sin cuenta.
create unique index if not exists fut_attendance_manual_uidx
  on fut_attendance(event_id, manual_player_id) where manual_player_id is not null;


-- ════════════════════════════════════════════════════════════════════════════
--  5. PLANES DE ENTRENAMIENTO
-- ════════════════════════════════════════════════════════════════════════════
--  Una plantilla de sesión reutilizable: el entrenador la arma una vez y la
--  vuelca al calendario cuantas veces quiera.
create table if not exists fut_training_plans (
  id           uuid primary key default gen_random_uuid(),
  coach_id     uuid not null references usuarios(id) on delete cascade,
  nombre       text not null,
  objetivo     text default '',
  tipo         text default 'mixto',            -- fisico|tecnico|tactico|mental|mixto
  intensidad   text default 'media',
  duracion_min int default 90,
  bloques      jsonb not null default '[]'::jsonb,  -- [{nombre, minutos, descripcion, material}]
  material     text default '',
  veces_usado  int default 0,
  creado       timestamptz default now()
);
create index if not exists fut_plans_coach_idx on fut_training_plans(coach_id, creado desc);


-- ════════════════════════════════════════════════════════════════════════════
--  6. JUGADORES SIN CUENTA
-- ════════════════════════════════════════════════════════════════════════════
--  Un chico de 12 años no tiene correo. El entrenador lo apunta a mano y lo
--  evalúa igual; si algún día se registra, se le vincula la ficha.
create table if not exists fut_manual_players (
  id            uuid primary key default gen_random_uuid(),
  coach_id      uuid not null references usuarios(id) on delete cascade,
  nombre        text not null,
  dorsal        int,
  posicion      text default '',
  pie_habil     text default '',
  anio_nacimiento int,
  estatura      numeric,
  peso          numeric,
  telefono      text,
  tutor         text,                            -- contacto del representante
  notas         text default '',
  activo        boolean default true,
  vinculado_a   uuid references usuarios(id) on delete set null,
  creado        timestamptz default now()
);
create index if not exists fut_manual_coach_idx on fut_manual_players(coach_id, activo);


-- ════════════════════════════════════════════════════════════════════════════
--  7. SOLICITUDES DE INGRESO
-- ════════════════════════════════════════════════════════════════════════════
--  El código de equipo deja entrar a cualquiera que lo tenga. Con esto el
--  entrenador decide: el jugador pide y él acepta o rechaza.
create table if not exists fut_join_requests (
  id         uuid primary key default gen_random_uuid(),
  coach_id   uuid not null references usuarios(id) on delete cascade,
  player_id  uuid not null references usuarios(id) on delete cascade,
  mensaje    text default '',
  posicion   text default '',
  estado     text default 'pendiente',           -- pendiente|aceptada|rechazada
  resuelto   timestamptz,
  creado     timestamptz default now()
);
create unique index if not exists fut_join_req_uidx on fut_join_requests(coach_id, player_id);
create index        if not exists fut_join_req_idx  on fut_join_requests(coach_id, estado);


-- ════════════════════════════════════════════════════════════════════════════
--  8. FICHA MÉDICA Y LESIONES
-- ════════════════════════════════════════════════════════════════════════════
create table if not exists fut_medical (
  player_id      uuid primary key references usuarios(id) on delete cascade,
  grupo_sanguineo text default '',
  alergias       text default '',
  medicacion     text default '',
  condiciones    text default '',
  contacto_nombre text default '',
  contacto_tel   text default '',
  seguro         text default '',
  actualizado    timestamptz default now()
);

create table if not exists fut_injuries (
  id           uuid primary key default gen_random_uuid(),
  player_id    uuid references usuarios(id) on delete cascade,
  manual_player_id uuid,
  coach_id     uuid references usuarios(id) on delete set null,
  zona         text not null default '',         -- isquiotibial, tobillo…
  lado         text default '',                  -- izquierdo|derecho|—
  tipo         text default '',                  -- muscular|articular|ósea|otra
  gravedad     text default 'leve',              -- leve|moderada|grave
  fecha        date not null default current_date,
  alta_prevista date,
  alta_real    date,
  estado       text default 'activa',            -- activa|recuperando|alta
  descripcion  text default '',
  creado       timestamptz default now()
);
create index if not exists fut_injuries_player_idx on fut_injuries(player_id, estado);
create index if not exists fut_injuries_coach_idx  on fut_injuries(coach_id, fecha desc);


-- ════════════════════════════════════════════════════════════════════════════
--  9. AVISOS A LOS ADMINISTRADORES
-- ════════════════════════════════════════════════════════════════════════════
--  Toda alta, pago, canje y baja deja constancia aquí. El correo se puede
--  perder o irse a spam; la bandeja del panel no.
create table if not exists fut_notificaciones (
  id        uuid primary key default gen_random_uuid(),
  tipo      text not null default 'info',        -- alta|pago|deuna|codigo|baja|info
  titulo    text not null,
  detalle   text default '',
  user_id   uuid references usuarios(id) on delete set null,
  importe   text,
  datos     jsonb default '{}'::jsonb,
  leida     boolean default false,
  leida_por uuid references usuarios(id) on delete set null,
  creado    timestamptz default now()
);
create index if not exists fut_notif_idx on fut_notificaciones(leida, creado desc);


-- ════════════════════════════════════════════════════════════════════════════
--  10. AJUSTES DE LA APP
-- ════════════════════════════════════════════════════════════════════════════
--  Clave-valor para lo que el administrador cambia sin tocar el código: los
--  datos de la cuenta DeUna, los precios, el aviso del panel.
create table if not exists fut_settings (
  clave       text primary key,
  valor       jsonb not null default '{}'::jsonb,
  actualizado timestamptz default now(),
  por         uuid references usuarios(id) on delete set null
);


-- ════════════════════════════════════════════════════════════════════════════
--  11. PAGOS — ampliación para DeUna
-- ════════════════════════════════════════════════════════════════════════════
alter table fut_pagos add column if not exists importe      text;
alter table fut_pagos add column if not exists moneda       text default 'USD';
alter table fut_pagos add column if not exists referencia   text;      -- nº de comprobante DeUna
alter table fut_pagos add column if not exists comprobante  text;      -- URL de la imagen
alter table fut_pagos add column if not exists meses        int default 1;
alter table fut_pagos add column if not exists revisado_por uuid references usuarios(id) on delete set null;
alter table fut_pagos add column if not exists revisado     timestamptz;
alter table fut_pagos add column if not exists nota_admin   text default '';

create index if not exists fut_pagos_estado_idx on fut_pagos(estado, creado desc);


-- ════════════════════════════════════════════════════════════════════════════
--  12. SEGURIDAD A NIVEL DE FILA
-- ════════════════════════════════════════════════════════════════════════════
--  Igual que en schema.sql: RLS activado y SIN políticas públicas. La app
--  entra siempre desde el servidor con la clave de servicio (que salta RLS por
--  diseño) y comprueba los permisos en cada endpoint. Si alguien consiguiera
--  la clave anónima, desde el navegador no leería ni escribiría nada.
do $$
declare t text;
begin
  foreach t in array array[
    'fut_promo_codes','fut_promo_uses','fut_eval_templates','fut_eval_ranges',
    'fut_eval_results','fut_training_plans','fut_manual_players',
    'fut_join_requests','fut_medical','fut_injuries','fut_notificaciones',
    'fut_settings'
  ]
  loop
    execute format('alter table %I enable row level security', t);
  end loop;
end $$;


-- ════════════════════════════════════════════════════════════════════════════
--  13. AVISAR A POSTGREST DEL ESQUEMA NUEVO
-- ════════════════════════════════════════════════════════════════════════════
--  Sin esto la API REST sigue sirviendo el esquema viejo y las tablas nuevas
--  responden PGRST205 durante un rato.
notify pgrst, 'reload schema';


-- ════════════════════════════════════════════════════════════════════════════
--  COMPROBACIÓN
-- ════════════════════════════════════════════════════════════════════════════
do $$
declare n int;
begin
  select count(*) into n from information_schema.tables
   where table_schema = 'public' and table_name like 'fut\_%';
  raise notice '════════════════════════════════════';
  raise notice '  Tablas fut_*: %  (esperadas: 34)', n;
  raise notice '  Esquema v2 aplicado';
  raise notice '════════════════════════════════════';
end $$;


-- ════════════════════════════════════════════════════════════════════════════
--  14. ESTADO DEL JUGADOR (autoinforme)
-- ════════════════════════════════════════════════════════════════════════════
--  Los tres números que el MVP enseña en «Estado físico promedio» del tablero
--  del entrenador. Vienen de `user_profiles` en la app original: los pone EL
--  PROPIO JUGADOR y NO son confidenciales — no tienen nada que ver con las
--  respuestas del check-in de bienestar, que el entrenador no ve nunca.
alter table fut_player_profile add column if not exists energia       int;
alter table fut_player_profile add column if not exists motivacion    int;
alter table fut_player_profile add column if not exists estado_fisico int;
alter table fut_player_profile add column if not exists estado_actualizado timestamptz;

notify pgrst, 'reload schema';


-- ════════════════════════════════════════════════════════════════════════════
--  15. CUERPO TÉCNICO: ENTRENADOR PRINCIPAL + ASISTENTES
-- ════════════════════════════════════════════════════════════════════════════
--  Un equipo puede tener varios entrenadores. El PRINCIPAL es el dueño del
--  `codigo_equipo` y de la suscripción; los ASISTENTES evalúan, miden, pasan
--  lista y anotan igual que él, y lo que anotan cae en los datos del equipo.
--
--  Por qué `principal_id` y no un `team_id` nuevo: en esta app el equipo YA se
--  identifica por el id del entrenador principal (fut_plantilla.coach_id,
--  fut_events.coach_id, fut_eval_results.coach_id…). Inventar un team_id
--  obligaría a migrar nueve tablas y a reescribir cien consultas; con esto,
--  `db.equipo_id()` traduce «quién soy» a «de qué equipo escribo» y el resto
--  del código sigue igual.
create table if not exists fut_team_coaches (
  id           uuid primary key default gen_random_uuid(),
  principal_id uuid not null references usuarios(id) on delete cascade,
  coach_id     uuid not null references usuarios(id) on delete cascade,
  rol          text not null default 'asistente',   -- principal | asistente
  estado       text not null default 'activo',      -- activo | retirado
  creado       timestamptz default now(),
  retirado     timestamptz
);
-- Un entrenador pertenece a un equipo a la vez, como los jugadores.
create unique index if not exists fut_team_coaches_uidx on fut_team_coaches(coach_id);
create index        if not exists fut_team_coaches_pri  on fut_team_coaches(principal_id, estado);

-- Las solicitudes de ingreso ahora distinguen jugador de asistente.
alter table fut_join_requests add column if not exists tipo text default 'jugador';

-- ── Firma de quién anota ──
--  Sin esto, en un equipo con asistentes no hay forma de saber quién puso un
--  número, y el primer dato raro se convierte en una discusión.
alter table fut_eval_results   add column if not exists registrado_por uuid references usuarios(id) on delete set null;
alter table fut_events         add column if not exists registrado_por uuid references usuarios(id) on delete set null;
alter table fut_matches        add column if not exists registrado_por uuid references usuarios(id) on delete set null;
alter table fut_match_stats    add column if not exists registrado_por uuid references usuarios(id) on delete set null;
alter table fut_observaciones  add column if not exists registrado_por uuid references usuarios(id) on delete set null;
alter table fut_injuries       add column if not exists registrado_por uuid references usuarios(id) on delete set null;
alter table fut_manual_players add column if not exists registrado_por uuid references usuarios(id) on delete set null;

do $$
begin
  execute 'alter table fut_team_coaches enable row level security';
end $$;

notify pgrst, 'reload schema';
