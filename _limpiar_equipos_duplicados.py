# -*- coding: utf-8 -*-
r"""Deja un solo equipo por entrenador en la tabla `teams` del esquema nativo.

POR QUE
-------
Al recrear el equipo, la fila anterior se quedaba en `teams`. Cuatro cuentas
acabaron con varias —una con doce—, y `CoachIAScreen.loadCoachData` pedia el
equipo con `.maybeSingle()`, que devuelve null en cuanto hay dos filas. El
early return que venia detras dejaba a la IA sin plantilla, sin planes y sin
evaluaciones: respondia "no tienes jugadores" a quien tenia diecinueve.

El codigo ya esta arreglado para aguantar varios equipos, asi que esto no es
imprescindible; es quitar la causa de raiz y que la app no tenga que adivinar
cual de los doce es el bueno.

QUE BORRA Y QUE NO
------------------
Solo equipos SIN NADA COLGANDO. Antes de borrar se cuenta cuantas filas
apuntan a ese team_id en las cinco tablas que lo referencian. Si a un
entrenador le quedan dos equipos y los dos tienen datos, no se toca ninguno y
se avisa: fusionarlos es otra decision y no se toma sola.

USO
---
    .venv\Scripts\python.exe _limpiar_equipos_duplicados.py            # simula
    .venv\Scripts\python.exe _limpiar_equipos_duplicados.py --aplicar  # borra
"""
import io
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(r'C:\MisApps\FutbolAppWeb\.env')
from supabase import create_client  # noqa: E402

APLICAR = '--aplicar' in sys.argv

#  Todo lo que apunta a un equipo. Si alguna de estas tiene filas, el equipo
#  tiene datos detras y no se borra.
REFERENCIAS = ('team_players', 'coach_training_plans', 'player_evaluations',
               'team_join_requests', 'tactical_plays')


def main():
    sb = create_client(os.environ['SUPABASE_URL'],
                       os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])

    teams = sb.table('teams').select('*').execute().data
    io.open('sql/_teams_antes.json', 'w', encoding='utf-8').write(
        json.dumps(teams, ensure_ascii=False, indent=1, default=str))
    print('Copia de los %d equipos actuales -> sql/_teams_antes.json\n' % len(teams))

    #  Se traen las referencias de una vez y se cuentan en memoria: son pocas
    #  filas y asi no se hace una consulta por equipo y tabla.
    refs = {}
    for tabla in REFERENCIAS:
        for fila in (sb.table(tabla).select('team_id').execute().data or []):
            tid = fila.get('team_id')
            if tid:
                refs.setdefault(tid, {}).setdefault(tabla, 0)
                refs[tid][tabla] += 1

    por_coach = {}
    for t in teams:
        por_coach.setdefault(t['coach_id'], []).append(t)

    a_borrar, conflictos = [], []
    for coach, suyos in por_coach.items():
        if len(suyos) < 2:
            continue
        con_datos = [t for t in suyos if refs.get(t['id'])]
        vacios = [t for t in suyos if not refs.get(t['id'])]

        if len(con_datos) > 1:
            conflictos.append((coach, con_datos))
            continue

        #  Si ninguno tiene datos se conserva el mas reciente, que es el que el
        #  entrenador estaba usando cuando dejo de crear equipos nuevos.
        if not con_datos:
            vacios.sort(key=lambda t: t.get('created_at') or t.get('creado') or '', reverse=True)
            vacios = vacios[1:]
        a_borrar += vacios

    print('Entrenadores con mas de un equipo: %d'
          % sum(1 for v in por_coach.values() if len(v) > 1))
    print('Equipos a borrar (ninguno tiene datos colgando): %d\n' % len(a_borrar))
    for t in a_borrar:
        print('   %-28s %s  coach %s' % ((t.get('name') or '?')[:28], t['id'][:8],
                                         t['coach_id'][:8]))

    if conflictos:
        print('\nNO se tocan, tienen datos los dos (fusionarlos es otra decision):')
        for coach, ts in conflictos:
            print('   coach %s:' % coach[:8])
            for t in ts:
                detalle = ', '.join('%s=%d' % kv for kv in sorted(refs[t['id']].items()))
                print('      %-26s %s  %s' % ((t.get('name') or '?')[:26], t['id'][:8], detalle))

    if not a_borrar:
        print('\nNada que borrar.')
        return 0

    if not APLICAR:
        print('\nSIMULACION. Nada borrado. Repite con --aplicar.')
        return 0

    print('\nBorrando...')
    for t in a_borrar:
        sb.table('teams').delete().eq('id', t['id']).execute()
    quedan = sb.table('teams').select('id', count='exact').limit(1).execute().count
    print('Hecho. Quedan %d equipos (antes %d).' % (quedan, len(teams)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
