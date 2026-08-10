# -*- coding: utf-8 -*-
"""
admin.py — El panel de los tres administradores.

Toma la forma del panel de ElectroBiomed (cristal oscuro, tarjetas de métricas,
tabla de usuarios y bloque de códigos) pero con los datos de ProFoot y con lo
que allí no había: aprobación de comprobantes DeUna y bandeja de avisos.

Vive fuera de `futbol/` a propósito: no es una pantalla del producto, es la
trastienda. Se monta en /admin y todas sus rutas pasan por @solo_admin.
"""
import logging
from datetime import date, datetime, timedelta, timezone

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

import avisos
import suscripciones as subs
from roles import ROLES, solo_admin

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__, url_prefix='/admin')


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _csrf():
    from app import csrf_ok
    return csrf_ok()


def _api(f):
    """Sesión + administrador + CSRF + errores en JSON."""
    from functools import wraps

    @wraps(f)
    @login_required
    @solo_admin
    def wrapper(*a, **kw):
        if request.method != 'GET' and not _csrf():
            return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
        try:
            return f(*a, **kw)
        except Exception as e:
            logger.error('admin %s: %s', request.path, e, exc_info=True)
            return jsonify({'error': 'No se pudo completar la acción.'}), 500
    return wrapper


def _cuerpo():
    return request.get_json(silent=True) or {}


# ═══════════════════════ DATOS ═══════════════════════
def _usuarios():
    """Todos los usuarios con lo que el panel necesita mostrar de cada uno."""
    from futbol import db

    filas = db.rows('usuarios', 'admin usuarios', _order='creado', _desc=True) or []
    if not filas:
        return []

    # Cuántos jugadores tiene cada entrenador: una consulta, no una por fila.
    plantilla = db.rows('fut_plantilla', 'admin plantilla', activo=True) or []
    por_coach = {}
    for v in plantilla:
        por_coach.setdefault(v.get('coach_id'), []).append(v.get('player_id'))
    coach_de = {v.get('player_id'): v.get('coach_id') for v in plantilla}

    nombres = {f['id']: f.get('nombre') for f in filas}
    ahora = datetime.now(timezone.utc)

    for f in filas:
        f['_es_coach'] = f.get('rol') == 'especialista'
        f['_tier'] = (f.get('tier') or 'free').lower()
        hasta = subs._parse(f.get('pro_hasta'))
        f['_pro_vigente'] = f['_tier'] == 'pro' and (not hasta or hasta > ahora)
        f['_pro_hasta'] = db.parse_fecha(f.get('pro_hasta'))
        f['_dias'] = (hasta - ahora).days if hasta else None
        f['_alta'] = db.parse_fecha(f.get('creado'))
        f['_n_jugadores'] = len(por_coach.get(f['id'], []))
        f['_coach'] = nombres.get(coach_de.get(f['id']), '') if not f['_es_coach'] else ''
        if f.get('es_admin'):
            f['_rol'] = 'admin'
        elif f['_es_coach']:
            f['_rol'] = 'coach_pro' if f['_pro_vigente'] else 'entrenador'
        else:
            f['_rol'] = 'jugador_pro' if f['_pro_vigente'] else 'jugador'
        f['_rol_etiqueta'] = ROLES[f['_rol']]['etiqueta']
        f['_rol_emoji'] = ROLES[f['_rol']]['emoji']
    return filas


def _metricas(usuarios):
    hoy = date.today()
    hace_30 = hoy - timedelta(days=30)
    pro = [u for u in usuarios if u['_pro_vigente'] and not u.get('es_admin')]
    return {
        'total': len(usuarios),
        'jugadores': len([u for u in usuarios if not u['_es_coach'] and not u.get('es_admin')]),
        'entrenadores': len([u for u in usuarios if u['_es_coach'] and not u.get('es_admin')]),
        'admins': len([u for u in usuarios if u.get('es_admin')]),
        'pro': len(pro),
        'free': len(usuarios) - len(pro) - len([u for u in usuarios if u.get('es_admin')]),
        'nuevos_30': len([u for u in usuarios if (u['_alta'] or date.min) >= hace_30]),
        'bloqueados': len([u for u in usuarios if u.get('bloqueado')]),
        'caducan_7': len([u for u in pro if u['_dias'] is not None and 0 <= u['_dias'] <= 7]),
    }


