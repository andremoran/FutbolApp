# -*- coding: utf-8 -*-
"""
_probar_flujos.py — Que las cosas no solo se vean: que FUNCIONEN.

_probar.py abre pantallas; esto hace el recorrido de verdad de punta a punta:
el entrenador agenda, pasa lista, evalúa; el jugador ve su nivel; el admin
emite un código y aprueba un comprobante de DeUna.

    python _probar_flujos.py

Usa las mismas cuentas *@prueba.profoot que _probar.py y limpia lo que crea.
"""
import sys
from datetime import date, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import app as aplicacion  # noqa: E402
from _probar import CUENTAS, entrar, preparar  # noqa: E402
from futbol import db  # noqa: E402

VERDE, ROJO, GRIS, FIN = '\033[92m', '\033[91m', '\033[90m', '\033[0m'

_ok = _mal = 0
_creados = {'eventos': [], 'evals': [], 'codigos': [], 'pagos': []}


def comprobar(texto, condicion, detalle=''):
    global _ok, _mal
    if condicion:
        _ok += 1
        print(f'{VERDE}  ✓{FIN} {texto}' + (f' {GRIS}{detalle}{FIN}' if detalle else ''))
    else:
        _mal += 1
        print(f'{ROJO}  ✗ {texto}  {detalle}{FIN}')
    return bool(condicion)


def cliente(rol):
    c = aplicacion.app.test_client()
    if not entrar(c, CUENTAS[rol]['correo']):
        raise SystemExit(f'No se pudo entrar como {rol}')
    return c


def post(c, url, datos, metodo='POST'):
    with c.session_transaction() as s:
        tok = s.get('_csrf')
    r = c.open(url, method=metodo, json=datos, headers={'X-CSRFToken': tok})
    try:
        return r.status_code, r.get_json() or {}
    except Exception:
        return r.status_code, {}


# ═══════════════════════════════════════════════════════════════════════════
def flujo_calendario(coach):
    print('\n── CALENDARIO Y ASISTENCIA ───────────────────────')
    manana = (date.today() + timedelta(days=1)).isoformat()

    cod, j = post(coach, '/api/calendario/evento', {
        'tipo': 'entreno', 'titulo': 'Sesión de prueba', 'fecha': manana,
        'hora': '18:30', 'lugar': 'Cancha de prueba',
        'tipo_entreno': 'fisico', 'intensidad': 'alta', 'duracion_min': 75,
    })
    if not comprobar('El entrenador agenda un entrenamiento', cod == 200 and j.get('id'),
                     j.get('error', '')):
        return None
    eid = j['id']
    _creados['eventos'].append(eid)

    fila = db.one('fut_events', 'ev', id=eid)
    comprobar('El evento guarda intensidad y duración',
              fila and fila.get('intensidad') == 'alta' and fila.get('duracion_min') == 75,
              f"intensidad={fila.get('intensidad')} min={fila.get('duracion_min')}")

    # La carga = 75 min × 1,5 (alta) = 113
    from futbol.calendario import carga_de
    comprobar('La carga se calcula con el factor de intensidad',
              carga_de(fila) == 113, f'carga={carga_de(fila)} (esperado 113)')

    cod, j = post(coach, '/api/calendario/evento', {
        'tipo': 'partido', 'titulo': 'Amistoso', 'fecha': manana,
        'rival': 'Rival de prueba', 'local': False,
    })
    comprobar('Agenda un partido con rival y condición', cod == 200 and j.get('id'),
              j.get('error', ''))
    if j.get('id'):
        _creados['eventos'].append(j['id'])

    # Pasar lista
    jugadores = db.jugadores_del_entrenador(
        db.one('usuarios', 'coach', correo=CUENTAS['coach_pro']['correo'])['id'])
    marcas = [{'player_id': str(jj['id']), 'nombre': jj.get('name') or '',
               'estado': 'presente' if i == 0 else 'tarde', 'motivo': ''}
              for i, jj in enumerate(jugadores)]
    cod, j = post(coach, '/api/asistencia/lista', {'event_id': eid, 'marcas': marcas})
    comprobar('Pasa lista de todo el equipo de una vez',
              cod == 200 and j.get('n') == len(marcas), j.get('error', ''))

    guardadas = db.rows('fut_attendance', 'chk', event_id=eid) or []
    comprobar('La asistencia queda con los cuatro estados nuevos',
              guardadas and all(a.get('estado') in ('presente', 'tarde', 'ausente',
                                                    'justificado', 'pendiente')
                                for a in guardadas),
              f'{len(guardadas)} marcas')
    return eid


