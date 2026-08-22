# -*- coding: utf-8 -*-
"""
futbol/equipo.py — Jugadores sin cuenta y solicitudes de ingreso.

Dos huecos que dejaba el registro por código:

  1. Un chico de once años no tiene correo. El entrenador lo apunta a mano,
     lo evalúa y le pasa lista igual que a los demás; si algún día se
     registra, se le enchufa la ficha con todo el histórico.

  2. El código de equipo deja entrar a cualquiera que lo tenga. Con las
     solicitudes, el jugador pide y el entrenador acepta — que es lo que
     hace falta en cuanto el código circula por un grupo de WhatsApp.
"""
import logging
from datetime import datetime, timezone

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles

from . import bp, db

logger = logging.getLogger(__name__)

POSICIONES = ['Portero', 'Lateral derecho', 'Central', 'Lateral izquierdo',
              'Pivote', 'Interior', 'Mediapunta', 'Extremo derecho',
              'Extremo izquierdo', 'Delantero']


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _coach_o_fuera():
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.inicio'))
    return None


def _guardia_coach():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el entrenador gestiona la plantilla.'}), 403
    return None


def solicitudes_pendientes(coach_id):
    return db.rows('fut_join_requests', 'solicitudes',
                   coach_id=coach_id, estado='pendiente',
                   _order='creado', _desc=True) or []


# ═══════════════════════ CUERPO TÉCNICO ═══════════════════════
@bp.route('/coach/asistentes')
@login_required
@roles.solo_principal('asistentes')
def c_asistentes():
    """Quién más puede anotar en este equipo.

    Un asistente hace lo mismo que el principal sobre los datos del equipo
    —evalúa, mide, pasa lista, apunta lesiones— y lo que anota queda firmado
    con su nombre. Lo que NO puede es tocar la suscripción ni el propio
    cuerpo técnico: eso es del dueño del equipo.
    """
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    cuerpo = db.cuerpo_tecnico(uid)
    pendientes = [s for s in solicitudes_pendientes(uid)
                  if s.get('tipo') == 'asistente']
    if pendientes:
        ids = [s['player_id'] for s in pendientes]
        personas = db.q(
            lambda: db.sb().table('usuarios').select('*').in_('id', ids)
            .execute().data or [], [], 'aspirantes')
        por_id = {p['id']: p for p in personas}
        for s in pendientes:
            s['_persona'] = por_id.get(s.get('player_id'), {})
            s['_fecha'] = db.parse_fecha(s.get('creado'))

    return render_template('c_asistentes.html',
                           tab_activa='equipo', hide_tabbar=True,
                           cuerpo=cuerpo,
                           asistentes=[c for c in cuerpo if c['rol'] == 'asistente'],
                           pendientes=pendientes,
                           codigo=db.codigo_equipo(uid),
                           es_pro=roles.es_pro(current_user))


@bp.route('/api/asistente/<aid>', methods=['DELETE'])
@login_required
def api_asistente_quitar(aid):
    error = _guardia_coach()
    if error:
        return error
    if roles.es_asistente(current_user):
        return jsonify({'error': 'Solo el entrenador principal gestiona el '
                                 'cuerpo técnico.'}), 403

    uid = db.equipo_id(current_user.id)
    fila = db.one('fut_team_coaches', 'asistente', coach_id=aid, principal_id=uid)
    if not fila:
        return jsonify({'error': 'Esa persona no está en tu cuerpo técnico.'}), 404

    # Se marca como retirado en vez de borrar: lo que anotó sigue firmado con
    # su nombre y hay que poder saber quién era.
    db.update('fut_team_coaches',
              {'estado': 'retirado', 'retirado': _ahora()}, 'quitar asist',
              id=fila['id'], obligatorio=True)
    return jsonify({'ok': True, 'mensaje': 'Fuera del cuerpo técnico. Lo que '
                                           'anotó se conserva con su firma.'})


