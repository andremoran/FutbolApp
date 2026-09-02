# FutbolApp (ProFoot Assistant)

Aplicación web de gestión de equipos de fútbol. Es la réplica en web de la app
móvil ProFoot Assistant: mismas pestañas, mismo diseño, instalable como PWA.

**Stack:** Flask · Supabase (PostgREST, sin ORM) · PayPal · Gemini nivel gratuito.
**Producción:** https://profut.org (Contabo, manual) y espejo en Vercel (automático).

---

## Arrancar y probar

```bash
pip install -r requirements.txt
python app.py                 # http://localhost:5000
```

Hace falta un `.env` con al menos `SUPABASE_URL`, `SUPABASE_KEY` (service_role),
`SECRET_KEY` y `CODIGOS_ENTRENADOR`. Plantilla en `.env.example`.

**Las pruebas hablan con el Supabase de verdad**, no hay mocks. Tardan minutos y
crean cuentas `*@prueba.profoot` / `*@simula.profoot` que borran al terminar.

```bash
python _probar.py             # 181 · pantallas de los 5 roles + candados de plan
python _probar_flujos.py      #  58 · recorridos de punta a punta
python _probar_segmentos.py   #  49 · los tres perfiles son tres cosas distintas
python _simular_perfiles.py   #  60 · el primer día de un entrenador de cada perfil
python _probar_global.py      #  78 · el OVR de un jugador a lo largo de 12 semanas
python _paridad.py            #       que no falte ninguna pantalla del MVP
python _medir_pantallas.py    #       cuántas consultas cuesta abrir cada pantalla
```

Antes de subir algo que toque pantallas del entrenador, corre al menos
`_probar.py` y `_simular_perfiles.py`.

---

## Cómo está montado

```
app.py              Flask, sesión, CSRF, context processor global, manejo de errores
auth.py             registro / acceso / reset por correo. CODIGOS_ENTRENADOR
usuarios.py         hash de contraseñas (scrypt propio)
roles.py            TODO lo que decide permisos. es_pro, puede, @solo_pro, @solo_admin
pagos.py            PayPal Subscriptions
suscripciones.py    canje de códigos
avisos.py           avisa a los admin por correo + bandeja del panel
admin.py            panel /admin

futbol/             23 módulos, todos cuelgan del mismo blueprint (bp) montado en la raíz
  db.py             la única puerta a Supabase. q(), one(), rows(), insert(), update()
  coach.py          pantallas del entrenador          player.py    pantallas del jugador
  evaluaciones.py   pruebas, baremos y resultados     tests_catalogo.py  las 58 pruebas
  microciclos.py    MOTOR de la planificación semanal
  microciclo_modelos.py   las TRES periodizaciones (ver abajo)
  segmentos.py      a quién entrena cada entrenador   (ver abajo)
  ia.py             el asistente (Gemini)             mental.py    salud mental
  calendario.py · equipo.py · salud.py · api.py · account.py · social.py · graficas.py

templates/          101 plantillas Jinja
static/profoot.css  puerto 1:1 del diseño de la app móvil
sql/                14 migraciones, TODAS idempotentes
```

Base: **39 tablas `fut_*` + `usuarios`** en el proyecto `uegjzyudvvlduhnpuqdv`.

---

## Las decisiones que NO se pueden romper

Cada una está así por un motivo concreto. Si algo parece innecesariamente
complicado, probablemente sea una de estas.

### 1. El entrenador NUNCA ve las respuestas de salud mental

Solo un semáforo verde/ámbar/rojo y la fecha. Las consultas del coach en
`mental.py` piden **columnas explícitas** y jamás `respuestas`. Si se rompe esa
frontera los jugadores dejan de ser honestos y el módulo entero deja de servir.
La interfaz lo dice en voz alta a los dos lados.

### 2. Rol × tier, no un solo campo