def _pagos(limite=120):
    from futbol import db
    filas = db.rows('fut_pagos', 'admin pagos', _order='creado', _desc=True,
                    _limit=limite) or []
    if not filas:
        return []
    ids = list({f['user_id'] for f in filas if f.get('user_id')})
    personas = db.q(
        lambda: db.sb().table('usuarios').select('id, nombre, correo, rol')
        .in_('id', ids).execute().data or [], [], 'personas pago')
    por_id = {p['id']: p for p in personas}
    for f in filas:
        f['_usuario'] = por_id.get(f.get('user_id'), {})
        f['_fecha'] = db.parse_fecha(f.get('creado'))
        f['_pendiente'] = (f.get('estado') or '').lower() in ('pendiente', 'por_revisar')
    return filas


def ajustes():
    """Los ajustes de la app, con valores por defecto sensatos.

    Están en la base y no en el .env porque el administrador tiene que poder
    cambiar el número de DeUna un domingo sin redesplegar.
    """
    from futbol import db
    fila = db.one('fut_settings', 'ajustes', clave='general') or {}
    guardado = fila.get('valor') or {}
    base = {
        'deuna_activo': True,
        'deuna_titular': '',
        'deuna_documento': '',
        'deuna_telefono': '',
        'deuna_banco': 'Banco Pichincha',
        'deuna_qr': '',
        'deuna_instrucciones': (
            'Abre DeUna, escanea el código o busca el número, envía el importe '
            'exacto y sube la captura del comprobante.'),
        'precio_jugador': '4.99',
        'precio_entrenador': '14.99',
        'precio_club': '49.00',
        'aviso_panel': '',
    }
    base.update({k: v for k, v in guardado.items() if v is not None})
    return base


def guardar_ajustes(nuevos, por=None):
    from futbol import db
    actuales = ajustes()
    actuales.update(nuevos)
    db.upsert('fut_settings', {
        'clave': 'general', 'valor': actuales,
        'actualizado': _ahora(), 'por': por,
    }, 'guardar ajustes', on_conflict='clave')
    return actuales


# ═══════════════════════ PANTALLAS ═══════════════════════
@bp.route('/')
@login_required
@solo_admin
def tablero():
    # Al entrar se pone al día quién venció: el panel no puede enseñar como Pro
    # a alguien que dejó de pagar hace tres semanas.
    subs.caducar_vencidos()

    usuarios = _usuarios()
    pagos = _pagos(20)
    return render_template(
        'admin_tablero.html',
        metricas=_metricas(usuarios),
        recientes=usuarios[:8],
        caducan=[u for u in usuarios
                 if u['_pro_vigente'] and u['_dias'] is not None and 0 <= u['_dias'] <= 14][:8],
        pendientes=[p for p in pagos if p['_pendiente']],
        avisos=avisos.ultimos(8),
        sin_leer=avisos.sin_leer(),
        codigos=subs.codigos()[:6],
        seccion='tablero')


@bp.route('/usuarios')
@login_required
@solo_admin
def usuarios():
    lista = _usuarios()
    filtro = (request.args.get('f') or '').strip().lower()
    rol = request.args.get('rol') or ''

    if filtro:
        lista = [u for u in lista
                 if filtro in (u.get('nombre') or '').lower()
                 or filtro in (u.get('correo') or '').lower()
                 or filtro in (u.get('codigo_equipo') or '').lower()]
    if rol:
        lista = [u for u in lista if u['_rol'] == rol]

    return render_template('admin_usuarios.html',
                           usuarios=lista,
                           metricas=_metricas(_usuarios()),
                           filtro=filtro, rol_filtro=rol,
                           roles=ROLES,
                           sin_leer=avisos.sin_leer(),
                           seccion='usuarios')