# ═══════════════════════ JUGADORES SIN CUENTA ═══════════════════════
@bp.route('/coach/jugadores-manuales')
@login_required
def c_manuales():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    lista = db.rows('fut_manual_players', 'manuales', coach_id=uid,
                    _order='nombre') or []
    activos = [m for m in lista if m.get('activo')]

    # Cuántas evaluaciones tiene cada uno: sin esto no se sabe a quién falta medir.
    conteo = {}
    for r in (db.rows('fut_eval_results', 'evals manual', coach_id=uid) or []):
        mid = r.get('manual_player_id')
        if mid:
            conteo[str(mid)] = conteo.get(str(mid), 0) + 1
    for m in lista:
        m['_evals'] = conteo.get(str(m['id']), 0)
        m['_alta'] = db.parse_fecha(m.get('creado'))
        #  Se calcula al pintar, no se guarda: una edad guardada envejece mal.
        m['_edad'] = db.edad_de(m.get('fecha_nacimiento'), m.get('anio_nacimiento'))

    #  Con `?editar=<id>` el mismo formulario sirve para MODIFICAR a uno que ya
    #  existe. La API (`POST /api/manual`) ya sabia actualizar cuando le llega
    #  un `id`, pero ninguna pantalla se lo mandaba: los datos de un jugador
    #  sin cuenta no se podian corregir desde el web, solo archivarlo y volver
    #  a crearlo —perdiendo su Perfil Dinamico y su historico—.
    editando = None
    mid = request.args.get('editar')
    if mid:
        editando = db.one('fut_manual_players', 'editar manual', id=mid, coach_id=uid)
        if not editando:
            abort(404)

    return render_template('c_manuales.html',
                           tab_activa='equipo', hide_tabbar=True,
                           editando=editando,
                           manuales=activos,
                           archivados=[m for m in lista if not m.get('activo')],
                           posiciones=POSICIONES,
                           aptitudes=db.APTITUDES,
                           niveles_fatiga=db.NIVELES_FATIGA,
                           n_plantilla=len(db.jugadores_del_entrenador(uid)))


#  Topes de cada campo médico. Las fechas y los números se validan aparte:
#  una fecha mal escrita tiene que quedar vacía, no reventar el alta entera.
_TOPES_MEDICOS = {
    'grupo_sanguineo': 10, 'seguro': 120, 'alergias': 600, 'condiciones': 800,
    'medicacion': 600, 'contacto_nombre': 120, 'contacto_parentesco': 60,
    'contacto_tel': 30, 'cirugias': 600,
    'notas_medico': 800, 'notas_fisio': 800, 'notas_entrenador': 800,
}
#  `vacunas`, `antecedentes_personales` y `antecedentes_familiares` existen en
#  la tabla (schema_v4) pero ninguna pantalla los pide: alargaban demasiado el
#  alta para lo poco que un entrenador de formación puede responder. Las
#  columnas se dejan por si algún día las llena un club con cuerpo médico —
#  el antecedente familiar es el cribado cardiovascular de la FIFA.


def _limpiar_ficha_medica(medico):
    """Deja solo lo que se puede guardar, con su tipo y su tope."""
    if not isinstance(medico, dict):
        return {}

    limpio = {}
    for campo, tope in _TOPES_MEDICOS.items():
        valor = (medico.get(campo) or '').strip() if isinstance(medico.get(campo), str) else medico.get(campo)
        if valor:
            limpio[campo] = str(valor)[:tope]

    for campo in ('estatura_cm', 'peso_kg'):
        valor = medico.get(campo)
        if valor not in (None, ''):
            try:
                limpio[campo] = float(valor)
            except (TypeError, ValueError):
                pass

    for campo in ('ultimo_chequeo', 'certificado_vence'):
        valor = (medico.get(campo) or '').strip()
        if valor and db.parse_fecha(valor):
            limpio[campo] = valor[:10]

    apto = (medico.get('apto') or '').strip()
    if apto in db.APTITUD_META:
        limpio['apto'] = apto

    return limpio


_COLUMNA_FECHA = None


