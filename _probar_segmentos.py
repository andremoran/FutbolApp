# -*- coding: utf-8 -*-
"""
_probar_segmentos.py — Que los tres segmentos sean tres cosas distintas.

`_probar.py` abre pantallas y `_probar_flujos.py` hace recorridos. Esto
comprueba lo único que de verdad justifica la existencia de los segmentos: que
un entrenador de colegio y uno de club profesional, abriendo LA MISMA URL, no
reciben el mismo plan, ni las mismas palabras, ni los mismos avisos.

Si algún día alguien «simplifica» el modelo y los tres acaban dando la misma
planilla, esto se pone rojo.

    python _probar_segmentos.py

Usa la cuenta coachpro@prueba.profoot de _probar.py y la deja como estaba.
"""
import sys
from datetime import date

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import app as aplicacion                                        # noqa: E402
from _probar import CUENTAS, entrar, preparar                   # noqa: E402
from futbol import db                                           # noqa: E402
from futbol import microciclo_modelos as modelos                # noqa: E402
from futbol import microciclos as mc                            # noqa: E402
from futbol import segmentos as seg                             # noqa: E402

VERDE, ROJO, GRIS, FIN = '\033[92m', '\033[91m', '\033[90m', '\033[0m'

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


def post(c, url, datos, metodo='POST'):
    with c.session_transaction() as s:
        tok = s.get('_csrf')
    r = c.open(url, method=metodo, json=datos, headers={'X-CSRFToken': tok})
    try:
        return r.status_code, r.get_json() or {}
    except Exception:                                            # noqa: BLE001
        return r.status_code, {}


# ═══════════════════════════════════════════════════════════════════════════
#  1. LOS MODELOS, SIN TOCAR LA RED
# ═══════════════════════════════════════════════════════════════════════════
def modelos_coherentes():
    """Que cada modelo se sostenga solo: sin días huérfanos ni claves torcidas."""
    print('\n── LOS TRES MODELOS ──────────────────────────────')
    for clave, m in modelos.MODELOS.items():
        huerfanos = [(r, d) for r, dias in m['rotaciones'].items()
                     for d in dias if d not in m['dias']]
        comprobar(f'{clave}: toda rotación usa días que existen', not huerfanos,
                  str(huerfanos[:2]))

        malos = [md for md, g in m['dias'].items()
                 if g['carga'] not in m['carga_meta'] or g['fase'] not in m['fase_meta']]
        comprobar(f'{clave}: toda carga y toda fase son del vocabulario', not malos,
                  str(malos))

        #  Los principios que cita un día tienen que existir. Es el fallo fácil
        #  al añadir uno nuevo: se numera un consejo y nadie lo escribe.
        ns = {p['n'] for p in m['principios']}
        sueltos = [(md, n) for md, g in m['dias'].items()
                   for n in g.get('principios', ()) if n not in ns]
        comprobar(f'{clave}: cada día cita principios que existen', not sueltos,
                  str(sueltos[:2]))

        #  Lo que hace posible cambiar de segmento sin perder lo escrito.
        comprobar(f'{clave}: las columnas guardadas son las de siempre',
                  tuple(c for c, _ in m['campos']) == modelos.CLAVES_CAMPOS)

        comprobar(f'{clave}: tiene fuentes citadas', len(m['fuentes']) >= 1,
                  f"{len(m['fuentes'])} fuente(s), {len(m['principios'])} principios")