@bp.route('/codigos')
@login_required
@solo_admin
def codigos():
    lista = subs.codigos()
    return render_template('admin_codigos.html',
                           codigos=lista,
                           canjes=subs.canjes(80),
                           vigentes=len([c for c in lista if c['_vigente']]),
                           cupos=sum(c['_restantes'] for c in lista if c['_vigente']),
                           sin_leer=avisos.sin_leer(),
                           seccion='codigos')


@bp.route('/pagos')
@login_required
@solo_admin
def pagos():
    lista = _pagos(200)
    return render_template('admin_pagos.html',
                           pagos=lista,
                           pendientes=[p for p in lista if p['_pendiente']],
                           ajustes=ajustes(),
                           sin_leer=avisos.sin_leer(),
                           seccion='pagos')


@bp.route('/avisos')
@login_required
@solo_admin
def bandeja():
    return render_template('admin_avisos.html',
                           avisos=avisos.ultimos(120),
                           sin_leer=avisos.sin_leer(),
                           seccion='avisos')


@bp.route('/ajustes')
@login_required
@solo_admin
def pantalla_ajustes():
    from futbol import db
    todos = db.rows('usuarios', 'para admin', _order='nombre') or []
    return render_template('admin_ajustes.html',
                           ajustes=ajustes(),
                           administradores=[u for u in todos if u.get('es_admin')],
                           candidatos=[u for u in todos if not u.get('es_admin')],
                           correos_env=avisos.ADMIN_EMAILS_ENV,
                           sin_leer=avisos.sin_leer(),
                           seccion='ajustes')


# ═══════════════════════ API ═══════════════════════
@bp.route('/api/usuario/<uid>', methods=['POST'])
@_api
def api_usuario(uid):
    """Cambia el plan, el rol, el bloqueo o los datos de un usuario."""
    from futbol import db

    d = _cuerpo()
    accion = d.get('accion')
    fila = db.one('usuarios', 'usuario admin', id=uid)
    if not fila:
        return jsonify({'error': 'Ese usuario no existe.'}), 404

    if accion == 'pro':
        meses = max(1, min(24, int(d.get('meses') or 1)))
        hasta = subs.activar(uid, meses=meses, origen='admin')
        avisos.avisar('info', f'Pro concedido a {fila.get("nombre")}',
                      f'{meses} mes(es) por {current_user.name}',
                      usuario=uid, correo=False)
        return jsonify({'ok': True, 'hasta': hasta.isoformat() if hasta else None,
                        'mensaje': f'{fila.get("nombre")} tiene Pro por {meses} mes(es).'})

    if accion == 'free':
        subs.desactivar(uid, 'retirado por el administrador')
        return jsonify({'ok': True, 'mensaje': f'{fila.get("nombre")} pasó al plan gratuito.'})

    if accion == 'bloquear':
        bloquear = bool(d.get('valor'))
        db.update('usuarios', {'bloqueado': bloquear}, 'bloquear', id=uid)
        return jsonify({'ok': True,
                        'mensaje': ('Cuenta bloqueada.' if bloquear else 'Cuenta desbloqueada.')})

    if accion == 'admin':
        hacer = bool(d.get('valor'))
        actuales = [u for u in (db.rows('usuarios', 'admins', es_admin=True) or [])]
        if hacer and len(actuales) >= 3 and not fila.get('es_admin'):
            return jsonify({'error': 'Ya hay tres administradores. Quita a uno primero.'}), 400
        if not hacer and str(uid) == str(current_user.id):
            return jsonify({'error': 'No puedes quitarte a ti mismo el acceso.'}), 400
        db.update('usuarios', {'es_admin': hacer}, 'admin', id=uid)
        # Sin esto, el proceso seguiría creyendo que no hay administradores y
        # ADMIN_EMAILS del entorno volvería a conceder acceso.
        from usuarios import olvidar_cache_admins
        olvidar_cache_admins()
        avisos.avisar('info',
                      ('Nuevo administrador: ' if hacer else 'Administrador retirado: ')
                      + (fila.get('nombre') or ''),
                      f'Lo hizo {current_user.name}', usuario=uid)
        return jsonify({'ok': True,
                        'mensaje': ('Ahora es administrador.' if hacer
                                    else 'Ya no es administrador.')})

    if accion == 'datos':
        cambios = {}
        for campo, tope in (('nombre', 80), ('correo', 120), ('telefono', 30), ('club', 80)):
            if campo in d:
                cambios[campo] = (str(d[campo]) or '').strip()[:tope] or None
        if 'correo' in cambios and cambios['correo']:
            cambios['correo'] = cambios['correo'].lower()
            otro = db.one('usuarios', 'correo repe', correo=cambios['correo'])
            if otro and str(otro['id']) != str(uid):
                return jsonify({'error': 'Ese correo ya lo usa otra cuenta.'}), 400
        if not cambios:
            return jsonify({'error': 'Nada que cambiar.'}), 400
        db.update('usuarios', cambios, 'datos usuario', id=uid)
        return jsonify({'ok': True, 'mensaje': 'Datos actualizados.'})

    if accion == 'codigo_equipo':
        if fila.get('rol') != 'especialista':
            return jsonify({'error': 'Solo los entrenadores tienen código de equipo.'}), 400
        from auth import _nuevo_codigo_equipo
        nuevo = _nuevo_codigo_equipo()
        db.update('usuarios', {'codigo_equipo': nuevo}, 'nuevo codigo eq', id=uid)
        return jsonify({'ok': True, 'codigo': nuevo,
                        'mensaje': f'Código de equipo nuevo: {nuevo}'})

    return jsonify({'error': 'Acción desconocida.'}), 400