def _hay_fecha_nacimiento():
    """¿Está aplicada la migración de la fecha de nacimiento? Se mira una vez."""
    global _COLUMNA_FECHA
    if _COLUMNA_FECHA is None:
        try:
            db.sb().table('fut_manual_players').select('fecha_nacimiento').limit(1).execute()
            _COLUMNA_FECHA = True
        except Exception:
            logger.warning('Falta la columna fecha_nacimiento: aplica '
                           'sql/schema_v7_fecha_nacimiento.sql. Se guarda solo el año.')
            _COLUMNA_FECHA = False
    return _COLUMNA_FECHA


@bp.route('/api/manual', methods=['POST'])
@login_required


def api_manual():
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)
    nombre = (d.get('nombre') or '').strip()
    if len(nombre) < 2:
        return jsonify({'error': 'Escribe el nombre del jugador.'}), 400

    datos = {
        'nombre': nombre[:100],
        'posicion': (d.get('posicion') or '')[:40],
        'pie_habil': (d.get('pie_habil') or '')[:20],
        'telefono': (d.get('telefono') or '')[:30],
        'tutor': (d.get('tutor') or '')[:120],
        'notas': (d.get('notas') or '')[:600],
    }
    for campo, tipo in (('dorsal', int), ('anio_nacimiento', int),
                        ('estatura', float), ('peso', float),
                        ('goles', int), ('asistencias', int),
                        ('minutos_jugados', int), ('jugadas_clave', int),
                        ('valoracion_promedio', int)):
        v = d.get(campo)
        if v not in (None, ''):
            try:
                datos[campo] = tipo(v)
            except (TypeError, ValueError):
                pass

    #  Va DESPUES del bucle a proposito: la fecha completa manda sobre el año
    #  suelto, y si se pusiera antes el bucle lo sobrescribiria con lo que
    #  mandara el cliente. El año se deriva de la fecha para que lo que ya lo
    #  lee —solicitudes, ficha del jugador, registro— siga funcionando sin
    #  tocarlo. Si solo llega el año, se guarda el año y ya.
    fecha = (d.get('fecha_nacimiento') or '').strip()[:10]
    if fecha:
        anio = db.anio_de(fecha)
        if anio:
            datos['anio_nacimiento'] = anio
        #  La columna la añade `sql/schema_v7_fecha_nacimiento.sql`. Si el
        #  codigo llegara a produccion antes que el SQL, mandarla haria fallar
        #  el guardado entero y no se podrian dar de alta jugadores. Se
        #  comprueba una vez y, mientras no este, se guarda solo el año — que
        #  es exactamente lo que se hacia antes.
        if _hay_fecha_nacimiento():
            datos['fecha_nacimiento'] = fecha

    # Perfil Dinámico (18 atributos + estado): mismos campos que evaluar a un
    # jugador con cuenta, ver futbol/db.py:guardar_atributos. No son columnas
    # de fut_manual_players, así que se guardan aparte y no entran en `datos`.
    campos_perfil = {}
    # La fatiga llega como bajo|medio|alto y se guarda como número (db.py).
    if d.get('fatiga') in db.FATIGA_A_NUMERO:
        campos_perfil['fatiga'] = db.FATIGA_A_NUMERO[d['fatiga']]
    campos_numericos = set(db.ATRIBUTOS_18) | {'potencial'}
    campos_texto = ('riesgo_sobrecarga', 'fortalezas', 'debilidades', 'evolucion_tecnica',
                    'lesiones_historial', 'posicion_secundaria')
    for k in list(campos_numericos) + list(campos_texto):
        v = d.get(k)
        if v in (None, ''):
            continue
        if k in campos_numericos:
            try:
                campos_perfil[k] = int(v)
            except (TypeError, ValueError):
                pass
        else:
            campos_perfil[k] = str(v)[:600]

    # Ficha médica. Va aparte, en fut_medical: es el mismo sitio donde vive la
    # del jugador con cuenta, así no hay dos fichas médicas distintas según
    # cómo se dio de alta a la persona.
    campos_medicos = _limpiar_ficha_medica(d.get('medico') or {})

    mid = d.get('id')
    if mid:
        if not db.one('fut_manual_players', 'mio', id=mid, coach_id=uid):
            return jsonify({'error': 'Ese jugador no es de tu equipo.'}), 403
        db.update('fut_manual_players', datos, 'manual up', obligatorio=True,
                  id=mid, coach_id=uid)
        if campos_perfil:
            db.guardar_atributos(manual_player_id=mid, **campos_perfil)
        if campos_medicos:
            db.guardar_ficha_medica(manual_player_id=mid,
                                    actualizado_por=current_user.id, **campos_medicos)
        return jsonify({'ok': True, 'id': mid, 'mensaje': 'Ficha actualizada.'})

    # Los apuntados a mano cuentan para el tope del plan gratuito: si no,
    # el límite de plantilla no serviría de nada.
    if not roles.es_pro(current_user):
        n = (len(db.jugadores_del_entrenador(uid))
             + len(db.rows('fut_manual_players', 'cuenta', coach_id=uid, activo=True) or []))
        if n >= roles.LIMITE_PLANTILLA_FREE:
            return jsonify({
                'error': f'El plan gratuito llega a {roles.LIMITE_PLANTILLA_FREE} '
                         'jugadores. Pásate a Pro para una plantilla sin límite.',
                'pro': True, 'url': url_for('futbol.planes')}), 402

    datos.update({'coach_id': uid, 'activo': True,
                  'registrado_por': current_user.id, 'creado': _ahora()})
    fila = db.insert('fut_manual_players', datos, 'manual nuevo')
    if not fila:
        return jsonify({'error': 'No se pudo guardar.'}), 500
    if campos_perfil:
        db.guardar_atributos(manual_player_id=fila['id'], **campos_perfil)
    if campos_medicos:
        db.guardar_ficha_medica(manual_player_id=fila['id'],
                                actualizado_por=current_user.id, **campos_medicos)
    return jsonify({'ok': True, 'id': fila['id'],
                    'mensaje': f'{nombre} está en la plantilla.'})


