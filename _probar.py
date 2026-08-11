# -*- coding: utf-8 -*-
"""
_probar.py — Recorre TODA la app con los cinco roles.

No es un test unitario: es el recorrido que haría una persona abriendo cada
pantalla. Sirve para pillar la plantilla que se rompió al renombrar una
variable, que es el fallo que más veces se cuela.

    python _probar.py             # recorre todo
    python _probar.py --limpiar   # borra las cuentas de prueba al terminar

Las cuentas de prueba llevan el correo *@prueba.profoot y son las mismas entre
ejecuciones, así que no se llena la base de basura.
"""
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import app as aplicacion  # noqa: E402
from futbol import db  # noqa: E402
from usuarios import hash_password  # noqa: E402

DOMINIO = 'prueba.profoot'
CLAVE = 'PruebaProfoot2026'

CUENTAS = {
    'jugador':     dict(correo=f'jugador@{DOMINIO}',     rol='paciente',
                        tier='free', nombre='Prueba Jugador'),
    'jugador_pro': dict(correo=f'jugadorpro@{DOMINIO}',  rol='paciente',
                        tier='pro',  nombre='Prueba Jugador Pro'),
    'entrenador':  dict(correo=f'entrenador@{DOMINIO}',  rol='especialista',
                        tier='free', nombre='Prueba Entrenador'),
    'coach_pro':   dict(correo=f'coachpro@{DOMINIO}',    rol='especialista',
                        tier='pro',  nombre='Prueba Coach Pro'),
    'asistente':   dict(correo=f'asistente@{DOMINIO}',   rol='especialista',
                        tier='free', nombre='Prueba Asistente'),
    'admin':       dict(correo=f'admin@{DOMINIO}',       rol='especialista',
                        tier='pro',  nombre='Prueba Admin', es_admin=True),
}

VERDE, ROJO, AMARILLO, GRIS, FIN = '\033[92m', '\033[91m', '\033[93m', '\033[90m', '\033[0m'


def preparar():
    """Crea (o pone al día) las cinco cuentas y las engancha entre sí."""
    ids = {}
    for clave, datos in CUENTAS.items():
        fila = db.one('usuarios', 'prueba', correo=datos['correo'])
        campos = {
            'nombre': datos['nombre'], 'correo': datos['correo'],
            'rol': datos['rol'], 'tier': datos['tier'],
            'es_admin': datos.get('es_admin', False),
            'activo': datos['tier'] == 'pro', 'bloqueado': False,
            'anio_nacimiento': 2008,
        }
        if fila:
            db.update('usuarios', campos, 'prueba up', id=fila['id'])
            ids[clave] = fila['id']
        else:
            campos['password'] = hash_password(CLAVE)
            if datos['rol'] == 'especialista':
                from auth import _nuevo_codigo_equipo
                campos['codigo_equipo'] = _nuevo_codigo_equipo()
            nuevo = db.insert('usuarios', campos, 'prueba alta')
            if not nuevo:
                raise SystemExit(f'No se pudo crear la cuenta de prueba {clave}')
            ids[clave] = nuevo['id']

    # El asistente entra al cuerpo técnico del coach de prueba.
    if not db.one('fut_team_coaches', 'asist prueba', coach_id=ids['asistente']):
        db.insert('fut_team_coaches', {
            'principal_id': ids['coach_pro'], 'coach_id': ids['asistente'],
            'rol': 'asistente', 'estado': 'activo'}, 'asist prueba')

    # Los jugadores de prueba van a la plantilla del coach de prueba.
    for jugador in ('jugador', 'jugador_pro'):
        if not db.one('fut_plantilla', 'vinculo', player_id=ids[jugador]):
            db.insert('fut_plantilla', {
                'coach_id': ids['coach_pro'], 'player_id': ids[jugador],
                'activo': True,
            }, 'vinculo prueba')
    return ids