@bp.route('/api/usuario/<uid>/borrar', methods=['POST'])
@_api
def api_borrar_usuario(uid):
    """Borra la cuenta. Las filas hijas caen por ON DELETE CASCADE."""
    from futbol import db

    if str(uid) == str(current_user.id):
        return jsonify({'error': 'No puedes borrar tu propia cuenta.'}), 400
    fila = db.one('usuarios', 'borrar usuario', id=uid)
    if not fila:
        return jsonify({'error': 'Ese usuario no existe.'}), 404
    if fila.get('es_admin'):
        return jsonify({'error': 'Quítale primero el rol de administrador.'}), 400

    db.delete('usuarios', 'borrar usuario', id=uid)
    avisos.avisar('baja', f'Cuenta borrada: {fila.get("nombre")}',
                  f'{fila.get("correo")} · la borró {current_user.name}')
    return jsonify({'ok': True, 'mensaje': 'Cuenta borrada.'})


@bp.route('/api/codigo', methods=['POST'])
@_api
def api_codigo_crear():
    d = _cuerpo()
    cantidad = max(1, min(50, int(d.get('cantidad') or 1)))
    creados, errores = [], []

    for i in range(cantidad):
        # Con cantidad > 1 se generan solos: pedir 20 códigos a mano no tiene sentido.
        codigo = (d.get('codigo') or '').strip().upper() if cantidad == 1 else None
        if not codigo:
            codigo = subs.generar_codigo(d.get('prefijo') or 'PRO')
        fila, error = subs.crear_codigo(
            current_user.id, codigo=codigo,
            meses=d.get('meses') or 3, max_usos=d.get('max_usos') or 1,
            para_rol=d.get('para_rol') or 'cualquiera',
            vence=d.get('vence') or None, nota=d.get('nota') or '')
        if error:
            errores.append(error)
        else:
            creados.append(fila['codigo'])

    if not creados:
        return jsonify({'error': errores[0] if errores else 'No se pudo crear.'}), 400
    return jsonify({'ok': True, 'codigos': creados,
                    'mensaje': (f'{len(creados)} código(s) creado(s): '
                                + ', '.join(creados[:5])
                                + ('…' if len(creados) > 5 else ''))})