def modelos_distintos():
    """Que no sean el mismo plan con otro color."""
    print('\n── SON DE VERDAD DISTINTOS ───────────────────────')
    pro = modelos.MODELOS['profesional']
    semi = modelos.MODELOS['semipro']
    col = modelos.MODELOS['colegio']

    comprobar('El colegio no planifica por distancia al partido',
              not any(d.startswith('MD') for d in col['dias']),
              ' · '.join(sorted(col['dias'])[:5]))

    #  El semipro comparte notación con el profesional a propósito, pero el
    #  contenido de sus días tiene que ser otro: si coincidiera, sobraría.
    iguales = [md for md in pro['dias']
               if md in semi['dias'] and pro['dias'][md]['foco'] == semi['dias'][md]['foco']]
    comprobar('El semipro comparte notación pero no contenido', not iguales, str(iguales))

    #  La semana pesa menos según baja la disponibilidad del jugador. Es EL
    #  invariante del asunto: si algún día se rompe, es que un segmento está
    #  pidiendo más de lo que su gente puede dar.
    def peso(m):
        return sum(m['carga_meta'][m['dias'][md]['carga']]['alto']
                   for md in m['rotaciones'][7])

    comprobar('La semana pesa menos cuanto menos disponible está el jugador',
              peso(col) < peso(semi) < peso(pro),
              f'colegio {peso(col)} · semipro {peso(semi)} · profesional {peso(pro)}')

    comprobar('El semipro solo tiene UN día duro por semana',
              sum(1 for md in semi['rotaciones'][7] if semi['dias'][md]['carga'] == 'alta') == 1)

    comprobar('Las filas de la planilla se llaman distinto en cada segmento',
              len({tuple(e for _, e in m['campos']) for m in modelos.MODELOS.values()}) == 3)

    comprobar('Ninguna fuente del colegio es la del fútbol de élite',
              not ({f['titulo'] for f in col['fuentes']} & {f['titulo'] for f in pro['fuentes']}))


def avisos_del_segmento():
    """Que cada guía regañe por lo suyo — y que no regañe a una semana en blanco."""
    print('\n── LOS AVISOS ────────────────────────────────────')
    for clave, m in modelos.MODELOS.items():
        blancas = {r: m['revisar'](mc.plantilla(m, r, date.today()))
                   for r in m['rotaciones']}
        #  El profesional avisa de que sus dos días duros van seguidos ya en la
        #  plantilla de 7 y 8 días: es intencionado, invita a intercambiarlos.
        tope = 1 if clave == 'profesional' else 0
        comprobar(f'{clave}: una semana recién creada casi no da avisos',
                  all(len(a) <= tope for a in blancas.values()),
                  f'máx {max(len(a) for a in blancas.values())}')

    #  Un colegio que reparte titulares y suplentes: es EL error de este
    #  segmento y la guía tiene que decirlo con todas las letras.
    col = modelos.MODELOS['colegio']
    dias = mc.plantilla(col, 7, date.today())
    for d in dias:
        if d['md'].startswith('S'):
            d['tactico'] = 'Ensayo 11v11 con los titulares'
    avisos = col['revisar'](dias)
    comprobar('Colegio: avisa si aparecen titulares y suplentes',
              any(a['principio'] == 2 and a['nivel'] == 'alerta' for a in avisos))

    #  Un semipro con dos días duros y sin prevención: los dos fallos que le
    #  cuestan jugadores.
    semi = modelos.MODELOS['semipro']
    dias = mc.plantilla(semi, 7, date.today())
    for d in dias:
        d['tactico'] = 'Trabajo colectivo'
        if d['md'] in ('MD-4', 'MD-3'):
            d['carga'] = 'alta'
    avisos = semi['revisar'](dias)
    comprobar('Semipro: avisa de dos días duros', any(a['principio'] == 1 for a in avisos))
    comprobar('Semipro: avisa de que no hay prevención',
              any(a['principio'] == 5 and a['nivel'] == 'alerta' for a in avisos))