def rutas_de(rol):
    """Las pantallas que le tocan a cada rol, con lo que se espera de cada una."""
    jugador = [
        '/app', '/inicio', '/agenda', '/calendario', '/progreso',
        '/progreso/entrenos', '/progreso/metas', '/progreso/habitos',
        '/progreso/partidos', '/progreso/tests', '/ficha', '/mensajes',
        '/checkin', '/perfil', '/planes', '/evaluaciones',
        '/medico', '/unirme', '/tactica', '/canjear', '/ia',
    ]
    jugador_pro = jugador + ['/evolucion']
    coach = [
        '/app', '/coach', '/coach/plantilla', '/coach/agenda', '/coach/calendario',
        '/coach/asistencia', '/coach/partidos', '/coach/mensajes',
        '/coach/observaciones', '/coach/mental', '/coach/mental/asignar',
        '/coach/equipo/editar', '/coach/tests', '/coach/solicitudes',
        '/coach/jugadores-manuales', '/perfil', '/planes', '/coach/evaluaciones',
        '/coach/ia',
    ]
    coach_pro = coach + [
        '/coach/tactica', '/coach/tactica/pizarra',
        '/coach/planes', '/coach/evaluaciones/catalogo', '/coach/evolucion',
        '/coach/medico', '/coach/evaluaciones/nueva', '/canjear',
    ]
    if rol == 'jugador':
        return jugador
    if rol == 'jugador_pro':
        return jugador_pro
    if rol == 'entrenador':
        return coach
    if rol == 'asistente':
        # Ve y anota como el principal; lo que no toca es el cuerpo técnico.
        return [r for r in coach_pro if r != '/coach/asistentes'] + ['/unirme-equipo']
    if rol == 'coach_pro':
        return coach_pro + ['/coach/asistentes']
    return coach_pro + ['/admin/', '/admin/usuarios', '/admin/codigos',
                        '/admin/pagos', '/admin/avisos', '/admin/ajustes']


def entrar(cliente, correo):
    cliente.get('/entrar')
    with cliente.session_transaction() as s:
        token = s.get('_csrf')
    r = cliente.post('/login', data={'correo': correo, 'password': CLAVE, '_csrf': token},
                     follow_redirects=False)
    return r.status_code in (301, 302)


def recorrer(rol, correo):
    aplicacion.app.config['SESSION_COOKIE_SECURE'] = False
    aplicacion.app.config['TESTING'] = False       # queremos ver los 500 reales
    cliente = aplicacion.app.test_client()

    if not entrar(cliente, correo):
        print(f'{ROJO}  No se pudo entrar como {rol}{FIN}')
        return 0, 1, []

    # Qué rutas existen de verdad. Hace falta porque el manejador de 404 de la
    # app redirige a la portada: sin esto, una ruta que NO existe se vería como
    # un 200 perfecto y el recorrido daría todo por bueno.
    conocidas = {r.rule for r in aplicacion.app.url_map.iter_rules()}

    ok = fallos = 0
    problemas = []
    for ruta in rutas_de(rol):
        if ruta not in conocidas:
            fallos += 1
            problemas.append((ruta, 'no existe', 'la ruta no está registrada'))
            print(f'{ROJO}  ✗ {ruta:38s} NO EXISTE{FIN}')
            continue
        try:
            r = cliente.get(ruta, follow_redirects=True)
            cuerpo = r.get_data(as_text=True)
            destino = r.request.path
            # Un 200 que en realidad es la página de error no es un 200; y
            # acabar en otra pantalla puede ser un candado legítimo o un fallo.
            roto = (r.status_code >= 400
                    or 'Se nos cruzaron los cables' in cuerpo
                    or 'jinja2.exceptions' in cuerpo
                    or 'Traceback (most recent' in cuerpo)
            if roto:
                fallos += 1
                pista = _pista(cuerpo)
                problemas.append((ruta, r.status_code, pista))
                print(f'{ROJO}  ✗ {ruta:38s} {r.status_code}  {pista}{FIN}')
            elif destino != ruta:
                ok += 1
                print(f'{AMARILLO}  ↪{FIN} {ruta:38s} {r.status_code} '
                      f'{GRIS}→ {destino}{FIN}')
            else:
                ok += 1
                marca = f'{GRIS}({len(cuerpo) // 1024} kB){FIN}'
                print(f'{VERDE}  ✓{FIN} {ruta:38s} {r.status_code} {marca}')
        except Exception as e:
            fallos += 1
            problemas.append((ruta, 'excepción', str(e)[:160]))
            print(f'{ROJO}  ✗ {ruta:38s} EXCEPCIÓN  {str(e)[:120]}{FIN}')
    return ok, fallos, problemas


