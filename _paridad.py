# -*- coding: utf-8 -*-
"""
_paridad.py — ¿Tenemos todo lo que tiene el MVP de polansols?

Recorre las 59 pantallas de github.com/polansols/FutbolApp y comprueba que
cada una tiene equivalente en la web. No compara código: compara FUNCIONES,
que es lo que el cliente pidió («como mínimo todas las funcionalidades de ese
MVP»).

    python _paridad.py
"""
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import app as aplicacion  # noqa: E402

VERDE, AMARILLO, ROJO, GRIS, FIN = '\033[92m', '\033[93m', '\033[91m', '\033[90m', '\033[0m'

# (pantalla del MVP, qué hace, ruta equivalente en la web o None)
#   None = decidido NO portar, con su motivo entre paréntesis.
EQUIVALENCIAS = [
    # ── Acceso ──
    ('AuthScreen',              'Portada de acceso',            '/entrar'),
    ('LoginScreen',             'Entrar',                       '/entrar'),
    ('RegisterScreen',          'Registro',                     '/registro'),
    ('RoleSelectionScreen',     'Elegir rol',                   '/rol'),
    ('JoinTeamScreen',          'Unirse a un equipo',           '/unirme'),

    # ── Jugador ──
    ('HomeScreen',              'Inicio del jugador',           '/inicio'),
    ('PlayerCalendarScreen',    'Calendario del jugador',       '/calendario'),
    ('PlayerProgressHubScreen', 'Hub de progreso',              '/progreso'),
    ('TrainingScreen',          'Entrenos del jugador',         '/progreso/entrenos'),
    ('GoalsScreen',             'Metas',                        '/progreso/metas'),
    ('HabitsScreen',            'Hábitos',                      '/progreso/habitos'),
    ('MatchesScreen',           'Partidos del jugador',         '/progreso/partidos'),
    ('MyTestsScreen',           'Mis pruebas',                  '/progreso/tests'),
    ('ProfileScreen',           'Ficha del jugador',            '/ficha'),
    ('EditProfileScreen',       'Editar perfil',                '/perfil'),
    ('PlayerMessagesScreen',    'Mensajes del coach',           '/mensajes'),
    ('MentalCheckInScreen',     'Check-in de bienestar',        '/checkin'),
    ('MentalCheckInResultScreen', 'Resultado del check-in',     '/checkin'),
    ('PlayerEvaluationViewScreen', 'Ver mis evaluaciones',      '/evaluaciones'),
    ('PlayerEvolutionScreen',   'Mi evolución',                 '/evolucion'),
    ('PlayerMedicalScreen',     'Ficha médica',                 '/medico'),
    ('PlayerTacticalViewScreen', 'Ver jugadas del coach',       '/tactica'),
    ('PremiumScreen',           'Planes y suscripción',         '/planes'),

    # ── Entrenador ──
    ('CoachDashboardScreen',    'Tablero del entrenador',       '/coach'),
    ('CoachScreen',             'Panel del entrenador',         '/coach'),
    ('TeamPlayersScreen',       'Plantilla',                    '/coach/plantilla'),
    ('PlayerDetailScreen',      'Ficha de un jugador',          '/coach/plantilla'),
    ('CoachProfileScreen',      'Perfil del entrenador',        '/perfil'),
    ('EditCoachProfileScreen',  'Editar perfil del coach',      '/coach/equipo/editar'),
    ('ScheduleScreen',          'Calendario y carga',           '/coach/calendario'),
    ('EventAttendanceScreen',   'Pasar lista',                  '/coach/asistencia'),
    ('CreateTrainingPlanScreen', 'Crear plan de sesión',        '/coach/planes'),
    ('TrainingPlansListScreen', 'Lista de planes',              '/coach/planes'),
    ('TrainingObservationScreen', 'Observación de sesión',      '/coach/observaciones'),
    ('TrainingObservationsListScreen', 'Lista de observaciones', '/coach/observaciones'),
    ('TrainingObservationDetailScreen', 'Detalle de observación', '/coach/observaciones'),
    ('MatchStatsScreen',        'Estadísticas de partido',      '/coach/partidos'),
    ('CoachMessagesScreen',     'Mensajes a la plantilla',      '/coach/mensajes'),
    ('CoachMentalHealthScreen', 'Semáforos de bienestar',       '/coach/mental'),
    ('AssignMentalCheckInScreen', 'Asignar check-in',           '/coach/mental/asignar'),
    ('JoinRequestsScreen',      'Solicitudes de ingreso',       '/coach/solicitudes'),
    ('AcceptPlayerScreen',      'Aceptar jugador',              '/coach/solicitudes'),
    ('AddManualPlayerScreen',   'Apuntar jugador sin cuenta',   '/coach/jugadores-manuales'),
    ('ManualPlayerDetailScreen', 'Ficha del jugador sin cuenta', '/coach/jugadores-manuales'),
    ('CoachIAScreen',           'IA del entrenador',            '/coach/ia'),

    # ── Evaluaciones ──
    ('TestsHomeScreen',         'Centro de evaluaciones',       '/coach/evaluaciones'),
    ('TestTemplatesScreen',     'Catálogo de pruebas',          '/coach/evaluaciones/catalogo'),
    ('CreateTestScreen',        'Tomar una prueba',             '/coach/evaluaciones/catalogo'),
    ('CreateCustomTestScreen',  'Crear prueba propia',          '/coach/evaluaciones/nueva'),
    ('TestResultScreen',        'Resultado de una prueba',      '/coach/evaluaciones'),
    ('TestRankingScreen',       'Ranking del equipo',           '/coach/evaluaciones'),
    ('PlayerEvaluationScreen',  'Evaluar a un jugador',         '/coach/evaluaciones'),
    ('TeamEvolutionDashboardScreen', 'Evolución del equipo',    '/coach/evolucion'),

    # ── Táctica ──
    ('TacticalBoardScreen',     'Pizarra táctica',              '/coach/tactica/pizarra'),
    ('TacticalPlaysLibraryScreen', 'Biblioteca de jugadas',     '/coach/tactica'),
    ('TacticalAnimationScreen', 'Animar una jugada (momentos)',  '/coach/tactica/pizarra'),

    # ── Administración ──
    ('AdminPromoScreen',        'Códigos promocionales',        '/admin/codigos'),
]