@bp.route('/api/codigo/<cid>', methods=['POST'])
@_api
def api_codigo_cambiar(cid):
    from futbol import db
    d = _cuerpo()
    if 'activo' in d:
        db.update('fut_promo_codes', {'activo': bool(d['activo'])}, 'codigo activo', id=cid)
        return jsonify({'ok': True,
                        'mensaje': 'Código reactivado.' if d['activo'] else 'Código desactivado.'})
    return jsonify({'error': 'Nada que cambiar.'}), 400


@bp.route('/api/codigo/<cid>/borrar', methods=['POST'])
@_api
def api_codigo_borrar(cid):
    from futbol import db
    db.delete('fut_promo_codes', 'borrar codigo', id=cid)
    return jsonify({'ok': True, 'mensaje': 'Código borrado.'})


@bp.route('/api/pago/<pid>', methods=['POST'])
@_api
def api_pago(pid):
    """Aprueba o rechaza un comprobante de DeUna."""
    from futbol import db

    d = _cuerpo()
    pago = db.one('fut_pagos', 'pago admin', id=pid)
    if not pago:
        return jsonify({'error': 'Ese pago no existe.'}), 404

    accion = d.get('accion')
    nota = (d.get('nota') or '')[:400]

    if accion == 'aprobar':
        meses = max(1, min(24, int(d.get('meses') or pago.get('meses') or 1)))
        hasta = subs.activar(pago['user_id'], meses=meses,
                             origen=pago.get('proveedor') or 'deuna',
                             plan=pago.get('plan'))
        db.update('fut_pagos', {
            'estado': 'aprobado', 'revisado_por': current_user.id,
            'revisado': _ahora(), 'nota_admin': nota, 'meses': meses,
        }, 'aprobar pago', id=pid)
        usuario = db.one('usuarios', 'usuario pago', id=pago['user_id']) or {}
        avisos.avisar('pago', f'Pago aprobado · {usuario.get("nombre", "?")}',
                      f'{meses} mes(es) de Pro · lo aprobó {current_user.name}',
                      usuario=pago['user_id'], importe=pago.get('importe'), correo=False)
        return jsonify({'ok': True, 'hasta': hasta.isoformat() if hasta else None,
                        'mensaje': f'Aprobado. {usuario.get("nombre")} tiene Pro '
                                   f'por {meses} mes(es).'})

    if accion == 'rechazar':
        db.update('fut_pagos', {
            'estado': 'rechazado', 'revisado_por': current_user.id,
            'revisado': _ahora(), 'nota_admin': nota,
        }, 'rechazar pago', id=pid)
        return jsonify({'ok': True, 'mensaje': 'Comprobante rechazado.'})

    return jsonify({'error': 'Acción desconocida.'}), 400


@bp.route('/api/ajustes', methods=['POST'])
@_api
def api_ajustes():
    d = _cuerpo()
    permitidos = ('deuna_activo', 'deuna_titular', 'deuna_documento', 'deuna_telefono',
                  'deuna_banco', 'deuna_qr', 'deuna_instrucciones',
                  'precio_jugador', 'precio_entrenador', 'precio_club', 'aviso_panel')
    nuevos = {k: (d[k] if k == 'deuna_activo' else str(d[k])[:600])
              for k in permitidos if k in d}
    if not nuevos:
        return jsonify({'error': 'Nada que guardar.'}), 400
    guardar_ajustes(nuevos, por=current_user.id)
    return jsonify({'ok': True, 'mensaje': 'Ajustes guardados.'})


@bp.route('/api/avisos/leer', methods=['POST'])
@_api
def api_avisos_leer():
    d = _cuerpo()
    if d.get('todos'):
        pendientes = [a['id'] for a in avisos.ultimos(500, solo_sin_leer=True)]
        avisos.marcar_leidas(pendientes, current_user.id)
        return jsonify({'ok': True, 'n': len(pendientes)})
    avisos.marcar_leidas(d.get('ids') or [], current_user.id)
    return jsonify({'ok': True})