def _pista(cuerpo):
    """Saca de la página de error la línea que dice qué pasó."""
    for patron in (r'jinja2\.exceptions\.\w+: ([^\n<]{0,160})',
                   r'(?:Error|error): ([^\n<]{0,160})',
                   r'<title>([^<]{0,90})</title>'):
        m = re.search(patron, cuerpo)
        if m:
            return m.group(1).strip()
    return ''


def probar_alta():
    """El embudo de alta completo, sin sesión: rol -> plan -> formulario."""
    cliente = aplicacion.app.test_client()
    print('\n── EMBUDO DE ALTA (sin sesión) ───────────────────')
    casos = [
        ('/rol', 'Paso 1: elegir rol'),
        ('/plan?rol=jugador', 'Paso 2: plan del jugador'),
        ('/plan?rol=entrenador', 'Paso 2: plan del entrenador'),
        ('/registro?rol=jugador&plan=free', 'Paso 3: alta gratis'),
        ('/registro?rol=entrenador&plan=pro', 'Paso 3: alta Pro'),
        ('/registro?rol=entrenador&plan=codigo', 'Paso 3: alta con código'),
        ('/clubes', 'Clubes: agendar llamada'),
    ]
    ok = mal = 0
    for ruta, texto in casos:
        r = cliente.get(ruta, follow_redirects=True)
        cuerpo = r.get_data(as_text=True)
        roto = (r.status_code >= 400 or 'jinja2.exceptions' in cuerpo
                or 'Se nos cruzaron los cables' in cuerpo)
        if roto:
            mal += 1
            print(f'{ROJO}  ✗ {texto:34s} {r.status_code} {_pista(cuerpo)}{FIN}')
        else:
            ok += 1
            print(f'{VERDE}  ✓{FIN} {texto:34s} {r.status_code}')
    return ok, mal