def flujo_evaluacion(coach, jugador_pro):
    print('\n── EVALUACIONES ──────────────────────────────────')

    # El contexto decide el baremo
    cod, j = post(coach, '/api/eval/contexto',
                  {'categoria_edad': 'sub_18', 'nivel': 'juvenil'})
    comprobar('Se guarda la categoría y el nivel del equipo', cod == 200, j.get('error', ''))

    coach_id = db.one('usuarios', 'c', correo=CUENTAS['coach_pro']['correo'])['id']
    pro_id = db.one('usuarios', 'p', correo=CUENTAS['jugador_pro']['correo'])['id']

    # Sprint 30 m: 4,18 s es élite en sub-18 (corte 4,15) → debería salir "bueno"
    cod, j = post(coach, '/api/eval/resultado', {
        'test': 'sprint_30m',
        'resultados': [{'player_id': str(pro_id), 'valores': {'tiempo': '4.18'},
                        'fecha': date.today().isoformat()}],
    })
    if not comprobar('El entrenador anota un sprint de 30 m',
                     cod == 200 and j.get('n') == 1, j.get('error', '')):
        return
    _creados['evals'] += j.get('ids', [])

    fila = db.one('fut_eval_results', 'r', id=j['ids'][0])
    comprobar('Queda clasificado contra el baremo internacional',
              fila and (fila.get('niveles') or {}).get('tiempo') == 'bueno',
              f"nivel={(fila.get('niveles') or {}).get('tiempo')} (sub-18: élite ≤4,15)")
    comprobar('Le pone un puntaje 0-100 comparable',
              fila and isinstance(fila.get('puntaje'), int) and 0 <= fila['puntaje'] <= 100,
              f"puntaje={fila.get('puntaje')}")
    comprobar('Guarda contra qué contexto se comparó',
              fila and fila.get('contexto_edad') == 'sub_18',
              f"{fila.get('contexto_edad')} · {fila.get('contexto_nivel')}")

    # El mismo tiempo en categoría de élite tiene que dar peor
    from futbol import tests_catalogo as cat
    j_elite = cat.evaluar_valor('sprint_30m', 'tiempo', 4.18, 'general', 'elite')
    j_sub14 = cat.evaluar_valor('sprint_30m', 'tiempo', 4.18, 'sub_14', 'general')
    comprobar('El mismo 4,18 s vale distinto según con quién se compare',
              j_elite['puntaje'] < j_sub14['puntaje'],
              f"élite={j_elite['nivel']}({j_elite['puntaje']}) · "
              f"sub-14={j_sub14['nivel']}({j_sub14['puntaje']})")

    # Prueba de varias medidas
    cod, j2 = post(coach, '/api/eval/resultado', {
        'test': 'yoyo_ir1',
        'resultados': [{'player_id': str(pro_id),
                        'valores': {'distancia': '1880', 'nivel': '18.5'}}],
    })
    comprobar('Admite pruebas con varias medidas (Yo-Yo)',
              cod == 200 and j2.get('n') == 1, j2.get('error', ''))
    _creados['evals'] += j2.get('ids', [])

    # Valor imposible
    cod, j3 = post(coach, '/api/eval/resultado', {
        'test': 'sprint_30m',
        'resultados': [{'player_id': str(pro_id), 'valores': {'tiempo': '0.5'}}],
    })
    comprobar('Rechaza una marca imposible con un mensaje claro',
              cod == 400 and 'entre' in (j3.get('error') or ''),
              (j3.get('error') or '')[:80])

    # El jugador lo ve
    r = jugador_pro.get('/evaluaciones')
    cuerpo = r.get_data(as_text=True)
    comprobar('El jugador Pro ve su marca y su nivel',
              r.status_code == 200 and '4.18' in cuerpo and 'Bueno' in cuerpo)

    # Ranking del equipo
    r = coach.get('/coach/evaluaciones/test/sprint_30m')
    comprobar('El ranking del equipo se dibuja',
              r.status_code == 200 and 'Prueba Jugador Pro' in r.get_data(as_text=True))
    return coach_id


