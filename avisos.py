# -*- coding: utf-8 -*-
"""
avisos.py — Lo que tienen que enterarse los administradores.

Cada alta, cada pago, cada canje de código y cada baja deja DOS rastros:

  1. Una fila en `fut_notificaciones`  → la bandeja del panel. No se pierde,
     no se va a spam y queda como historial auditable.
  2. Un correo a los tres administradores → para enterarse sin abrir el panel.

Son dos porque si solo hubiera correo, un filtro de Gmail borraría la única
prueba de un cobro; y si solo hubiera bandeja, nadie se enteraría hasta entrar.

El correo se manda en un hilo aparte: un SMTP lento no puede dejar colgado al
usuario que acaba de pagar.
"""
import logging
import os
import smtplib
import threading
from datetime import datetime, timezone
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587') or 587)
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
APP_URL = (os.getenv('APP_LIVE_URL') or '').rstrip('/')

# Arranque en frío: si aún no hay ningún usuario marcado como administrador en
# la base, los avisos van a estos correos.
ADMIN_EMAILS_ENV = [c.strip().lower()
                    for c in (os.getenv('ADMIN_EMAILS', '') or '').split(',')
                    if c.strip()]

ICONO = {
    'alta':   '🆕', 'pago':  '💳', 'deuna': '📲', 'codigo': '🎟️',
    'baja':   '🚪', 'error': '⚠️', 'info':  'ℹ️',
}


def _ahora():
    return datetime.now(timezone.utc).isoformat()


# ─── Destinatarios ──────────────────────────────────────────────────────────
def administradores():
    """Los usuarios marcados como administradores, con su correo y su nombre."""
    from futbol import db
    filas = db.rows('usuarios', 'admins', es_admin=True) or []
    return [f for f in filas if f.get('correo')]


def correos_admin():
    """A dónde se manda el aviso. Nunca devuelve vacío si hay .env configurado."""
    correos = [(f.get('correo') or '').lower() for f in administradores()]
    for c in ADMIN_EMAILS_ENV:
        if c not in correos:
            correos.append(c)
    return [c for c in correos if c]


# ─── Registrar + avisar ─────────────────────────────────────────────────────
def avisar(tipo, titulo, detalle='', usuario=None, importe=None, datos=None,
           correo=True):
    """Deja el aviso en la bandeja y, si procede, lo manda por correo.

    Nunca lanza: un fallo avisando no puede tumbar un cobro que ya se hizo.
    """
    from futbol import db

    uid = None
    if usuario is not None:
        uid = usuario if isinstance(usuario, str) else getattr(usuario, 'id', None)

    fila = {
        'tipo': tipo, 'titulo': titulo[:200], 'detalle': (detalle or '')[:2000],
        'user_id': uid, 'importe': str(importe) if importe is not None else None,
        'datos': datos or {}, 'leida': False, 'creado': _ahora(),
    }
    try:
        db.insert('fut_notificaciones', fila, 'aviso')
    except Exception as e:                                   # pragma: no cover
        logger.error('No se pudo guardar el aviso: %s', e)

    logger.info('AVISO %s · %s · %s', tipo, titulo, detalle[:120])

    if correo:
        _enviar_en_segundo_plano(tipo, titulo, detalle, importe)
    return fila


def _enviar_en_segundo_plano(tipo, titulo, detalle, importe):
    destinos = correos_admin()
    if not destinos:
        logger.warning('Aviso sin destinatarios: no hay administradores.')
        return
    if not (SMTP_SERVER and EMAIL_USER and EMAIL_PASSWORD):
        logger.warning('SMTP sin configurar; el aviso solo queda en la bandeja.')
        return

    hilo = threading.Thread(target=_enviar, daemon=True,
                            args=(destinos, tipo, titulo, detalle, importe))
    hilo.start()


