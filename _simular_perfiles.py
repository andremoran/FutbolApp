# -*- coding: utf-8 -*-
"""
_simular_perfiles.py — El primer día de un entrenador de cada perfil.

Las otras pruebas comprueban piezas. Esta se sienta en la silla del usuario:
crea una cuenta NUEVA desde el formulario de alta, entra por primera vez y hace
el recorrido entero —tablero, ajustes del equipo, pruebas, planificación,
asistente— comprobando en cada pantalla que lo que lee es lo SUYO y no lo de
un club de Serie A.

También mete un jugador con el código de cada equipo, para verificar lo que
pidió el CEO: que el jugador no elige nada y cae en la clasificación de su
entrenador.

    python _simular_perfiles.py

Crea cuentas *@simula.profoot y las borra al terminar.
"""
import sys
from datetime import date

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import app as aplicacion                                        # noqa: E402
from futbol import db                                           # noqa: E402
from futbol import ia                                           # noqa: E402
from futbol import microciclo_modelos as modelos                # noqa: E402
from futbol import segmentos as seg                             # noqa: E402
from usuarios import hash_password                              # noqa: E402

VERDE, ROJO, AZUL, GRIS, FIN = ('\033[92m', '\033[91m', '\033[96m',
                                '\033[90m', '\033[0m')
DOMINIO = 'simula.profoot'
CLAVE = 'Simulacion2026'

_ok = _mal = 0
_creados = []


def comprobar(texto, condicion, detalle=''):
    global _ok, _mal
    if condicion:
        _ok += 1
        print(f'{VERDE}  ✓{FIN} {texto}' + (f' {GRIS}{detalle}{FIN}' if detalle else ''))
    else:
        _mal += 1
        print(f'{ROJO}  ✗ {texto}  {detalle}{FIN}')
    return bool(condicion)


def _borrar_si_existe(correo):
    fila = db.one('usuarios', 'limpiar previa', correo=correo)
    if fila:
        db.delete('usuarios', 'limpiar previa', id=fila['id'])


# ═══════════════════════════════════════════════════════════════════════════
#  EL ALTA, TAL Y COMO LA HACE UNA PERSONA
# ═══════════════════════════════════════════════════════════════════════════
def dar_de_alta(segmento):
    """Rellena el formulario de registro de verdad y devuelve (cliente, id)."""
    correo = f'coach-{segmento}@{DOMINIO}'
    _borrar_si_existe(correo)

    c = aplicacion.app.test_client()
    c.get(f'/registro?rol=entrenador&segmento={segmento}')
    with c.session_transaction() as s:
        token = s.get('_csrf')

    r = c.post('/signup', data={
        '_csrf': token, 'role': 'especialista', 'plan': 'free',
        'name': f'Entrenador {segmento}', 'correo': correo,
        'password': CLAVE, 'gender': 'male', 'birth_year': '1988',
        'segmento': segmento,
    }, follow_redirects=False)

    fila = db.one('usuarios', 'alta simulada', correo=correo)
    comprobar(f'[{segmento}] El alta se completa desde el formulario',
              r.status_code in (301, 302) and bool(fila), f'HTTP {r.status_code}')
    if not fila:
        return None, None

    _creados.append(fila['id'])
    #  Pro para poder ver la planificación semanal, que es donde vive el modelo.
    #  Se hace por base y no comprando nada: aquí se simula la experiencia, no
    #  la pasarela de pago, que ya tiene sus propias pruebas.
    db.update('usuarios', {'tier': 'pro', 'activo': True}, 'pro simulado', id=fila['id'])
    return c, fila['id']