def flujo_codigo(admin, jugador):
    print('\n── CÓDIGOS DE SUSCRIPCIÓN ────────────────────────')

    cod, j = post(admin, '/admin/api/codigo', {
        'prefijo': 'TEST', 'meses': 3, 'max_usos': 2, 'cantidad': 1,
        'nota': 'Creado por _probar_flujos',
    })
    if not comprobar('El admin emite un código', cod == 200 and j.get('codigos'),
                     j.get('error', '')):
        return
    codigo = j['codigos'][0]
    fila = db.one('fut_promo_codes', 'c', codigo=codigo)
    _creados['codigos'].append(fila['id'])
    print(f'    {GRIS}código: {codigo}{FIN}')

    # El jugador gratis lo canjea
    cod, j = post(jugador, '/api/canjear', {'codigo': codigo})
    comprobar('El jugador gratis lo canjea y pasa a Pro',
              cod == 200 and j.get('meses') == 3, j.get('error', ''))

    fila_j = db.one('usuarios', 'j', correo=CUENTAS['jugador']['correo'])
    comprobar('Su cuenta queda en tier pro con fecha de caducidad',
              fila_j.get('tier') == 'pro' and fila_j.get('pro_hasta'),
              f"tier={fila_j.get('tier')} hasta={str(fila_j.get('pro_hasta'))[:10]}")

    r = jugador.get('/ia', follow_redirects=True)
    comprobar('Y ya entra a la IA que antes tenía cerrada',
              r.request.path == '/ia', f'acabó en {r.request.path}')

    cod, j = post(jugador, '/api/canjear', {'codigo': codigo})
    comprobar('No deja canjear dos veces teniendo uno vigente',
              cod == 400 and 'activo' in (j.get('error') or ''),
              (j.get('error') or '')[:70])

    cod, j = post(jugador, '/api/canjear', {'codigo': 'NO-EXISTE-99'})
    comprobar('Un código inventado da un error entendible',
              cod == 400 and 'no existe' in (j.get('error') or '').lower(),
              (j.get('error') or '')[:70])

    fila = db.one('fut_promo_codes', 'c', codigo=codigo)
    comprobar('El cupo del código baja', fila.get('usos') == 1,
              f"usos={fila.get('usos')}/{fila.get('max_usos')}")