`usuarios.rol` ('paciente' | 'especialista') × `usuarios.tier` ('free' | 'pro')
+ `es_admin` componen los cinco roles. Están separados porque **el rol no cambia
nunca y el tier cambia con cada cobro**: en un solo campo, cada renovación
tendría que reescribir qué ES la persona, y un impago convertiría a un entrenador
en otra cosa.

Todo lo que decide permisos vive en `roles.py`. No comprobar planes a mano en una
vista: usar `@solo_pro('lo_que_sea')`.

### 3. Los baremos publicados van en el CÓDIGO, no en la base

`futbol/tests_catalogo.py` — 58 pruebas con cortes publicados (Cooper, Bangsbo,
Haugen, Léger, EUROFIT…), estratificados por categoría de edad × nivel
competitivo con caída hacia atrás. Un baremo publicado es una constante, no un
dato del cliente: sembrarlo obligaría a repetirlo por entorno y a vigilar que no
se desincronicen. En la base solo van las pruebas que se inventa el entrenador,
sus baremos propios y los resultados.

### 4. `db._normalizar_usuario()` traduce a las claves viejas

Convierte la fila de `usuarios` a los nombres que esperan las plantillas
(`name`, `gender`, `weight`, `profile_photo`…). Evitó tocar 35 archivos al
cambiar de esquema. **No quitarlo** aunque parezca redundante.

### 5. Nunca activar un plan con lo que diga el navegador

Los pagos por DeUna quedan `estado='pendiente'` y los aprueba un admin. Los de
PayPal se verifican contra su API antes de activar, comprobando **que el
`plan_id` cobrado coincida** — si no, cualquiera activaría el plan caro pagando
el barato.

### 6. Una escritura que falla no puede responder que todo fue bien

`db.update`/`db.insert` aceptan `obligatorio=True`: úsalo siempre que el usuario
vaya a leer un «Listo» después. Perder una escritura en silencio es peor que
fallar.

### 7. El global del jugador sale de los 18 atributos, y de nada más

`fut_attributes` tiene cuatro columnas viejas (`tecnica/fisico/tactico/mental`)
que son **derivadas**: las recalcula `db.guardar_atributos()` desde los 18 y las
lee `db.atributos()`. Nadie más las escribe. Cuando las pruebas escribían ahí,
el overall no se enteraba y la siguiente evaluación borraba tres meses de
marcas. **Toda escritura del Perfil Dinámico pasa por `guardar_atributos()`**,
que recalcula el overall, las medias de familia, deja la foto semanal y repasa
las alertas.

El táctico no se evalúa: se calcula desde `db.ATRIBUTOS_TACTICOS`
(visión de juego + concentración + disciplina), los mismos que mueve la prueba
«Perfil Táctico».

### 8. Una marca premia MEJORAR, no repetir

`evaluaciones.aplicar_a_ficha()`: la primera vez que un jugador hace una prueba
se le coloca por baremo y por su puesto en el equipo. A partir de la segunda
manda `_progreso_propio()` — cuánto ha mejorado respecto a su mejor marca
anterior. Si no, un entrenador que pase el Cooper todos los lunes le sube 20
puntos de resistencia a un chaval que corre lo mismo que en agosto.

### 9. El 50 de relleno no es una nota

`ficha_atributos()` rellena los huecos con 50 para no dejar pantallas en
blanco, y `_tiene_perfil` dice si hay evaluación de verdad. **Ninguna pantalla
puede enseñar ese 50 como si fuera una valoración**: ni «Mi Ficha», ni la
cabecera del entrenador, ni la IA. A quien nadie ha evaluado se le dice eso.

---

## Los tres segmentos (agosto 2026 — lo más nuevo)

La app daba por hecho una sola realidad: club profesional, sesión diaria, partido
cada fin de semana. Pero la mayoría de quien la usa no vive ahí. Ahora cada
equipo tiene un **segmento**:

```
fut_teams.segmento = 'profesional' | 'semipro' | 'colegio'      (por defecto profesional)
```