# ═══════════════════════════════════════════════════════════════════════════
#  EL RECORRIDO
# ═══════════════════════════════════════════════════════════════════════════
ESPERADO = {
    'colegio': {
        'lema': 'Formar jugadores, no ganar el sábado',
        'inicio': ['Arma tu grupo', 'Mide la talla de todos', 'Escribe tu semana escolar'],
        'micro': ['Semanas escolares', 'Días que abarca la semana'],
        'dias': ['S1', 'S2', 'JORNADA'],
        'bateria0': 'antropometria',
        'guia': ['Que siga jugando dentro de diez años', 'El estirón manda'],
        'ia_prohibe': ['NUNCA propongas cargas de adulto', 'sin jugar'],
    },
    'semipro': {
        'lema': 'Competir de verdad con el tiempo que hay',
        'inicio': ['Arma tu plantilla', 'Di contra qué se mide tu equipo',
                   'Escribe tu semana de trabajo'],
        'micro': ['Semanas de trabajo', 'Días entre partidos'],
        'dias': ['MD-4', 'MD-2', 'MD'],
        'bateria0': 'antropometria',
        'guia': ['Llegar a fin de temporada con la plantilla entera', 'Un solo día duro'],
        'ia_prohibe': ['NUNCA propongas doble sesión', 'UN solo día duro'],
    },
    'profesional': {
        'lema': 'Llegar al partido en el mejor estado posible',
        #  Los tres de siempre, con sus mismas palabras: el perfil profesional
        #  no cambia y esta prueba está para que siga sin cambiar.
        'inicio': ['Agregá tu primer jugador', 'Evaluá a un jugador',
                   'Programá un entrenamiento'],
        'micro': ['Microciclos', 'Días entre partidos'],
        'dias': ['MD-4', 'MD-3', 'MD-2'],
        'bateria0': 'antropometria',
        'guia': ['Rendir el día del partido', 'Dinámica de carga y contenido'],
        'ia_prohibe': [],
    },
}


def recorrer(segmento, c, uid):
    e = ESPERADO[segmento]
    print(f'\n{AZUL}   ── su primer día ──{FIN}')

    comprobar(f'[{segmento}] El equipo nace ya en su segmento',
              seg.del_entrenador(uid) == segmento, seg.del_entrenador(uid))

    # ── 1. El tablero ────────────────────────────────────────────────────────
    inicio = c.get('/coach/inicio', follow_redirects=True).get_data(as_text=True)
    comprobar(f'[{segmento}] El tablero le dice para qué sirve esto', e['lema'] in inicio)
    faltan = [p for p in e['inicio'] if p not in inicio]
    comprobar(f'[{segmento}] Y le propone SUS primeros pasos', not faltan, str(faltan))

    #  Que no se le cuelen los de otro perfil.
    ajenos = [p for otro, d in ESPERADO.items() if otro != segmento
              for p in d['inicio'] if p in inicio and p not in e['inicio']]
    comprobar(f'[{segmento}] Y ninguno de otro perfil', not ajenos, str(ajenos))

    # ── 2. Los ajustes del equipo ────────────────────────────────────────────
    editar = c.get('/coach/equipo/editar').get_data(as_text=True)
    comprobar(f'[{segmento}] En «Mi equipo» aparece marcado su perfil',
              f'data-seg="{segmento}"' in editar and 'A quién entrenas' in editar)
    comprobar(f'[{segmento}] Y se le avisa de que el código lo hereda el jugador',
              'hereda' in editar)

    # ── 3. Qué medir ─────────────────────────────────────────────────────────
    catalogo = c.get('/coach/evaluaciones/catalogo').get_data(as_text=True)
    comprobar(f'[{segmento}] El catálogo le dice por dónde empezar',
              'Por dónde empezar' in catalogo)
    bateria = seg.bateria(segmento)
    comprobar(f'[{segmento}] Con las {len(bateria)} pruebas de su batería',
              all(f'clave={cl}' in catalogo or cl in catalogo for cl in bateria))
    comprobar(f'[{segmento}] Y la primera es la que le hace falta antes que nada',
              bateria[0] == e['bateria0'], bateria[0])

    hay_aviso = 'Necesita material de laboratorio' in catalogo
    comprobar(f'[{segmento}] Aviso de material de laboratorio: '
              f"{'sí' if segmento != 'profesional' else 'no hace falta'}",
              hay_aviso == (segmento != 'profesional'))

    # ── 4. La planificación ──────────────────────────────────────────────────
    micros = c.get('/coach/microciclos').get_data(as_text=True)
    faltan = [x for x in e['micro'] if x not in micros]
    comprobar(f'[{segmento}] La planificación le habla en su idioma', not faltan, str(faltan))

    with c.session_transaction() as s:
        token = s.get('_csrf')
    r = c.open('/api/microciclo/nuevo', method='POST', json={'rotacion': 7},
               headers={'X-CSRFToken': token})
    datos = r.get_json() or {}
    comprobar(f'[{segmento}] Puede crear su semana en un toque',
              r.status_code == 200 and datos.get('id'), datos.get('error', ''))

    if datos.get('id'):
        fila = db.one('fut_microcycles', 'sim micro', id=datos['id']) or {}
        dias = [d.get('md') for d in (fila.get('dias') or [])]
        faltan = [d for d in e['dias'] if d not in dias]
        comprobar(f'[{segmento}] Y nace con los días de SU modelo', not faltan,
                  ' · '.join(dias))
        comprobar(f'[{segmento}] La semana recuerda con qué modelo se escribió',
                  fila.get('segmento') == segmento)

    guia = c.get('/coach/microciclos/guia').get_data(as_text=True)
    faltan = [x for x in e['guia'] if x not in guia]
    comprobar(f'[{segmento}] La guía trae sus objetivos y sus principios',
              not faltan, str(faltan))

    # ── 5. El asistente ──────────────────────────────────────────────────────
    #  Se mira el PROMPT, no la respuesta: la respuesta la escribe Gemini y
    #  cambia cada vez. Lo que tiene que ser siempre igual es lo que se le pide.
    class _U:
        id, role, name = uid, 'especialista', 'Simulado'
        is_authenticated = True

    prompt = ia._prompt(_U(), '¿Cómo mejoro la resistencia del equipo?')
    comprobar(f'[{segmento}] El asistente sabe a quién le habla',
              seg.meta(segmento)['etiqueta'][:20] in prompt
              or seg.guia_ia(segmento)['quien'][:40] in prompt)
    faltan = [x for x in e['ia_prohibe'] if x not in prompt]
    comprobar(f'[{segmento}] Y tiene prohibido el consejo que no le sirve',
              not faltan, str(faltan))

    return db.one('usuarios', 'sim coach', id=uid) or {}