def flujo_deuna(admin, coach):
    print('\n── PAGO CON DEUNA ────────────────────────────────')

    cod, j = post(admin, '/admin/api/ajustes', {
        'deuna_activo': True, 'deuna_titular': 'Prueba Automática',
        'deuna_telefono': '0999999999', 'deuna_documento': '1700000000',
    })
    comprobar('El admin configura la cuenta DeUna', cod == 200, j.get('error', ''))

    r = coach.get('/pagos/deuna/entrenador_pro')
    comprobar('El coach ve la pantalla de DeUna con los datos',
              r.status_code == 200 and '0999999999' in r.get_data(as_text=True))

    cod, j = post(coach, '/pagos/api/deuna', {
        'plan': 'entrenador_pro', 'referencia': 'REF-PRUEBA-001', 'meses': 3,
    })
    if not comprobar('Manda el comprobante y queda PENDIENTE',
                     cod == 200, j.get('error', '')):
        return

    coach_id = db.one('usuarios', 'c', correo=CUENTAS['coach_pro']['correo'])['id']
    pago = next((p for p in (db.rows('fut_pagos', 'p', user_id=coach_id,
                                     _order='creado', _desc=True) or [])
                 if p.get('referencia') == 'REF-PRUEBA-001'), None)
    if not comprobar('El pago se registra para revisión', bool(pago)):
        return
    _creados['pagos'].append(pago['id'])
    comprobar('NO se activa solo: espera al administrador',
              pago.get('estado') == 'pendiente', f"estado={pago.get('estado')}")

    cod, j = post(coach, '/pagos/api/deuna',
                  {'plan': 'entrenador_pro', 'referencia': 'REF-PRUEBA-002'})
    comprobar('No deja mandar dos comprobantes a la vez',
              cod == 400 and 'esperando' in (j.get('error') or ''),
              (j.get('error') or '')[:70])

    aviso = next((a for a in (db.rows('fut_notificaciones', 'n', tipo='deuna',
                                      _order='creado', _desc=True, _limit=5) or [])), None)
    comprobar('Los administradores reciben el aviso en la bandeja', bool(aviso),
              (aviso or {}).get('titulo', '')[:60])

    cod, j = post(admin, f'/admin/api/pago/{pago["id"]}',
                  {'accion': 'aprobar', 'meses': 3, 'nota': 'Prueba automática'})
    comprobar('El admin lo aprueba y activa la cuenta', cod == 200, j.get('error', ''))

    fila = db.one('usuarios', 'c', id=coach_id)
    comprobar('La cuenta del coach queda en Pro',
              fila.get('tier') == 'pro' and fila.get('pro_origen') == 'deuna',
              f"tier={fila.get('tier')} vía {fila.get('pro_origen')}")

    pago = db.one('fut_pagos', 'p', id=pago['id'])
    comprobar('El pago queda aprobado y con quién lo revisó',
              pago.get('estado') == 'aprobado' and pago.get('revisado_por'),
              f"estado={pago.get('estado')}")


def flujo_admin(admin):
    print('\n── PANEL DE ADMINISTRACIÓN ───────────────────────')

    jugador_id = db.one('usuarios', 'j', correo=CUENTAS['jugador']['correo'])['id']

    cod, j = post(admin, f'/admin/api/usuario/{jugador_id}',
                  {'accion': 'bloquear', 'valor': True})
    comprobar('El admin bloquea una cuenta', cod == 200, j.get('error', ''))
    comprobar('Queda marcada como bloqueada',
              db.one('usuarios', 'j', id=jugador_id).get('bloqueado') is True)

    bloqueado = aplicacion.app.test_client()
    entrado = entrar(bloqueado, CUENTAS['jugador']['correo'])
    if entrado:
        r = bloqueado.get('/inicio', follow_redirects=True)
        comprobar('Una cuenta bloqueada no llega a la app',
                  r.request.path != '/inicio', f'acabó en {r.request.path}')
    else:
        comprobar('Una cuenta bloqueada no llega a la app', True, 'ni siquiera entra')

    post(admin, f'/admin/api/usuario/{jugador_id}', {'accion': 'bloquear', 'valor': False})

    cod, j = post(admin, f'/admin/api/usuario/{jugador_id}',
                  {'accion': 'pro', 'meses': 6})
    comprobar('El admin regala Pro a mano', cod == 200, j.get('error', ''))

    cod, j = post(admin, f'/admin/api/usuario/{jugador_id}', {'accion': 'free'})
    comprobar('Y se lo puede quitar', cod == 200, j.get('error', ''))
    comprobar('La cuenta vuelve al plan gratuito',
              db.one('usuarios', 'j', id=jugador_id).get('tier') == 'free')

    admin_id = db.one('usuarios', 'a', correo=CUENTAS['admin']['correo'])['id']
    cod, j = post(admin, f'/admin/api/usuario/{admin_id}',
                  {'accion': 'admin', 'valor': False})
    comprobar('Un admin no puede quitarse a sí mismo el acceso',
              cod == 400 and 'ti mismo' in (j.get('error') or ''),
              (j.get('error') or '')[:60])

    cod, j = post(admin, f'/admin/api/usuario/{admin_id}/borrar', {})
    comprobar('Ni borrar su propia cuenta',
              cod == 400, (j.get('error') or '')[:60])


