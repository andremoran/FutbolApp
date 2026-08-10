# -*- coding: utf-8 -*-
"""
suscripciones.py — Activar, renovar y quitar el plan Pro.

Todo lo que cambia el `tier` de un usuario pasa por aquí: la tarjeta de PayPal,
el comprobante de DeUna que aprueba un administrador, el código de suscripción
y el interruptor manual del panel. Tenerlo en un solo sitio evita que dentro de
seis meses haya cuatro maneras distintas —y tres de ellas con un fallo— de
poner a alguien en Pro.
"""
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'   # sin 0/O ni 1/I: se dictan por teléfono
RE_CODIGO = re.compile(r'^[A-Z0-9\-]{4,32}$')


def _ahora():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


def _parse(valor):
    if not valor:
        return None
    try:
        f = datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    return f if f.tzinfo else f.replace(tzinfo=timezone.utc)


# ═══════════════════════ ACTIVAR ═══════════════════════
def activar(user_id, meses=1, origen='admin', plan=None, codigo=None,
            suscripcion_id=None, estado='ACTIVE'):
    """Pone al usuario en Pro y devuelve hasta cuándo.

    Si ya tenía Pro vigente, los meses se SUMAN a lo que le quedaba: un pago
    adelantado no debe borrar los días que ya pagó.
    """
    from futbol import db

    fila = db.one('usuarios', 'activar', id=user_id)
    if not fila:
        return None

    base = _parse(fila.get('pro_hasta'))
    if not base or base < _ahora() or (fila.get('tier') or 'free') != 'pro':
        base = _ahora()
    hasta = base + timedelta(days=int(round(30.44 * max(1, int(meses)))))

    cambios = {
        'tier': 'pro',
        'activo': True,                    # compatibilidad con lo que ya había
        'pro_hasta': _iso(hasta),
        'pro_origen': origen,
        'bloqueado': False,
    }
    if plan:
        cambios['plan'] = plan
    if codigo:
        cambios['codigo_promo'] = codigo
    if suscripcion_id:
        cambios['suscripcion_id'] = suscripcion_id
        cambios['suscripcion_estado'] = estado
        cambios['suscripcion_desde'] = _iso(_ahora())

    db.update('usuarios', cambios, 'activar pro', id=user_id)
    logger.info('Pro activado para %s hasta %s (%s)', user_id, hasta.date(), origen)
    return hasta


def desactivar(user_id, motivo='cancelado'):
    """Devuelve al usuario al plan gratuito. No borra nada de lo que creó."""
    from futbol import db
    db.update('usuarios', {
        'tier': 'free', 'activo': False,
        'suscripcion_estado': motivo, 'pro_hasta': None,
    }, 'bajar a free', id=user_id)
    logger.info('Pro retirado a %s (%s)', user_id, motivo)


def dias_restantes(usuario):
    """Días que le quedan de Pro. None si no caduca o no es Pro."""
    hasta = _parse(getattr(usuario, 'pro_hasta', None))
    if not hasta:
        return None
    return max(0, (hasta - _ahora()).days)


def caduca_pronto(usuario, umbral=7):
    d = dias_restantes(usuario)
    return d is not None and d <= umbral


# ═══════════════════════ CÓDIGOS ═══════════════════════
def generar_codigo(prefijo='PRO', largo=6):
    sufijo = ''.join(secrets.choice(ALFABETO) for _ in range(largo))
    return f'{(prefijo or "PRO").upper()[:10]}-{sufijo}'


def crear_codigo(creado_por, codigo=None, meses=3, max_usos=1,
                 para_rol='cualquiera', vence=None, nota=''):
    """Da de alta un código de suscripción. Devuelve (fila, error)."""
    from futbol import db

    codigo = (codigo or generar_codigo()).strip().upper()
    if not RE_CODIGO.match(codigo):
        return None, 'El código solo admite letras, números y guiones (4 a 32).'
    if not 1 <= int(meses) <= 24:
        return None, 'La duración va de 1 a 24 meses.'
    if db.one('fut_promo_codes', 'codigo existe', codigo=codigo):
        return None, f'El código {codigo} ya existe.'

    fila = db.insert('fut_promo_codes', {
        'codigo': codigo,
        'meses': int(meses),
        'max_usos': max(1, int(max_usos or 1)),
        'usos': 0,
        'para_rol': para_rol if para_rol in ('cualquiera', 'paciente', 'especialista')
                    else 'cualquiera',
        'vence': vence or None,
        'activo': True,
        'nota': (nota or '')[:300],
        'creado_por': creado_por,
        'creado': _iso(_ahora()),
    }, 'crear codigo')
    if not fila:
        return None, 'No se pudo guardar el código.'
    return fila, None