def entra_un_jugador(segmento, coach):
    """El jugador no elige: cae donde esté su entrenador."""
    correo = f'jugador-{segmento}@{DOMINIO}'
    _borrar_si_existe(correo)

    c = aplicacion.app.test_client()
    c.get('/registro?rol=jugador')
    with c.session_transaction() as s:
        token = s.get('_csrf')
    c.post('/signup', data={
        '_csrf': token, 'role': 'paciente', 'plan': 'free',
        'name': f'Jugador {segmento}', 'correo': correo, 'password': CLAVE,
        'gender': 'male', 'birth_year': '2011',
        'codigo_vinculacion': coach.get('codigo_equipo') or '',
    }, follow_redirects=False)

    fila = db.one('usuarios', 'jugador simulado', correo=correo)
    if not comprobar(f'[{segmento}] Un jugador entra con el código del equipo', bool(fila)):
        return
    _creados.append(fila['id'])

    class _J:
        id, role, name = fila['id'], 'paciente', 'Simulado'
        is_authenticated = True

    comprobar(f'[{segmento}] Y hereda la clasificación de su entrenador, sin elegir nada',
              seg.del_usuario(_J()) == segmento, seg.del_usuario(_J()))


def limpiar():
    print(f'\n{GRIS}Borrando las cuentas simuladas…{FIN}')
    for uid in _creados:
        db.delete('usuarios', 'limpiar simulacion', id=uid)


def main():
    aplicacion.app.config['SESSION_COOKIE_SECURE'] = False
    print('\n════ EL PRIMER DÍA DE CADA PERFIL ════')

    try:
        for segmento in ('colegio', 'semipro', 'profesional'):
            meta = seg.meta(segmento)
            print(f"\n{AZUL}▸ {meta['etiqueta'].upper()}{FIN}  {GRIS}{meta['lema']}{FIN}")
            c, uid = dar_de_alta(segmento)
            if not c:
                continue
            coach = recorrer(segmento, c, uid)
            entra_un_jugador(segmento, coach)
    finally:
        limpiar()

    print('\n' + '═' * 62)
    color = ROJO if _mal else VERDE
    print(f'{color}{_ok} comprobaciones bien · {_mal} con problema{FIN}\n')
    return 1 if _mal else 0


if __name__ == '__main__':
    raise SystemExit(main())