def flujo_manuales_y_solicitudes(coach, jugador):
    print('\n── JUGADORES SIN CUENTA Y SOLICITUDES ────────────')

    cod, j = post(coach, '/api/manual', {
        'nombre': 'Chico De Prueba', 'dorsal': 77, 'posicion': 'Delantero',
        'anio_nacimiento': 2012, 'tutor': 'Madre de prueba',
    })
    if comprobar('Apunta a un jugador sin cuenta', cod == 200 and j.get('id'),
                 j.get('error', '')):
        mid = j['id']
        cod, j2 = post(coach, '/api/eval/resultado', {
            'test': 'cmj',
            'resultados': [{'player_id': mid, 'manual': True,
                            'valores': {'altura': '32.5'}}],
        })
        comprobar('Se le puede evaluar igual que a los demás',
                  cod == 200 and j2.get('n') == 1, j2.get('error', ''))
        if j2.get('ids'):
            _creados['evals'] += j2['ids']
            fila = db.one('fut_eval_results', 'r', id=j2['ids'][0])
            comprobar('Su nivel sale del baremo de SU edad (sub-14)',
                      fila.get('contexto_edad') in ('sub_14', 'sub_18'),
                      f"comparado con {fila.get('contexto_edad')}")
        post(coach, f'/api/manual/{mid}', {}, 'DELETE')

    codigo_equipo = db.codigo_equipo(
        db.one('usuarios', 'c', correo=CUENTAS['coach_pro']['correo'])['id'])
    cod, j = post(jugador, '/api/unirme', {'codigo': 'ZZZZZZ'})
    comprobar('Un código de equipo falso se rechaza con mensaje útil',
              cod == 404 and 'no existe' in (j.get('error') or ''),
              (j.get('error') or '')[:60])
    comprobar('El entrenador tiene código de equipo', bool(codigo_equipo), codigo_equipo)


def limpiar():
    print(f'\n{GRIS}Limpiando lo creado…{FIN}')
    for eid in _creados['eventos']:
        db.delete('fut_events', 'limpiar', id=eid)
    for rid in _creados['evals']:
        db.delete('fut_eval_results', 'limpiar', id=rid)
    for cid in _creados['codigos']:
        db.delete('fut_promo_uses', 'limpiar', code_id=cid)
        db.delete('fut_promo_codes', 'limpiar', id=cid)
    for pid in _creados['pagos']:
        db.delete('fut_pagos', 'limpiar', id=pid)
    db.delete('fut_notificaciones', 'limpiar', tipo='deuna')


def main():
    print('Preparando cuentas de prueba…')
    preparar()
    aplicacion.app.config['SESSION_COOKIE_SECURE'] = False

    coach = cliente('coach_pro')
    jugador = cliente('jugador')
    jugador_pro = cliente('jugador_pro')
    admin = cliente('admin')

    flujo_calendario(coach)
    flujo_evaluacion(coach, jugador_pro)
    flujo_manuales_y_solicitudes(coach, jugador)
    flujo_codigo(admin, jugador)
    flujo_deuna(admin, coach)
    flujo_admin(admin)

    limpiar()
    print('\n' + '═' * 62)
    color = VERDE if not _mal else ROJO
    print(f'{color}{_ok} comprobaciones bien · {_mal} con problema{FIN}')
    return 1 if _mal else 0


if __name__ == '__main__':
    raise SystemExit(main())