@bp.route('/api/manual/<mid>', methods=['DELETE'])
@login_required
def api_manual_archivar(mid):
    """Se archiva en vez de borrar: si se borrara, sus evaluaciones quedarían
    huérfanas y el histórico del equipo se falsearía."""
    error = _guardia_coach()
    if error:
        return error
    if not db.update('fut_manual_players', {'activo': False}, 'archivar',
                     id=mid, coach_id=db.equipo_id(current_user.id)):
        return jsonify({'error': 'Ese jugador no es de tu equipo.'}), 404
    return jsonify({'ok': True, 'mensaje': 'Jugador archivado. Su histórico se conserva.'})


@bp.route('/api/manual/<mid>/restaurar', methods=['POST'])
@login_required
def api_manual_restaurar(mid):
    error = _guardia_coach()
    if error:
        return error
    if not db.update('fut_manual_players', {'activo': True}, 'restaurar',
                     id=mid, coach_id=db.equipo_id(current_user.id)):
        return jsonify({'error': 'Ese jugador no es de tu equipo.'}), 404
    return jsonify({'ok': True, 'mensaje': 'Jugador de vuelta en la plantilla.'})


@bp.route('/api/manual/<mid>/vincular', methods=['POST'])
@login_required
def api_manual_vincular(mid):
    """Enchufa la ficha manual a una cuenta que acaba de registrarse."""
    error = _guardia_coach()
    if error:
        return error

    uid = db.equipo_id(current_user.id)
    d = request.get_json(silent=True) or {}
    pid = d.get('player_id')

    manual = db.one('fut_manual_players', 'manual', id=mid, coach_id=uid)
    if not manual:
        return jsonify({'error': 'Ese jugador no es de tu equipo.'}), 404
    if not any(str(j['id']) == str(pid) for j in db.jugadores_del_entrenador(uid)):
        return jsonify({'error': 'Esa cuenta no está en tu plantilla.'}), 403

    # Las evaluaciones pasan a la cuenta: es lo que hace que valga la pena
    # haberlo apuntado a mano durante meses.
    n = 0
    for r in (db.rows('fut_eval_results', 'evals manual',
                      coach_id=uid, manual_player_id=mid) or []):
        db.update('fut_eval_results',
                  {'player_id': pid, 'manual_player_id': None}, 'traspasar', id=r['id'], obligatorio=True)
        n += 1

    db.update('fut_manual_players', {'vinculado_a': pid, 'activo': False},
              'vincular', id=mid, obligatorio=True)
    return jsonify({'ok': True,
                    'mensaje': f'Vinculado. Se traspasaron {n} evaluación(es).'})


