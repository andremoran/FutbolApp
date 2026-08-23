# -*- coding: utf-8 -*-
"""Vigila los cuatro fallos que ya mordieron una vez, para que no vuelvan.

Son fallos de los que no se ven: la pantalla no revienta, simplemente enseña
menos de lo que hay. Por eso estuvieron meses ahí y por eso conviene una
comprobación automática y no la vista.

  1. DUEÑO EQUIVOCADO. En el web, las lecturas van por `db.equipo_id(...)` —el
     equipo— y algunas escrituras iban por `current_user.id` —la persona—. Un
     asistente técnico guardaba y su trabajo no volvía a aparecer. Dos casos
     eran peores: al editar el equipo o una jugada se REESCRIBÍA el dueño, así
     que el asistente se los quedaba y el principal los perdía.

  2. JUGADORES MANUALES OLVIDADOS. `jugadores_del_entrenador()` solo devuelve a
     los que tienen cuenta. Contar la plantilla con eso da 0 en un equipo con
     diecinueve apuntados a mano. Para contar está `db.tamano_plantilla()`.

  3. UNA FILA DONDE HAY VARIAS. En la app nativa, `.maybeSingle()` sobre
     `teams` filtrando por `coach_id` devuelve null en cuanto hay dos, y el
     código de arriba lo interpretaba como «no tiene equipo». Se realimentaba:
     el tablero creaba otro equipo, y con tres ya fallaba siempre.

    .venv\\Scripts\\python.exe _auditar_patrones.py
"""
import pathlib
import re
import sys

WEB = pathlib.Path(r'C:\MisApps\FutbolAppWeb')
NATIVA = pathlib.Path(r'C:\MisApps\FutbolApp')

fallos = []


def aviso(patron, detalle):
    fallos.append('[%s] %s' % (patron, detalle))


# ═══════════════════════════════════════════════════════════════════════════
#  1. El dueño de cada fila
# ═══════════════════════════════════════════════════════════════════════════
#  `codigo_equipo` y `equipo_id` reciben el id de la PERSONA a propósito: son
#  justo quienes traducen de persona a equipo.
SE_LES_PASA_LA_PERSONA = ('db.equipo_id(', 'equipo_id(', 'db.codigo_equipo(',
                          'db.es_asistente(', 'es_asistente(',
                          'registrado_por', 'actualizado_por', 'autor',
                          'player_id', 'user_id')


def auditar_dueno():
    escrituras = re.compile(r"""['"]coach_id['"]\s*:\s*current_user\.id""")
    lecturas = re.compile(r"""coach_id\s*=\s*current_user\.id""")
    for f in sorted((WEB / 'futbol').glob('*.py')):
        for n, linea in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if escrituras.search(linea):
                aviso('dueño', '%s:%d guarda coach_id con current_user.id; '
                               'debe ser db.equipo_id(current_user.id)' % (f.name, n))
            if lecturas.search(linea):
                aviso('dueño', '%s:%d consulta por coach_id=current_user.id; '
                               'debe ser db.equipo_id(current_user.id)' % (f.name, n))

    #  Funciones que reciben el id del equipo y a las que se les estaba pasando
    #  el de la persona.
    por_equipo = ('jugadores_del_entrenador', 'pruebas_propias', 'resultados_equipo',
                  'eventos_equipo', 'tamano_plantilla', 'contexto_equipo',
                  'equipo_del_entrenador')
    for f in sorted((WEB / 'futbol').glob('*.py')):
        for n, linea in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            for fn in por_equipo:
                if re.search(re.escape(fn) + r'\(\s*current_user\.id\s*\)', linea):
                    if any(x in linea for x in SE_LES_PASA_LA_PERSONA[:5]):
                        continue
                    aviso('dueño', '%s:%d %s(current_user.id): esa función espera '
                                   'el id del EQUIPO' % (f.name, n, fn))