Vive en el **EQUIPO, nunca en la persona**. El jugador no elige: entra con el
código de su entrenador y hereda ese segmento.

### Qué decide

| | archivo |
|---|---|
| La periodización de la semana | `microciclo_modelos.py` |
| Cómo se le habla (vocabulario) | `segmentos.py` › `VOCABULARIO` |
| Sus objetivos y primeros pasos | `segmentos.py` › `OBJETIVOS`, `PASOS` |
| Qué pruebas se le recomiendan | `segmentos.py` › `BATERIA` |
| Qué puede aconsejarle la IA | `segmentos.py` › `IA` → `ia.py` › `_prompt` |
| Contra qué baremo se mide por defecto | `segmentos.py` › `nivel_sugerido` |

### `microciclos.py` es ahora solo el MOTOR

No tiene ni una tabla dentro: la planilla, el guardado, la gráfica y el volcado
al calendario. Todo lo que cambia entre segmentos está en
`microciclo_modelos.py`, un modelo por segmento con sus días, rotaciones,
principios, fuentes y una función `revisar(dias)`.

- **profesional** — intacto. Buchheit 2024, notación MD-5…MD, 11 principios.
- **semipro** — misma notación MD, otro contenido. UN solo día duro.
- **colegio** — rompe la notación MD a propósito: días `S1/S2/S3/JORNADA/LIBRE`.

### Dos cosas que hay que respetar al tocar esto

**Las claves guardadas no cambian nunca.** Son siempre `inicial`, `fisico`,
`tecnico`, `tactico`, `estrategico`, `psicologico`, `final`. Lo único que cambia
por segmento es la **etiqueta**. Así un entrenador puede cambiar de segmento sin
perder una línea de lo que había escrito.

**Un microciclo guarda su propio segmento** (`fut_microcycles.segmento`) y al
guardarlo se valida contra el modelo **de la semana**, no contra el del equipo.
Si se validara con el del equipo, a quien cambiara de segmento se le vaciarían
todos los días viejos, porque su `md` no existe en el modelo nuevo.

### Para añadir un cuarto segmento

1. La clave en `sql/` (nueva migración con el `check` ampliado)
2. `segmentos.py`: entrada en `SEGMENTOS`, `VOCABULARIO`, `OBJETIVOS`, `BATERIA`,
   `PASOS`, `IA`
3. `microciclo_modelos.py`: su modelo + entrada en `MODELOS`
4. `_probar_segmentos.py` lo comprueba solo

---

## Convenciones de este repo

**Los comentarios explican el POR QUÉ, no el qué.** Este repo está lleno de
comentarios que cuentan qué se rompió antes y por qué el código está así. Es lo
que hace que se pueda volver seis meses después. Mantén ese tono: en español,
concreto, sin adornos.

```python
#  Se pide por `equipo_id` y no por `user.id`: un asistente técnico trabaja
#  sobre el equipo del principal, y preguntando por el suyo no salía nada.
```

**Los mensajes de commit son una explicación, no una etiqueta.** Título en una
línea que diga qué cambia para el usuario, y luego el porqué. Nada de
`feat:` / `fix:`. Mira `git log` para el tono.

**El diseño móvil es 1:1 con la app nativa.** `static/profoot.css` es un puerto
de `theme/design.ts`. La barra de pestañas (`_tabs_coach.html`,
`_tabs_player.html`) es réplica exacta y **no se toca**: lo nuevo cuelga del
menú ⋯ o de segmentos dentro de la pantalla.

**Todo lo del entrenador se pide por `db.equipo_id(current_user.id)`**, nunca por
`current_user.id` directamente. Un asistente técnico trabaja sobre el equipo del
principal; con su propio id no sale nada.

---

## Trampas conocidas

**Jinja no admite expresiones generadoras.** `{{ dict((c, d) for c, e, d in x) }}`
no compila. La tabla se arma en la vista y se pasa hecha.

