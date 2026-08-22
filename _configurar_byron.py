# -*- coding: utf-8 -*-
r"""Deja lista la cuenta de byronvelasco1357@gmail.com.

Se le copiaron 19 jugadores (ver `_copiar_plantilla.py`) pero le faltaban dos
cosas para que la cuenta funcione igual que la de origen:

  1. NO TENIA FILA EN `fut_teams`. Sin ella `contexto_equipo()` devuelve
     ('general','general') y cada marca se compara contra el baremo generico de
     respaldo en vez del de su categoria. Se le crea con **adulto / amateur**,
     elegido por el usuario.

  2. ESTABA EN PLAN GRATUITO CON 19 JUGADORES. El tope libre son 12, asi que no
     podia añadir mas desde la app, y ademas sin Pro no ve el nivel contra
     baremo, ni el ranking, ni la evolucion. Se le activa Pro.

Pro se activa con `suscripciones.activar()`, que es la funcion de la app: ajusta
`tier`, `pro_hasta`, `pro_origen`, desbloquea y suma los meses a lo que ya
tuviera. Escribir esos campos a mano seria repetir su logica y arriesgarse a
dejar la fila a medias — `es_pro()` mira `tier` Y la caducidad.

    .venv\Scripts\python.exe _configurar_byron.py            # simula
    .venv\Scripts\python.exe _configurar_byron.py --aplicar  # escribe
"""
import io
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

import app as _app  # noqa: F401,E402  (inicializa el cliente de Supabase)
import suscripciones  # noqa: E402
from futbol import db  # noqa: E402
from futbol import tests_catalogo as cat  # noqa: E402

CORREO = 'byronvelasco1357@gmail.com'
EDAD, NIVEL = 'adulto', 'amateur'
MESES_PRO = 12
APLICAR = '--aplicar' in sys.argv


def main():
    u = next((x for x in db.rows('usuarios', 'buscar')
              if x.get('correo') == CORREO), None)
    if not u:
        raise SystemExit('No existe la cuenta %s' % CORREO)
    uid = u['id']

    equipo = db.one('fut_teams', 'equipo', coach_id=uid)
    plantilla = db.tamano_plantilla(uid)
    edad_ahora, nivel_ahora = ('general', 'general')
    if equipo:
        edad_ahora = equipo.get('categoria_edad') or 'general'
        nivel_ahora = equipo.get('nivel') or 'general'

    et_edad = dict(cat.CATEGORIAS_EDAD).get(EDAD, EDAD)
    et_nivel = next((e for c, e, _ in cat.NIVELES_COMPETITIVOS if c == NIVEL), NIVEL)

    print('Cuenta: %s  (%s)' % (CORREO, u.get('nombre')))
    print('  plantilla         %d jugadores' % plantilla)
    print('  tier ahora        %s' % (u.get('tier') or 'free'))
    print('  pro_hasta ahora   %s' % (u.get('pro_hasta') or '-'))
    print('  contexto ahora    %s / %s' % (edad_ahora, nivel_ahora))
    print()
    print('Se va a dejar en:')
    print('  contexto          %s / %s   (%s - %s)' % (EDAD, NIVEL, et_edad, et_nivel))
    print('  Pro               %d meses, origen admin' % MESES_PRO)
    print('  equipo            %s' % ('actualizar la fila que ya tiene'
                                      if equipo else 'crear la fila (no tenia)'))

    if not APLICAR:
        print('\nSIMULACION. Nada escrito. Repite con --aplicar.')
        return 0

    #  Copia de como estaba, por si hay que revertir.
    io.open('sql/_byron_antes.json', 'w', encoding='utf-8').write(json.dumps(
        {'usuario': u, 'equipo': equipo}, ensure_ascii=False, indent=1, default=str))

    print('\nAplicando...')
    datos = {'categoria_edad': EDAD, 'nivel': NIVEL}
    if equipo:
        db.update('fut_teams', datos, 'byron ctx', id=equipo['id'])
        print('  equipo actualizado')
    else:
        #  El nombre sale de su propio `club`; si no lo tiene, uno neutro.
        datos.update({'coach_id': uid,
                      'nombre': (u.get('club') or 'Mi equipo')[:80],
                      'codigo': db.codigo_equipo(uid),
                      'creado': datetime.now(timezone.utc).isoformat()})
        db.insert('fut_teams', datos, 'byron equipo')
        print('  equipo creado: %r' % datos['nombre'])

    hasta = suscripciones.activar(uid, meses=MESES_PRO, origen='admin', plan='pro')
    print('  Pro activo hasta %s' % (hasta.date() if hasta else '?'))

    #  Comprobacion leyendo de nuevo, no de lo que creemos haber escrito.
    from futbol.evaluaciones import contexto_equipo
    v = db.one('usuarios', 'verificar', id=uid)
    e, n = contexto_equipo(uid)
    print('\nComprobado en la base:')
    print('  contexto   %s / %s' % (e, n))
    print('  tier       %s' % v.get('tier'))
    print('  pro_hasta  %s' % v.get('pro_hasta'))
    print('  bloqueado  %s' % v.get('bloqueado'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