# ═══════════════════════ SOLICITUDES DE INGRESO ═══════════════════════
@bp.route('/coach/solicitudes')
@login_required
def c_solicitudes():
    fuera = _coach_o_fuera()
    if fuera:
        return fuera

    uid = db.equipo_id(current_user.id)
    todas = db.rows('fut_join_requests', 'solicitudes todas', coach_id=uid,
                    _order='creado', _desc=True) or []
    ids = [s['player_id'] for s in todas if s.get('player_id')]
    personas = {}
    if ids:
        personas = {p['id']: p for p in db.q(
            lambda: db.sb().table('usuarios').select('*').in_('id', ids).execute().data or [],
            [], 'personas solicitud')}
    for s in todas:
        s['_jugador'] = db._normalizar_usuario(personas.get(s.get('player_id')))
        s['_fecha'] = db.parse_fecha(s.get('creado'))

    n = db.tamano_plantilla(uid)
    return render_template('c_solicitudes.html',
                           tab_activa='equipo', hide_tabbar=True,
                           pendientes=[s for s in todas if s.get('estado') == 'pendiente'],
                           resueltas=[s for s in todas if s.get('estado') != 'pendiente'][:20],
                           codigo=db.codigo_equipo(uid),
                           n_plantilla=n,
                           llena=roles.plantilla_llena(current_user, n),
                           tope=roles.limite_plantilla(current_user))


@bp.route('/api/solicitud/<sid>', methods=['POST'])
@login_required
def api_solicitud(sid):
    error = _guardia_coach()
    if error:
        return error

    uid = db.equipo_id(current_user.id)
    d = request.get_json(silent=True) or {}
    accion = d.get('accion')
    sol = db.one('fut_join_requests', 'solicitud', id=sid, coach_id=uid)
    if not sol:
        return jsonify({'error': 'Esa solicitud no existe.'}), 404
    if sol.get('estado') != 'pendiente':
        return jsonify({'error': 'Esa solicitud ya estaba resuelta.'}), 400

    es_asistente_sol = sol.get('tipo') == 'asistente'

    if accion == 'aceptar' and es_asistente_sol:
        # Meter a alguien en el cuerpo técnico es del dueño del equipo: un
        # asistente no puede ampliar el equipo por su cuenta.
        if roles.es_asistente(current_user):
            return jsonify({'error': 'Solo el entrenador principal acepta '
                                     'asistentes técnicos.'}), 403

        previo = db.one('fut_team_coaches', 'ya en un cuerpo',
                        coach_id=sol['player_id'])
        datos = {'principal_id': uid, 'coach_id': sol['player_id'],
                 'rol': 'asistente', 'estado': 'activo',
                 'retirado': None, 'creado': _ahora()}
        if previo:
            db.update('fut_team_coaches', datos, 'cambiar cuerpo', id=previo['id'], obligatorio=True)
        else:
            db.insert('fut_team_coaches', datos, 'alta asistente', obligatorio=True)

        db.update('fut_join_requests', {'estado': 'aceptada', 'resuelto': _ahora()},
                  'aceptar asist', id=sid, obligatorio=True)
        return jsonify({'ok': True,
                        'mensaje': 'Asistente aceptado. Ya puede evaluar, medir '
                                   'y pasar lista en tu equipo.'})

    if accion == 'aceptar':
        n = len(db.jugadores_del_entrenador(uid))
        if roles.plantilla_llena(current_user, n):
            return jsonify({
                'error': f'Tu plantilla llegó a {roles.LIMITE_PLANTILLA_FREE} '
                         'jugadores. Pásate a Pro para aceptar más.',
                'pro': True, 'url': url_for('futbol.planes')}), 402

        # Un jugador pertenece a un equipo a la vez: si ya estaba en otro, se
        # cambia de equipo en vez de duplicarse.
        previo = db.one('fut_plantilla', 'vinculo previo', player_id=sol['player_id'])
        if previo:
            db.update('fut_plantilla', {'coach_id': uid, 'activo': True},
                      'cambiar equipo', id=previo['id'], obligatorio=True)
        else:
            db.insert('fut_plantilla', {
                'coach_id': uid, 'player_id': sol['player_id'],
                'activo': True, 'creado': _ahora()}, 'aceptar solicitud', obligatorio=True)

        db.update('fut_join_requests', {'estado': 'aceptada', 'resuelto': _ahora()},
                  'aceptar', id=sid, obligatorio=True)
        return jsonify({'ok': True, 'mensaje': 'Jugador aceptado en el equipo.'})

    if accion == 'rechazar':
        db.update('fut_join_requests', {'estado': 'rechazada', 'resuelto': _ahora()},
                  'rechazar', id=sid, obligatorio=True)
        return jsonify({'ok': True, 'mensaje': 'Solicitud rechazada.'})

    return jsonify({'error': 'Acción desconocida.'}), 400