# ═══════════════════════════════════════════════════════════════════════════
#  2. Los jugadores sin cuenta
# ═══════════════════════════════════════════════════════════════════════════
#  Dos sitios cuentan solo a los jugadores CON CUENTA y está bien:
#
#  · `equipo.py` (pantalla de jugadores sin cuenta) lo escribe al lado de la
#    etiqueta «con cuenta», así que el número dice lo que dice.
#  · `equipo.py` (aceptar una solicitud) aplica el tope del plan gratuito
#    contando solo a los registrados, mientras que al crear uno manual sí los
#    suma. Es una incoherencia REAL y conocida, pero arreglarla vuelve el tope
#    más estricto, o sea que es una decisión de producto: la deja el usuario.
#  Se reconocen por una marca del propio codigo y no por su numero de linea:
#  un numero se queda viejo a la primera edicion y la exencion salta de sitio.
EXENTOS_MANUALES = ('n_plantilla=', 'roles.plantilla_llena')


def auditar_manuales():
    """Avisa de conteos de plantilla que se dejan fuera a los manuales.

    Solo se mira `len(...)` a secas. Sumarlos aparte —`len(a) + len(b)`— es
    correcto y no se marca; para eso se comprueba que la línea siguiente sume
    `fut_manual_players`.
    """
    patron = re.compile(r'len\(\s*(db\.)?jugadores_del_entrenador\(')
    for f in sorted((WEB / 'futbol').glob('*.py')):
        lineas = f.read_text(encoding='utf-8').splitlines()
        for n, linea in enumerate(lineas, 1):
            if not patron.search(linea):
                continue
            if f.name == 'db.py':          # es la propia tamano_plantilla()
                continue
            vecindad = ' '.join(lineas[n - 1:n + 2])
            if 'fut_manual_players' in vecindad or 'manuales' in vecindad:
                continue
            if any(m in vecindad for m in EXENTOS_MANUALES):
                continue
            aviso('manuales', '%s:%d cuenta la plantilla sin los apuntados a mano; '
                              'usa db.tamano_plantilla()' % (f.name, n))


# ═══════════════════════════════════════════════════════════════════════════
#  3. Una fila donde puede haber varias (app nativa)
# ═══════════════════════════════════════════════════════════════════════════
def auditar_una_fila():
    if not NATIVA.exists():
        return
    fuentes = (list((NATIVA / 'screens').glob('*.tsx'))
               + list((NATIVA / 'components').glob('*.tsx'))
               + list((NATIVA / 'utils').glob('*.ts')))
    for f in sorted(fuentes):
        lineas = f.read_text(encoding='utf-8', errors='replace').splitlines()
        for i, linea in enumerate(lineas):
            if "from('teams')" not in linea:
                continue
            ventana = ' '.join(lineas[i:i + 8])
            if "eq('coach_id'" not in ventana:
                continue
            if 'maybeSingle()' not in ventana and '.single()' not in ventana:
                continue
            if '.limit(1)' in ventana:
                continue
            aviso('una fila', '%s:%d pide teams por coach_id con maybeSingle() y sin '
                              'limit(1): devuelve null si el coach tiene dos equipos'
                              % (f.name, i + 1))


# ═══════════════════════════════════════════════════════════════════════════
#  4. Una fila con dos dueños posibles y uno de ellos NOT NULL
# ═══════════════════════════════════════════════════════════════════════════
#  `fut_attendance.player_id` era NOT NULL, pero pasar lista a un jugador SIN
#  CUENTA escribe ahi NULL. Fallaba siempre, y en silencio, asi que la
#  asistencia no se guardo nunca para nadie sin cuenta.
#
#  Esto NO se puede comprobar leyendo el codigo: hay que preguntarle al
#  esquema. Se ejecuta solo si hay credenciales a mano; si no, se avisa y se
#  sigue, para que la auditoria valga igual sin conexion.
def auditar_dos_duenyos():
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv(str(WEB / '.env'))
        from supabase import create_client
        sb = create_client(os.environ['SUPABASE_URL'],
                           os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])
    except Exception:
        print('  (sin credenciales: no se comprueba el esquema)')
        return

    #  PostgREST no da el esquema, asi que se prueba de la unica forma directa:
    #  se pide una fila con player_id nulo. Si la columna fuese NOT NULL, la
    #  tabla no podria tener ninguna — y las que admiten los dos tipos siempre
    #  acaban teniendo alguna en cuanto se usa con jugadores sin cuenta.
    for tabla in ('fut_attendance', 'fut_attributes', 'fut_medical',
                  'fut_eval_results', 'fut_injuries', 'fut_attribute_history',
                  'fut_match_stats'):
        try:
            sb.table(tabla).select('id').is_('player_id', 'null').limit(1).execute()
        except Exception as e:
            if 'player_id' in str(e):
                aviso('dos dueños', '%s: no admite player_id nulo, asi que no se '
                                    'puede guardar nada de un jugador sin cuenta' % tabla)