def probar_candados():
    """Que los planes gratuitos NO entren donde no deben.

    Es lo que más fácil se rompe: basta olvidar un decorador para regalar la
    IA. Aquí se comprueba a dónde acaba de verdad cada rol, no lo que dice el
    código.
    """
    aplicacion.app.config['SESSION_COOKIE_SECURE'] = False
    casos = [
        # (rol, ruta, dónde debería acabar, qué se comprueba)
        ('jugador',    '/ia',              '/ia',     'IA ABIERTA al jugador gratis (con cupo)'),
        ('jugador',    '/evolucion',       '/pro',    'Evolución cerrada al jugador gratis'),
        ('jugador',    '/admin/',          '!',       'Jugador fuera del panel'),
        ('jugador_pro', '/ia',             '/ia',     'IA abierta al jugador Pro'),
        ('jugador_pro', '/evolucion',      '/evolucion', 'Evolución abierta al jugador Pro'),
        ('jugador_pro', '/admin/usuarios', '!',       'Jugador Pro fuera del panel'),
        ('entrenador', '/coach/ia',        '/coach/ia', 'IA ABIERTA al entrenador gratis (con cupo)'),
        ('entrenador', '/coach/tactica',   '/pro',    'Táctica cerrada al entrenador gratis'),
        ('entrenador', '/coach/planes',    '/pro',    'Planes cerrados al entrenador gratis'),
        ('entrenador', '/coach/medico',    '/pro',    'Ficha médica cerrada al gratis'),
        ('entrenador', '/coach/evaluaciones', '/coach/evaluaciones',
         'Tomar pruebas SÍ está abierto al entrenador gratis'),
        ('entrenador', '/admin/',          '!',       'Entrenador fuera del panel'),
        ('coach_pro',  '/coach/ia',        '/coach/ia',   'IA abierta al Coach Pro'),
        ('coach_pro',  '/coach/planes',    '/coach/planes', 'Planes abiertos al Coach Pro'),
        ('coach_pro',  '/admin/',          '!',       'Coach Pro fuera del panel'),
        # Cerrar sesión tiene que cerrar de verdad, incluida la cookie de
        # "recordarme": en un móvil prestado es la diferencia entre salir y no.
        ('_salir',     '/app',             '/entrar', 'Tras cerrar sesión no se entra a la app'),
        ('asistente',  '/coach/plantilla', '/coach/plantilla',
         'El asistente ve la plantilla del equipo'),
        ('asistente',  '/coach/evaluaciones', '/coach/evaluaciones',
         'El asistente puede evaluar'),
        ('asistente',  '/coach/ia',        '/coach/ia',
         'El asistente hereda el Pro del equipo (IA sin cupo)'),
        ('asistente',  '/coach/asistentes', '!',
         'El asistente NO gestiona el cuerpo técnico'),
        ('coach_pro',  '/coach/asistentes', '/coach/asistentes',
         'El principal sí lo gestiona'),
        ('admin',      '/admin/',          '/admin/', 'Admin entra al panel'),
        ('admin',      '/coach/ia',        '/coach/ia',   'Admin tiene Pro'),
    ]

    print('\n── CANDADOS ──────────────────────────────────────')
    clientes, ok, mal = {}, 0, 0
    for rol, ruta, esperado, texto in casos:
        if rol not in clientes and rol != '_salir':
            c = aplicacion.app.test_client()
            if not entrar(c, CUENTAS[rol]['correo']):
                print(f'{ROJO}  no se pudo entrar como {rol}{FIN}')
                mal += 1
                continue
            clientes[rol] = c
        if rol == '_salir':
            # Se reutiliza el cliente del Coach Pro: entra, sale y se comprueba.
            c = aplicacion.app.test_client()
            entrar(c, CUENTAS['coach_pro']['correo'])
            c.get('/logout', follow_redirects=True)
            clientes[rol] = c
        r = clientes[rol].get(ruta, follow_redirects=True)
        destino = r.request.path
        # '!' = basta con que NO se quede en la ruta pedida.
        bien = (destino != ruta) if esperado == '!' else (destino == esperado)
        if bien:
            ok += 1
            print(f'{VERDE}  ✓{FIN} {texto}')
        else:
            mal += 1
            print(f'{ROJO}  ✗ {texto} — acabó en {destino}{FIN}')
    return ok, mal


def limpiar():
    for datos in CUENTAS.values():
        fila = db.one('usuarios', 'limpiar', correo=datos['correo'])
        if fila:
            db.delete('usuarios', 'limpiar', id=fila['id'])
    print('Cuentas de prueba borradas.')


def main():
    if '--limpiar' in sys.argv and len(sys.argv) == 2:
        limpiar()
        return 0

    print('Preparando cuentas de prueba…')
    preparar()

    total_ok = total_mal = 0
    todos = []
    for rol, datos in CUENTAS.items():
        print(f'\n── {rol.upper()} ──────────────────────────────────────')
        ok, mal, problemas = recorrer(rol, datos['correo'])
        total_ok += ok
        total_mal += mal
        todos += [(rol, *p) for p in problemas]

    ok_a, mal_a = probar_alta()
    total_ok += ok_a
    total_mal += mal_a

    ok_c, mal_c = probar_candados()
    total_ok += ok_c
    total_mal += mal_c

    print('\n' + '═' * 68)
    color = VERDE if not total_mal else ROJO
    print(f'{color}{total_ok} comprobaciones bien · {total_mal} con problema{FIN}')
    if todos:
        print('\nA revisar:')
        for rol, ruta, codigo, pista in todos:
            print(f'  [{rol}] {ruta} → {codigo}  {pista}')

    if '--limpiar' in sys.argv:
        limpiar()
    return 1 if total_mal else 0


if __name__ == '__main__':
    raise SystemExit(main())
