# -*- coding: utf-8 -*-
r"""Copia la plantilla de un entrenador a otra cuenta (esquema web, fut_*).

Copia, no mueve: el origen conserva sus jugadores y el destino recibe filas
NUEVAS con ids nuevos. A partir de ahi cada cuenta va por su lado y editar en
una no toca la otra. Si sale mal, se borran las del destino y no se ha perdido
nada del origen.

Un jugador manual no es una fila suelta: arrastra su Perfil Dinamico
(`fut_attributes`), su historico semanal (`fut_attribute_history`), su ficha
medica (`fut_medical`) y sus lesiones (`fut_injuries`). Copiar solo
`fut_manual_players` dejaria fichas en blanco, con los atributos a 50/100 y sin
evolucion — que es justo lo que hace util la app.

    .venv\Scripts\python.exe _copiar_plantilla.py            # simula
    .venv\Scripts\python.exe _copiar_plantilla.py --aplicar  # escribe
"""
import io
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(r'C:\MisApps\FutbolAppWeb\.env')
from supabase import create_client  # noqa: E402

ORIGEN = 'polansols77@gmail.com'
DESTINO = 'byronvelasco1357@gmail.com'
APLICAR = '--aplicar' in sys.argv


def main():
    sb = create_client(os.environ['SUPABASE_URL'],
                       os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])

    us = sb.table('usuarios').select('id,correo,nombre').execute().data
    def uid(correo):
        u = next((x for x in us if x.get('correo') == correo), None)
        if not u:
            raise SystemExit('No existe la cuenta %s' % correo)
        return u['id']

    o, d = uid(ORIGEN), uid(DESTINO)
    print('origen  %s  %s' % (ORIGEN, o[:8]))
    print('destino %s  %s\n' % (DESTINO, d[:8]))

    jugadores = sb.table('fut_manual_players').select('*').eq('coach_id', o)\
                  .eq('activo', True).execute().data
    if not jugadores:
        raise SystemExit('El origen no tiene jugadores manuales activos.')
    viejos = [j['id'] for j in jugadores]

    def traer(tabla):
        return sb.table(tabla).select('*').in_('manual_player_id', viejos).execute().data or []

    attrs = traer('fut_attributes')
    hist = traer('fut_attribute_history')
    medico = traer('fut_medical')
    lesiones = traer('fut_injuries')

    #  Lo que el destino ya tiene, para no duplicar si esto se lanza dos veces.
    ya = sb.table('fut_manual_players').select('nombre,dorsal').eq('coach_id', d).execute().data
    repetidos = {(x.get('nombre'), x.get('dorsal')) for x in ya}
    chocan = [j for j in jugadores if (j.get('nombre'), j.get('dorsal')) in repetidos]

    print('A copiar:')
    print('  jugadores            %d' % len(jugadores))
    print('  atributos            %d' % len(attrs))
    print('  historico semanal    %d' % len(hist))
    print('  fichas medicas       %d' % len(medico))
    print('  lesiones             %d' % len(lesiones))
    print('\nEl destino ya tiene %d jugadores manuales.' % len(ya))
    if chocan:
        print('AVISO: %d ya existen ahi por nombre y dorsal; se copiarian repetidos:' % len(chocan))
        for j in chocan[:5]:
            print('   ', j.get('nombre'), j.get('dorsal'))
        print('Abortado para no duplicar. Borra los del destino o revisa a mano.')
        return 1

    if not APLICAR:
        print('\nSIMULACION. Nada escrito. Repite con --aplicar.')
        print('Primeros 5 que se copiarian:')
        for j in jugadores[:5]:
            print('   %-22s %-18s dorsal %s' % (j.get('nombre'), j.get('posicion'), j.get('dorsal')))
        return 0

    #  Copia de seguridad de lo que el destino tiene ANTES de tocarlo.
    io.open('sql/_destino_antes.json', 'w', encoding='utf-8').write(
        json.dumps(ya, ensure_ascii=False, indent=1, default=str))

    def sin_id(fila, **cambios):
        f = {k: v for k, v in fila.items() if k != 'id'}
        f.update(cambios)
        return f

    print('\nCopiando jugadores...')
    mapa = {}
    for j in jugadores:
        nuevo = sb.table('fut_manual_players').insert(
            sin_id(j, coach_id=d, registrado_por=d)).execute().data[0]
        mapa[j['id']] = nuevo['id']
    print('   %d jugadores' % len(mapa))

    def copiar(tabla, filas, **extra):
        if not filas:
            return 0
        nuevas = [sin_id(f, manual_player_id=mapa[f['manual_player_id']], **extra)
                  for f in filas if f.get('manual_player_id') in mapa]
        for i in range(0, len(nuevas), 50):
            sb.table(tabla).insert(nuevas[i:i + 50]).execute()
        print('   %-24s %d' % (tabla, len(nuevas)))
        return len(nuevas)

    print('Copiando lo que cuelga de cada uno...')
    copiar('fut_attributes', attrs)
    copiar('fut_attribute_history', hist)
    copiar('fut_medical', medico, actualizado_por=d)
    copiar('fut_injuries', lesiones, coach_id=d, registrado_por=d)

    total = sb.table('fut_manual_players').select('id', count='exact')\
              .eq('coach_id', d).limit(1).execute().count
    print('\nHecho. El destino tiene ahora %d jugadores manuales.' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