def _enviar(destinos, tipo, titulo, detalle, importe):
    icono = ICONO.get(tipo, 'ℹ️')
    lineas = [f'{icono}  {titulo}', '']
    if detalle:
        lineas += [detalle, '']
    if importe:
        lineas += [f'Importe: {importe}', '']
    if APP_URL:
        lineas += [f'Panel: {APP_URL}/admin', '']
    lineas += ['—', 'ProFoot Assistant · aviso automático']

    msg = MIMEText('\n'.join(lineas), 'plain', 'utf-8')
    msg['Subject'] = f'{icono} ProFoot · {titulo}'
    msg['From'] = EMAIL_USER
    msg['To'] = ', '.join(destinos)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as s:
            s.starttls()
            s.login(EMAIL_USER, EMAIL_PASSWORD)
            s.send_message(msg)
        logger.info('Aviso enviado a %d administrador(es)', len(destinos))
    except Exception as e:
        logger.error('No se pudo enviar el aviso por correo: %s', e)


# ─── Atajos con el texto ya redactado ───────────────────────────────────────
def aviso_alta(usuario_fila):
    rol = ('especialista' if usuario_fila.get('rol') == 'especialista' else 'paciente')
    etiqueta = 'Entrenador' if rol == 'especialista' else 'Jugador'
    extra = ''
    if usuario_fila.get('codigo_equipo'):
        extra = f'\nCódigo de equipo: {usuario_fila["codigo_equipo"]}'
    avisar('alta',
           f'Cuenta nueva: {usuario_fila.get("nombre", "?")}',
           f'{etiqueta} · {usuario_fila.get("correo", "")}'
           f'{("· " + usuario_fila["telefono"]) if usuario_fila.get("telefono") else ""}{extra}',
           usuario=usuario_fila.get('id'),
           datos={'rol': rol, 'correo': usuario_fila.get('correo')})


def aviso_pago(usuario, plan, importe, proveedor, referencia=''):
    avisar('pago',
           f'Pago recibido · {plan}',
           f'{getattr(usuario, "name", "?")} ({getattr(usuario, "correo", "")})\n'
           f'Pasarela: {proveedor}'
           f'{(chr(10) + "Referencia: " + referencia) if referencia else ""}',
           usuario=usuario, importe=importe,
           datos={'plan': plan, 'proveedor': proveedor, 'referencia': referencia})


def aviso_deuna_pendiente(usuario, plan, importe, referencia):
    avisar('deuna',
           f'Comprobante DeUna por revisar · {plan}',
           f'{getattr(usuario, "name", "?")} ({getattr(usuario, "correo", "")})\n'
           f'Referencia: {referencia or "sin número"}\n'
           'Entra al panel para verificarlo y activar la cuenta.',
           usuario=usuario, importe=importe,
           datos={'plan': plan, 'referencia': referencia})


def aviso_codigo(usuario, codigo, meses):
    avisar('codigo',
           f'Código canjeado: {codigo}',
           f'{getattr(usuario, "name", "?")} ({getattr(usuario, "correo", "")}) '
           f'activó {meses} mes(es) de Pro.',
           usuario=usuario, datos={'codigo': codigo, 'meses': meses})


def aviso_baja(usuario_fila, motivo):
    avisar('baja',
           f'Suscripción caída: {usuario_fila.get("nombre", "?")}',
           f'{usuario_fila.get("correo", "")}\nMotivo: {motivo}',
           usuario=usuario_fila.get('id'), datos={'motivo': motivo})


# ─── Lectura desde el panel ─────────────────────────────────────────────────
def sin_leer():
    from futbol import db
    return len(db.rows('fut_notificaciones', 'sin leer', leida=False) or [])


def ultimos(limite=60, solo_sin_leer=False):
    from futbol import db
    filtros = {'_order': 'creado', '_desc': True, '_limit': limite}
    if solo_sin_leer:
        filtros['leida'] = False
    filas = db.rows('fut_notificaciones', 'avisos', **filtros) or []
    for f in filas:
        f['_icono'] = ICONO.get(f.get('tipo'), 'ℹ️')
        f['_fecha'] = db.parse_fecha(f.get('creado'))
    return filas


def marcar_leidas(ids, por=None):
    from futbol import db
    for nid in ids or []:
        db.update('fut_notificaciones',
                  {'leida': True, 'leida_por': por}, 'marcar leida', id=nid)