def canjear(usuario, codigo):
    """Canjea un código y activa Pro. Devuelve (meses, error).

    Comprueba en este orden: que exista, que esté activo, que no haya caducado,
    que queden cupos, que sea para su rol y que no tenga ya un canje vigente.
    Cada motivo tiene su propio mensaje: «código no válido» a secas hace que la
    gente escriba al soporte para preguntar cuál de las seis cosas falló.
    """
    from futbol import db

    codigo = (codigo or '').strip().upper()
    if not codigo:
        return None, 'Escribe el código.'

    fila = db.one('fut_promo_codes', 'canjear', codigo=codigo)
    if not fila:
        return None, 'Ese código no existe. Revisa que esté bien escrito.'
    if not fila.get('activo'):
        return None, 'Ese código ya no está en uso.'

    vence = _parse(fila.get('vence'))
    if vence and vence < _ahora():
        return None, 'Ese código caducó.'
    if int(fila.get('usos') or 0) >= int(fila.get('max_usos') or 1):
        return None, 'Ese código ya se usó el número de veces permitido.'

    para = fila.get('para_rol') or 'cualquiera'
    if para != 'cualquiera' and para != getattr(usuario, 'role', ''):
        cual = 'entrenadores' if para == 'especialista' else 'jugadores'
        return None, f'Ese código es solo para {cual}.'

    previo = db.one('fut_promo_uses', 'canje previo', user_id=usuario.id)
    if previo:
        hasta_previo = _parse(previo.get('pro_hasta'))
        if hasta_previo and hasta_previo > _ahora():
            return None, ('Ya tienes un código activo. Podrás canjear otro '
                          f'a partir del {hasta_previo.date().strftime("%d/%m/%Y")}.')

    meses = int(fila.get('meses') or 1)
    hasta = activar(usuario.id, meses=meses, origen='codigo', codigo=codigo)
    if not hasta:
        return None, 'No se pudo activar. Inténtalo de nuevo.'

    # El contador sube DESPUÉS de activar: si algo falla arriba, el cupo no se
    # gasta. Dos personas canjeando el último cupo a la vez es un riesgo
    # asumido aquí (haría falta un bloqueo de fila) y como mucho regala un mes.
    db.update('fut_promo_codes', {'usos': int(fila.get('usos') or 0) + 1},
              'gastar cupo', id=fila['id'])

    datos_uso = {
        'code_id': fila['id'], 'user_id': usuario.id, 'codigo': codigo,
        'pro_hasta': _iso(hasta), 'creado': _iso(_ahora()),
    }
    if previo:
        db.update('fut_promo_uses', datos_uso, 'canje up', id=previo['id'])
    else:
        db.insert('fut_promo_uses', datos_uso, 'canje')

    import avisos
    avisos.aviso_codigo(usuario, codigo, meses)
    return meses, None


def codigos(incluir_agotados=True):
    """Todos los códigos, con los cupos que quedan, para el panel."""
    from futbol import db
    filas = db.rows('fut_promo_codes', 'codigos', _order='creado', _desc=True) or []
    ahora = _ahora()
    salida = []
    for f in filas:
        usos, tope = int(f.get('usos') or 0), int(f.get('max_usos') or 1)
        vence = _parse(f.get('vence'))
        f['_restantes'] = max(0, tope - usos)
        f['_caducado'] = bool(vence and vence < ahora)
        f['_agotado'] = usos >= tope
        f['_vigente'] = bool(f.get('activo')) and not f['_caducado'] and not f['_agotado']
        f['_fecha'] = db.parse_fecha(f.get('creado'))
        if incluir_agotados or f['_vigente']:
            salida.append(f)
    return salida


def canjes(limite=200):
    """Quién canjeó qué y hasta cuándo le vale."""
    from futbol import db
    filas = db.rows('fut_promo_uses', 'canjes', _order='creado', _desc=True,
                    _limit=limite) or []
    if not filas:
        return []
    ids = list({f['user_id'] for f in filas if f.get('user_id')})
    personas = db.q(
        lambda: db.sb().table('usuarios').select('id, nombre, correo, rol')
        .in_('id', ids).execute().data or [], [], 'personas canje')
    por_id = {p['id']: p for p in personas}
    ahora = _ahora()
    for f in filas:
        f['_usuario'] = por_id.get(f.get('user_id'), {})
        hasta = _parse(f.get('pro_hasta'))
        f['_vigente'] = bool(hasta and hasta > ahora)
        f['_hasta'] = db.parse_fecha(f.get('pro_hasta'))
        f['_fecha'] = db.parse_fecha(f.get('creado'))
    return filas


# ═══════════════════════ MANTENIMIENTO ═══════════════════════
def caducar_vencidos():
    """Baja a gratuito a quien se le pasó la fecha.

    Se llama al entrar al panel en vez de con un cron: la app corre en Vercel
    y en un contenedor del VPS, donde un proceso de fondo no sobrevive a un
    despliegue. Además `roles.es_pro()` ya comprueba la fecha en cada petición,
    así que esto solo pone al día la columna para que el panel no engañe.
    """
    from futbol import db

    filas = db.rows('usuarios', 'pro vigentes', tier='pro') or []
    ahora, caducados = _ahora(), []
    for f in filas:
        hasta = _parse(f.get('pro_hasta'))
        if hasta and hasta < ahora:
            desactivar(f['id'], 'vencido')
            caducados.append(f)

    if caducados:
        import avisos
        nombres = ', '.join(f.get('nombre') or f.get('correo') or '?' for f in caducados[:10])
        avisos.avisar('baja', f'{len(caducados)} suscripción(es) vencida(s)',
                      nombres, correo=len(caducados) > 0)
    return caducados