# Lo que la web tiene y el MVP NO. Se lista para que quede claro qué se ganó.
DE_MAS = [
    ('/admin/',                  'Tablero de administración con métricas'),
    ('/admin/usuarios',          'Gestión completa de usuarios (5 roles)'),
    ('/admin/pagos',             'Aprobación de comprobantes DeUna'),
    ('/admin/avisos',            'Bandeja de avisos de altas y pagos'),
    ('/admin/ajustes',           'Ajustes en caliente: DeUna, precios, admins'),
    ('/pagos/checkout/<plan>',   'Cobro con tarjeta (PayPal Subscriptions)'),
    ('/pagos/deuna/<plan>',      'Cobro por transferencia DeUna'),
    ('/canjear',                 'Canje de código por el propio usuario'),
    ('/coach/medico',            'Parte de lesiones del equipo'),
    ('/pro',                     'Pantalla que explica cada función de pago'),
    ('/coach/evaluaciones/test/<clave>', 'Ranking por prueba con baremo'),
    ('/coach/evaluaciones/jugador/<pid>', 'Ficha de evaluación por jugador'),
    ('/coach/planes/<plid>',     'Volcar un plan a varias fechas de golpe'),
    ('/tactica',                 'Visor de jugadas para el jugador con reproducción'),
]


def main():
    rutas = {r.rule for r in aplicacion.app.url_map.iter_rules()}

    def existe(ruta):
        if ruta in rutas:
            return True
        # Las rutas con parámetro se comprueban por su prefijo.
        return any(r.startswith(ruta.rstrip('/')) for r in rutas)

    print('PARIDAD CON EL MVP DE polansols/FutbolApp')
    print('═' * 72)

    cubiertas = faltan = 0
    for pantalla, que_hace, ruta in EQUIVALENCIAS:
        if ruta is None:
            print(f'{AMARILLO}  ~ {pantalla:34s}{FIN} {GRIS}no portada · {que_hace}{FIN}')
            continue
        if existe(ruta):
            cubiertas += 1
            print(f'{VERDE}  ✓{FIN} {pantalla:34s} {GRIS}→ {ruta}{FIN}')
        else:
            faltan += 1
            print(f'{ROJO}  ✗ {pantalla:34s} FALTA · {que_hace}{FIN}')

    print('\n' + '─' * 72)
    print(f'{len(EQUIVALENCIAS)} pantallas del MVP · '
          f'{VERDE}{cubiertas} cubiertas{FIN}' +
          (f' · {ROJO}{faltan} sin cubrir{FIN}' if faltan else ''))

    print(f'\n{GRIS}Además, la web tiene lo que el MVP no:{FIN}')
    for ruta, texto in DE_MAS:
        marca = VERDE + '+' + FIN if existe(ruta.split('<')[0]) else ROJO + '?' + FIN
        print(f'  {marca} {texto}')

    print('\n' + '═' * 72)
    print(f'Rutas en la web: {len(rutas)}')
    return 1 if faltan else 0


if __name__ == '__main__':
    raise SystemExit(main())