**`--field: #15803d` es el VERDE DE LA CANCHA**, no un gris de formulario. Para
fondos claros: `--border-soft`.

**`is_active` tiene que ser propiedad, no método.** Flask-Login lo lee sin
llamarlo, y un método enlazado siempre es verdadero: una cuenta bloqueada entraba
igual.

**Al cerrar sesión, `session.clear()` va ANTES de `logout_user()`.** Al revés
borra el `_remember='clear'` y la cookie de «recordarme» sobrevive.

**Un `.bat` con saltos Unix (LF) se corrompe.** `cmd` parte los `REM` y grita
`"EM" no se reconoce`. Escribirlos **CRLF y sin tildes**.

**Vercel tiene límite de 60 s por función.** Por eso `futbol/ia.py` lleva
`PRESUPUESTO_S`: sin él, tres modelos con reintento tardaban minutos y morían.

**Las 58 pruebas son 44 KB de texto.** La ficha se pide suelta por
`/api/eval/ficha/<clave>`, no va en la página. En el móvil con datos importa.

**`fut_palabras` / `fut_segmento` son perezosos.** Están en todas las plantillas
pero no consultan nada hasta que alguien lee un atributo. Si los conviertes en un
dict normal, le añades una consulta a Supabase a cada pantalla de la app.

---

## Desplegar

```bash
git push origin main                        # 1. Vercel se actualiza solo
ssh -i ~/.ssh/futbolapp_vps -p 22 -o StrictHostKeyChecking=no \
    root@147.93.181.76 "bash /opt/futbolapp/redeploy.sh"    # 2. Contabo, manual
```

En Windows: `desplegar.bat`. La clave es `%USERPROFILE%\.ssh\futbolapp_vps`.

`redeploy.sh` vive en el servidor y hace `git fetch/reset --hard origin/main` **él
mismo**: publica GitHub, jamás la carpeta local. Un cambio sin `git push` no sale.

### Verificar de verdad

```bash
curl -s https://profut.org/salud            # -> {"app":"futbolapp","ok":true}
ssh -i ~/.ssh/futbolapp_vps root@147.93.181.76 \
    "git -C /opt/futbolapp/app log --oneline -1"
```

**No te fíes del `== salud ==` del guion:** hace `sleep 4` y gunicorn a veces
tarda más, así que **puede salir vacío estando todo bien**.

**Y usa `profut.org`, no `147-93-181-76.sslip.io`:** la URL vieja responde **301**
y redirige. Con `curl` sin `-L` vas a ver 301 en todo, incluido `/salud`, y parece
caído cuando no lo está.

### Base de datos

El despliegue publica **código**, no toca el esquema. Si el cambio necesita
columnas nuevas: primero el `.sql` en *Supabase → SQL Editor → Run*, y después
desplegar. Todo `sql/` es idempotente.

Para aplicarlo por consola: `python aplicar_sql.py sql/schema_vXX.sql`
(usa `SUPABASE_PAT`; la clave `service_role` NO puede hacer DDL por PostgREST).

---

## Qué NO hacer

- **No desplegar copiando archivos** (`scp`, `rsync`). El servidor se actualiza
  desde GitHub; copiar a mano lo deja desincronizado y el siguiente
  `reset --hard` se lleva lo copiado por delante.
- **No correr `crear_planes_paypal.py --crear` con `PAYPAL_ENV=live`** sin que
  André lo autorice: da de alta planes de cobro **reales**.
- **No tocar la barra de pestañas** ni el hero verde: son réplica de la app.
- **No meter secretos en el repo.** `.env` se queda fuera. (`planes_paypal.json`
  sí se versiona, a propósito: son solo los IDs de los billing plans, no
  credenciales — está explicado en el comentario del `.gitignore`.)
- **No cambiar el esquema desde el código** (crear tablas al vuelo). Migración en
  `sql/`, aplicada a mano, y luego el código.