@bp.route('/coach/jugador/<pid>/sacar', methods=['POST'])
@login_required
def c_sacar_jugador(pid):
    error = _guardia_coach()
    if error:
        return error
    uid = db.equipo_id(current_user.id)
    v = db.one('fut_plantilla', 'vinculo', player_id=pid, coach_id=uid)
    if not v:
        return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 404
    db.delete('fut_plantilla', 'sacar', id=v['id'], obligatorio=True)
    return jsonify({'ok': True, 'mensaje': 'Jugador fuera de la plantilla. '
                                           'Su cuenta y su histórico siguen ahí.'})


# ═══════════════════════ UNIRSE COMO ASISTENTE ═══════════════════════
@bp.route('/unirme-equipo')
@login_required
def c_unirme_equipo():
    """Un entrenador pide entrar al cuerpo técnico de otro.

    Mismo código de equipo que usan los jugadores: no hace falta inventar un
    segundo código ni que el principal genere invitaciones una a una.
    """
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.p_unirme'))

    uid = current_user.id
    mia = db.one('fut_join_requests', 'mi solicitud', player_id=uid)
    if mia:
        mia['_fecha'] = db.parse_fecha(mia.get('creado'))
        if mia.get('coach_id'):
            mia['_coach'] = db._normalizar_usuario(
                db.one('usuarios', 'coach sol', id=mia['coach_id']))

    equipo_id = db.equipo_id(uid)
    principal = None
    if str(equipo_id) != str(uid):
        principal = db._normalizar_usuario(db.one('usuarios', 'principal', id=equipo_id))

    return render_template('c_unirme_equipo.html',
                           tab_activa='', hide_tabbar=True,
                           solicitud=mia,
                           principal=principal,
                           # Con tamano_plantilla, que suma a los apuntados a
                           # mano: si no, a quien tiene la plantilla entera sin
                           # cuenta le salia 0 y el aviso no aparecia.
                           n_propios=db.tamano_plantilla(uid))