def auditar_escrituras_mudas():
    """Escrituras cuyo resultado nadie mira y que no son obligatorias.

    `db.insert/update/delete` nunca lanzan: si Supabase rechaza la operación
    devuelven None y la pantalla sigue como si nada, diciendole al entrenador
    que se guardó. Una escritura vale si se cumple UNA de estas tres:

      · lleva `obligatorio=True`, y entonces revienta y el usuario se entera;
      · alguien mira lo que devolvió y responde un error o un 404;
      · está en la lista de abajo, porque perderla de verdad no importa.

    Cualquier otra es una mentira esperando a pasar. Esta comprobación existe
    para que una escritura nueva no se cuele sin decidir a cuál de las tres
    pertenece.
    """
    import ast, glob

    #  Las que pueden fallar sin consecuencias, con el motivo al lado.
    PERDONADAS = {
        ('futbol/api.py', 'api_ia'):
            'el historial del chat es un extra; la respuesta ya está calculada',
        ('futbol/calendario.py', 'api_cal_evento'):
            'contador veces_usado, sirve para ordenar y nada más',
        ('futbol/calendario.py', 'api_plan_agendar'):
            'contador veces_usado, las sesiones ya están creadas',
        ('futbol/mental.py', 'cerrar_asignacion'):
            'se cierra después de guardar; si falla, solo se vuelve a pedir',
        ('futbol/social.py', 'mensajes'):
            'marcar leído mientras se pinta; romper la pantalla sería peor',
    }

    def es_db(n):
        f = getattr(n, 'func', None)
        return (isinstance(n, ast.Call) and isinstance(f, ast.Attribute)
                and f.attr in ('insert', 'update', 'delete')
                and isinstance(f.value, ast.Name) and f.value.id == 'db')

    for archivo in sorted(glob.glob('futbol/*.py')) + ['admin.py']:
        arbol = ast.parse(open(archivo, encoding='utf-8').read())
        duenyo = {}
        for n in ast.walk(arbol):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for l in range(n.lineno, (n.end_lineno or n.lineno) + 1):
                    duenyo[l] = n.name
        #  Una llamada que es un statement suelto = nadie mira el resultado.
        sueltas = {n.value.lineno for n in ast.walk(arbol)
                   if isinstance(n, ast.Expr) and es_db(n.value)}
        for n in ast.walk(arbol):
            if not es_db(n) or n.lineno not in sueltas:
                continue
            if 'obligatorio' in {k.arg for k in n.keywords if k.arg}:
                continue
            clave = (archivo.replace(chr(92), '/'), duenyo.get(n.lineno, '?'))
            if clave in PERDONADAS:
                continue
            aviso('escritura muda',
                  '%s:%d (%s) db.%s puede fallar sin que nadie se entere. '
                  'Ponle obligatorio=True, mira lo que devuelve, o añádela a '
                  'PERDONADAS con su motivo.'
                  % (clave[0], n.lineno, clave[1], n.func.attr))




def auditar_html_donde_va_json():
    """Que a una llamada de /api/ nunca le llegue una pantalla en HTML.

    `fetch` sigue los redirect el solo. Si el servidor contesta 302 a una ruta
    de /api/, la llamada acaba recibiendo un 200 con HTML: no se puede leer
    como JSON, el ayudante se queda con {} y —como el 200 cuenta como exito—
    da la operacion por buena. Asi es como el panel de admin llego a decir
    «Listo» con la sesion caducada, y como un 404 en la API no se notaba.

    Se prueba de verdad, levantando la app y llamando, porque el fallo no esta
    en ninguna linea concreta sino en como responden los guardias y los
    manejadores de error cuando nadie los mira.
    """
    import app as aplicacion

    casos = [
        ('sin sesion',      'POST', '/api/ia',              401),
        ('sin sesion admin','POST', '/admin/api/ajustes',   401),
        ('ruta inventada',  'POST', '/api/no_existe_nada',  404),
        ('ruta inventada',  'GET',  '/admin/api/tampoco',   404),
    ]
    with aplicacion.app.test_client() as c:
        for que, metodo, url, esperado in casos:
            r = c.open(url, method=metodo, json={} if metodo == 'POST' else None)
            tipo = (r.headers.get('Content-Type') or '').split(';')[0]
            if r.status_code in (301, 302):
                aviso('html donde va json',
                      '%s en %s responde %d y redirige a %s. Un fetch seguiria '
                      'ese salto y se quedaria con {} creyendo que todo fue bien.'
                      % (que, url, r.status_code, r.headers.get('Location')))
            elif tipo != 'application/json':
                aviso('html donde va json',
                      '%s en %s responde %s en vez de JSON.' % (que, url, tipo))
            elif r.status_code != esperado:
                aviso('html donde va json',
                      '%s en %s responde %d, se esperaba %d.'
                      % (que, url, r.status_code, esperado))

        #  Y al reves: una pantalla normal TIENE que seguir redirigiendo.
        r = c.get('/calendario')
        if r.status_code not in (301, 302):
            aviso('html donde va json',
                  'una pantalla normal (/calendario) ya no redirige al login: '
                  'responde %d. El arreglo de la API se ha comido las paginas.'
                  % r.status_code)