# ═══════════════════════════════════════════════════════════════════════════
#  2. DE PUNTA A PUNTA, CON UN ENTRENADOR DE VERDAD
# ═══════════════════════════════════════════════════════════════════════════
def flujo_en_la_web(uid):
    """El mismo entrenador cambia de segmento y la app cambia con él."""
    print('\n── EN LA WEB ─────────────────────────────────────')
    c = aplicacion.app.test_client()
    if not entrar(c, CUENTAS['coach_pro']['correo']):
        raise SystemExit('No se pudo entrar como coach_pro')

    esperado = {
        'colegio': ('Semanas escolares', 'Días que abarca la semana'),
        'semipro': ('Semanas de trabajo', 'Días entre partidos'),
        'profesional': ('Microciclos', 'Días entre partidos'),
    }

    for clave, (titulo, rotulo) in esperado.items():
        cod, r = post(c, '/api/equipo/segmento', {'segmento': clave})
        comprobar(f'Se puede pasar el equipo a {clave}', cod == 200 and r.get('ok'),
                  r.get('error', ''))
        comprobar(f'Y queda guardado en fut_teams', seg.del_entrenador(uid) == clave)

        html = c.get('/coach/microciclos').get_data(as_text=True)
        comprobar(f'{clave}: la pantalla se llama «{titulo}»', titulo in html)
        comprobar(f'{clave}: el selector dice «{rotulo}»', rotulo in html)

        guia = c.get('/coach/microciclos/guia').get_data(as_text=True)
        comprobar(f'{clave}: la guía trae los principios de su modelo',
                  modelos.MODELOS[clave]['principios'][0]['titulo'] in guia)

    #  La semana nace con la forma del segmento en el que está el equipo…
    cod, r = post(c, '/api/microciclo/nuevo', {'rotacion': 7})
    comprobar('Se crea una semana nueva', cod == 200 and r.get('id'), r.get('error', ''))
    mid = r.get('id')
    if mid:
        _creados.append(mid)
        fila = db.one('fut_microcycles', 'micro prueba', id=mid) or {}
        comprobar('La semana guarda el segmento con el que se escribió',
                  fila.get('segmento') == 'profesional', str(fila.get('segmento')))

        #  …y NO cambia de modelo cuando el equipo cambia de segmento. Es lo que
        #  evita que a un entrenador se le vacíen las semanas viejas al mover
        #  este ajuste.
        post(c, '/api/equipo/segmento', {'segmento': 'colegio'})
        fila = db.one('fut_microcycles', 'micro prueba', id=mid) or {}
        comprobar('Cambiar de segmento NO reescribe las semanas ya planificadas',
                  fila.get('segmento') == 'profesional', str(fila.get('segmento')))

        html = c.get(f'/coach/microciclos/{mid}').get_data(as_text=True)
        comprobar('Y al abrirla se lee con su modelo original', 'MD-4' in html)

        cod, r = post(c, '/api/microciclo', {
            'id': mid, 'nombre': 'Semana de prueba', 'rotacion': 7,
            'dias': [{'md': 'MD-4', 'carga': 'alta', 'fecha': date.today().isoformat(),
                      'fisico': 'Fuerza en gimnasio'}],
        })
        comprobar('Se guarda con el modelo de la semana, no con el del equipo',
                  cod == 200 and r.get('ok'), r.get('error', ''))
        fila = db.one('fut_microcycles', 'micro prueba', id=mid) or {}
        guardado = (fila.get('dias') or [{}])[0]
        comprobar('El día profesional sobrevive al guardado',
                  guardado.get('md') == 'MD-4', str(guardado.get('md')))

    #  Un valor inventado no puede entrar.
    cod, r = post(c, '/api/equipo/segmento', {'segmento': 'liga_de_barrio'})
    comprobar('Un segmento inventado se rechaza', cod == 400, r.get('error', ''))


def limpiar(uid, antes):
    print(f'\n{GRIS}Limpiando lo creado…{FIN}')
    for mid in _creados:
        db.delete('fut_microcycles', 'limpiar micro', id=mid)
    seg.guardar(uid, antes)


def main():
    ids = preparar()
    uid = ids['coach_pro']
    antes = seg.del_entrenador(uid)

    print('\n════ SEGMENTOS: colegio · semipro · profesional ════')
    modelos_coherentes()
    modelos_distintos()
    avisos_del_segmento()
    flujo_en_la_web(uid)
    limpiar(uid, antes)

    print('\n' + '═' * 62)
    color = ROJO if _mal else VERDE
    print(f'{color}{_ok} comprobaciones bien · {_mal} con problema{FIN}\n')
    return 1 if _mal else 0


if __name__ == '__main__':
    raise SystemExit(main())