@bp.route('/api/unirme-equipo', methods=['POST'])
@login_required
def api_unirme_equipo():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo un entrenador puede ser asistente.'}), 403

    uid = current_user.id
    d = request.get_json(silent=True) or {}
    codigo = (d.get('codigo') or '').strip().upper()
    if not codigo:
        return jsonify({'error': 'Escribe el código del equipo.'}), 400

    principal = db.one('usuarios', 'coach por codigo',
                       codigo_equipo=codigo, rol='especialista')
    if not principal:
        return jsonify({'error': 'Ese código no existe. Pídeselo al entrenador '
                                 'principal del equipo.'}), 404
    if str(principal['id']) == str(uid):
        return jsonify({'error': 'Ese es tu propio código.'}), 400

    # Ser asistente de otro NO borra tu equipo, pero sí deja de ser el que
    # gestionas: se avisa para que nadie descubra después que "desaparecieron"
    # sus jugadores.
    datos = {
        'coach_id': principal['id'], 'player_id': uid,
        'tipo': 'asistente',
        'mensaje': (d.get('mensaje') or '')[:400],
        'posicion': '',
        'estado': 'pendiente', 'resuelto': None, 'creado': _ahora(),
    }
    previa = db.one('fut_join_requests', 'previa',
                    player_id=uid, coach_id=principal['id'])
    if previa:
        db.update('fut_join_requests', datos, 'resolicitar asist', id=previa['id'], obligatorio=True)
    else:
        db.insert('fut_join_requests', datos, 'solicitar asist', obligatorio=True)

    return jsonify({'ok': True,
                    'mensaje': f'Solicitud enviada a {principal["nombre"]}. '
                               'Te avisará cuando te acepte en su cuerpo técnico.',
                    'redirect': url_for('futbol.c_unirme_equipo')})


# ═══════════════════════ LADO DEL JUGADOR ═══════════════════════
@bp.route('/unirme')
@login_required
def p_unirme():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_unirme_equipo'))

    uid = current_user.id
    mia = db.one('fut_join_requests', 'mi solicitud', player_id=uid)
    if mia:
        mia['_fecha'] = db.parse_fecha(mia.get('creado'))
        if mia.get('coach_id'):
            mia['_coach'] = db._normalizar_usuario(
                db.one('usuarios', 'coach sol', id=mia['coach_id']))

    return render_template('p_unirme.html',
                           tab_activa='', hide_tabbar=True,
                           entrenador=db.entrenador_del_jugador(uid),
                           solicitud=mia,
                           posiciones=POSICIONES)


@bp.route('/api/unirme', methods=['POST'])
@login_required
def api_unirme():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') == 'especialista':
        return jsonify({'error': 'Los entrenadores no se unen a equipos.'}), 403

    uid = current_user.id
    d = request.get_json(silent=True) or {}
    codigo = (d.get('codigo') or '').strip().upper()
    if not codigo:
        return jsonify({'error': 'Escribe el código que te dio tu entrenador.'}), 400

    coach = db.one('usuarios', 'coach por codigo',
                   codigo_equipo=codigo, rol='especialista')
    if not coach:
        return jsonify({'error': 'Ese código no existe. Pídeselo otra vez a tu '
                                 'entrenador y revisa mayúsculas y números.'}), 404

    actual = db.entrenador_del_jugador(uid)
    if actual and str(actual['id']) == str(coach['id']):
        return jsonify({'error': f'Ya estás en el equipo de {coach["nombre"]}.'}), 400

    datos = {
        'coach_id': coach['id'], 'player_id': uid,
        'mensaje': (d.get('mensaje') or '')[:400],
        'posicion': (d.get('posicion') or '')[:40],
        'estado': 'pendiente', 'resuelto': None, 'creado': _ahora(),
    }
    previa = db.one('fut_join_requests', 'previa', player_id=uid, coach_id=coach['id'])
    if previa:
        db.update('fut_join_requests', datos, 'resolicitar', id=previa['id'], obligatorio=True)
    else:
        db.insert('fut_join_requests', datos, 'solicitar', obligatorio=True)

    return jsonify({'ok': True,
                    'mensaje': f'Solicitud enviada a {coach["nombre"]}. '
                               'Te avisará cuando la acepte.',
                    'redirect': url_for('futbol.p_unirme')})