def auditar_contexto_ia_con_datos():
    """Que el contexto de la IA se arme cuando SI hay evaluaciones.

    Aqui hubo un fallo que estuvo escondido meses: la seccion de evaluaciones
    leia `medias_por_categoria()` como un diccionario cuando devuelve una
    lista. Solo se entra en ese trozo si hay resultados, y en la base no habia
    ninguno, asi que nunca reventaba.

    Y cuando por fin reventaba no se veia: `responder_ia()` se traga cualquier
    excepcion y contesta con el respaldo local. El entrenador no habria visto
    un error — solo una IA que de pronto deja de saber nada de sus pruebas, el
    mismo dia que apunta la primera marca.

    Por eso esto se prueba con datos INVENTADOS en memoria, sin tocar la base:
    lo que se comprueba es que el codigo aguanta el caso «hay resultados», que
    es el que no se da solo.
    """
    import futbol.ia as ia
    import futbol.evaluaciones as ev
    import futbol.db as fdb

    coach = next((u for u in fdb.rows('usuarios', 'aud usuarios')
                  if u.get('rol') == 'especialista' and fdb.equipo_id(u['id'])), None)
    if not coach:
        return

    class Falso:
        is_authenticated = True
        id = coach['id']
        role = coach.get('rol')
        name = coach.get('nombre')
        tier = coach.get('tier')
        pro_hasta = coach.get('pro_hasta')

        def is_admin(self):
            return False

    inventado = [{
        'id': 'x', 'test_clave': 'sprint_30m', 'test_nombre': 'Sprint 30m',
        'categoria': 'fisico', 'puntaje': 62, 'fecha': fdb.hoy_iso(),
        'jugador_nombre': 'Jugador de prueba', 'valores': {'time_seconds': 4.35},
        'player_id': None, 'manual_player_id': 'y', 'coach_id': coach['id'],
    }]

    reales = ev.resultados_equipo, ev.resultados_de
    ev.resultados_equipo = lambda *a, **k: list(inventado)
    ev.resultados_de = lambda *a, **k: list(inventado)
    try:
        ctx = ia._contexto_entrenador(Falso())
        if 'Sprint 30m' not in ctx:
            aviso('contexto de la IA',
                  'con evaluaciones guardadas, el contexto del entrenador no '
                  'las menciona: la IA no sabria de las pruebas de su equipo')
    except Exception as e:
        aviso('contexto de la IA',
              'el contexto del entrenador revienta cuando HAY evaluaciones '
              '(%s: %s). responder_ia() se lo traga y contesta con el respaldo, '
              'asi que el fallo no se ve.' % (type(e).__name__, e))
    finally:
        ev.resultados_equipo, ev.resultados_de = reales


for comprobacion in (auditar_dueno, auditar_manuales, auditar_una_fila,
                     auditar_dos_duenyos, auditar_escrituras_mudas,
                     auditar_html_donde_va_json, auditar_contexto_ia_con_datos):
    comprobacion()

print('Auditoría de los patrones conocidos')
print('=' * 62)
if fallos:
    print('%d aviso(s):\n' % len(fallos))
    for x in fallos:
        print('  ·', x)
    sys.exit(1)
print('Sin avisos: ningún patrón conocido ha vuelto.')
