# -*- coding: utf-8 -*-
"""
futbol/salud.py — Ficha médica y control de lesiones.

La frontera de privacidad, que es lo importante aquí
────────────────────────────────────────────────────
La ficha médica del jugador (alergias, medicación, condiciones) la escribe y la
lee ÉL. El entrenador solo ve lo que hace falta para no matarlo en un campo: el
contacto de emergencia y las alergias. No ve medicación ni condiciones.

Las lesiones son lo contrario: las lleva el entrenador porque afectan a las
convocatorias, y el jugador las ve todas.

Es la misma regla que ya rige el check-in de bienestar: si el jugador sospecha
que el entrenador lee todo, deja de escribir la verdad y el módulo no sirve
para nada.
"""
import logging
from datetime import date, datetime, timezone

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles

from . import bp, db

logger = logging.getLogger(__name__)

ZONAS = ['Tobillo', 'Rodilla', 'Isquiotibiales', 'Cuádriceps', 'Aductores',
         'Gemelo', 'Cadera', 'Ingle', 'Espalda baja', 'Hombro', 'Pie',
         'Muñeca', 'Cabeza', 'Otra']

TIPOS_LESION = [('muscular', 'Muscular'), ('articular', 'Articular'),
                ('osea', 'Ósea'), ('ligamentosa', 'Ligamentosa'),
                ('contusion', 'Contusión'), ('otra', 'Otra')]

GRAVEDADES = [('leve', 'Leve', '#f59e0b', '1 a 7 días'),
              ('moderada', 'Moderada', '#f97316', '1 a 4 semanas'),
              ('grave', 'Grave', '#ef4444', 'más de 4 semanas')]
GRAVEDAD_META = {c: {'etiqueta': e, 'color': col, 'plazo': p}
                 for c, e, col, p in GRAVEDADES}

ESTADOS = [('activa', 'De baja', '#ef4444'),
           ('recuperando', 'Recuperándose', '#f59e0b'),
           ('alta', 'De alta', '#10b981')]
ESTADO_META = {c: {'etiqueta': e, 'color': col} for c, e, col in ESTADOS}


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _guardia():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    return None


def decorar_lesiones(filas):
    hoy = date.today()
    for l in filas or []:
        l['_fecha'] = db.parse_fecha(l.get('fecha'))
        l['_alta_prevista'] = db.parse_fecha(l.get('alta_prevista'))
        l['_alta_real'] = db.parse_fecha(l.get('alta_real'))
        l['_gravedad'] = GRAVEDAD_META.get(l.get('gravedad') or 'leve', GRAVEDADES[0][1])
        l['_estado'] = ESTADO_META.get(l.get('estado') or 'activa',
                                       {'etiqueta': 'De baja', 'color': '#ef4444'})
        fin = l['_alta_real'] or hoy
        l['_dias'] = (fin - l['_fecha']).days if l['_fecha'] else None
        l['_restantes'] = ((l['_alta_prevista'] - hoy).days
                           if l['_alta_prevista'] and not l['_alta_real'] else None)
    return filas or []


def lesiones_activas(coach_id):
    filas = db.rows('fut_injuries', 'lesiones activas', coach_id=coach_id) or []
    return decorar_lesiones([f for f in filas if f.get('estado') != 'alta'])


# ═══════════════════════ LADO DEL JUGADOR ═══════════════════════
@bp.route('/medico')
@login_required
def p_medico():
    if getattr(current_user, 'role', '') == 'especialista':
        return redirect(url_for('futbol.c_medico'))

    uid = current_user.id
    ficha = db.one('fut_medical', 'mi ficha', player_id=uid) or {}
    lesiones = decorar_lesiones(
        db.rows('fut_injuries', 'mis lesiones', player_id=uid,
                _order='fecha', _desc=True, _limit=60) or [])

    return render_template('p_medico.html',
                           tab_activa='ficha', hide_tabbar=True,
                           ficha=ficha,
                           lesiones=lesiones,
                           activas=[l for l in lesiones if l.get('estado') != 'alta'],
                           entrenador=db.entrenador_del_jugador(uid),
                           gravedades=GRAVEDADES, estados=ESTADOS)


@bp.route('/api/medico', methods=['POST'])
@login_required
def api_medico():
    """Solo el propio jugador escribe su ficha médica. El entrenador no."""
    error = _guardia()
    if error:
        return error
    if getattr(current_user, 'role', '') == 'especialista':
        return jsonify({'error': 'La ficha médica la escribe el jugador.'}), 403

    d = request.get_json(silent=True) or {}
    datos = {}
    for campo, tope in (('grupo_sanguineo', 10), ('alergias', 600),
                        ('medicacion', 600), ('condiciones', 800),
                        ('contacto_nombre', 120), ('contacto_tel', 30),
                        ('contacto_parentesco', 60), ('seguro', 120)):
        if campo in d:
            datos[campo] = (str(d[campo]) or '')[:tope]

    # `solo_basicos`: el jugador escribe lo suyo, pero el veredicto de aptitud
    # y el cribado médico los firma el cuerpo técnico, no el interesado.
    if not db.guardar_ficha_medica(player_id=current_user.id,
                                   actualizado_por=current_user.id,
                                   solo_basicos=True, **datos):
        return jsonify({'error': 'No se pudo guardar la ficha.'}), 500
    return jsonify({'ok': True, 'mensaje': 'Ficha médica guardada.'})


