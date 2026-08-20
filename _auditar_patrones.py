# -*- coding: utf-8 -*-
"""Vigila los tres fallos que ya mordieron una vez, para que no vuelvan.

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


for comprobacion in (auditar_dueno, auditar_manuales, auditar_una_fila):
    comprobacion()

print('Auditoría de los tres patrones')
print('=' * 62)
if fallos:
    print('%d aviso(s):\n' % len(fallos))
    for x in fallos:
        print('  ·', x)
    sys.exit(1)
print('Sin avisos: ningún patrón conocido ha vuelto.')