# ═══════════════════════ LADO DEL ENTRENADOR ═══════════════════════
@bp.route('/coach/medico')
@login_required
@roles.solo_pro('medico')
def c_medico():
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.p_medico'))

    uid = db.equipo_id(current_user.id)
    jugadores = db.jugadores_del_entrenador(uid)
    lesiones = decorar_lesiones(
        db.rows('fut_injuries', 'lesiones equipo', coach_id=uid,
                _order='fecha', _desc=True, _limit=200) or [])

    por_jugador = {}
    for l in lesiones:
        por_jugador.setdefault(str(l.get('player_id')), []).append(l)

    # Del jugador solo se traen los campos que el entrenador puede ver.
    # La medicación y las condiciones NO se piden: no basta con no pintarlas,
    # no tienen que salir de la base.
    contactos = {}
    if jugadores:
        ids = [j['id'] for j in jugadores]
        filas = db.q(
            lambda: db.sb().table('fut_medical')
            .select('player_id, contacto_nombre, contacto_tel, alergias, grupo_sanguineo')
            .in_('player_id', ids).execute().data or [], [], 'contactos')
        contactos = {f['player_id']: f for f in filas}

    for j in jugadores:
        suyas = por_jugador.get(str(j['id']), [])
        j['_lesiones'] = suyas
        j['_activa'] = next((l for l in suyas if l.get('estado') != 'alta'), None)
        j['_medico'] = contactos.get(j['id'], {})

    activas = [l for l in lesiones if l.get('estado') != 'alta']
    return render_template('c_medico.html',
                           tab_activa='equipo', hide_tabbar=True,
                           jugadores=jugadores,
                           lesiones=lesiones[:40], activas=activas,
                           n_disponibles=len([j for j in jugadores if not j['_activa']]),
                           zonas=ZONAS, tipos=TIPOS_LESION,
                           gravedades=GRAVEDADES, estados=ESTADOS,
                           hoy=date.today().isoformat())


@bp.route('/api/lesion', methods=['POST'])
@login_required
def api_lesion():
    """Crea o actualiza una lesión. La lleva el entrenador."""
    error = _guardia()
    if error:
        return error
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'El parte de lesiones lo lleva el entrenador.'}), 403

    uid = db.equipo_id(current_user.id)
    d = request.get_json(silent=True) or {}
    lid = d.get('id')

    # Al actualizar, el jugador es el que ya tenía el parte: pedirlo otra vez
    # solo daría ocasión de equivocarse (y de mover una lesión a otra persona).
    if lid:
        previa = db.one('fut_injuries', 'lesion mia', id=lid, coach_id=uid)
        if not previa:
            return jsonify({'error': 'Ese parte no es tuyo.'}), 403
        pid = previa.get('player_id')
    else:
        pid = d.get('player_id')
        if not pid or not any(str(j['id']) == str(pid)
                              for j in db.jugadores_del_entrenador(uid)):
            return jsonify({'error': 'Ese jugador no es de tu plantilla.'}), 403

    # Al actualizar solo se tocan los campos que vengan: dar el alta manda
    # {id, estado} y no puede borrar la zona ni la fecha de la lesión.
    datos = {'player_id': pid, 'coach_id': uid}
    campos = {
        'zona': lambda v: str(v)[:60],
        'lado': lambda v: str(v)[:20],
        'tipo': lambda v: v if v in dict(TIPOS_LESION) else 'otra',
        'gravedad': lambda v: v if v in GRAVEDAD_META else 'leve',
        'estado': lambda v: v if v in ESTADO_META else 'activa',
        'fecha': lambda v: v or db.hoy_iso(),
        'alta_prevista': lambda v: v or None,
        'alta_real': lambda v: v or None,
        'descripcion': lambda v: str(v)[:1000],
    }
    for campo, limpiar in campos.items():
        if campo in d:
            datos[campo] = limpiar(d[campo])

    if not lid:
        datos.setdefault('estado', 'activa')
        datos.setdefault('fecha', db.hoy_iso())
        if not datos.get('zona'):
            return jsonify({'error': 'Indica la zona de la lesión.'}), 400

    # Dar el alta sin fecha deja el parte a medias y descuadra los días de baja.
    if datos.get('estado') == 'alta' and not datos.get('alta_real'):
        datos['alta_real'] = db.hoy_iso()

    if lid:
        db.update('fut_injuries', datos, 'lesion up', id=lid, coach_id=uid)
        return jsonify({'ok': True, 'id': lid, 'mensaje': 'Parte actualizado.'})

    datos['registrado_por'] = current_user.id
    datos['creado'] = _ahora()
    fila = db.insert('fut_injuries', datos, 'lesion nueva')
    if not fila:
        return jsonify({'error': 'No se pudo guardar el parte.'}), 500
    return jsonify({'ok': True, 'id': fila['id'], 'mensaje': 'Lesión registrada.'})


@bp.route('/api/lesion/<lid>', methods=['DELETE'])
@login_required
def api_lesion_borrar(lid):
    error = _guardia()
    if error:
        return error
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el entrenador borra partes.'}), 403
    db.delete('fut_injuries', 'borrar lesion', id=lid, coach_id=db.equipo_id(current_user.id))
    return jsonify({'ok': True, 'mensaje': 'Parte borrado.'})
