# -*- coding: utf-8 -*-
"""
auth.py — Registro, acceso y recuperación de contraseña de FutbolApp.

Es propia: ya no depende de ElectroBiomed. Un ENTRENADOR se registra con un
código de alta (variable CODIGOS_ENTRENADOR) y al hacerlo recibe su propio
código de equipo; un JUGADOR se registra con el código de equipo de su
entrenador y queda vinculado en el acto.
"""
import logging
import os
import re
import secrets
import time
from datetime import datetime, timezone

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from usuarios import User, buscar_por_correo, hash_password, verificar_password

logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__)

CODIGOS_ENTRENADOR = {c.strip().upper()
                      for c in (os.getenv('CODIGOS_ENTRENADOR', '') or '').split(',')
                      if c.strip()}

RE_CORREO = re.compile(r'^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$')

# Freno a la fuerza bruta: 8 intentos fallidos por IP en 15 minutos.
_intentos = {}
_LIMITE, _VENTANA = 8, 900


def _limitado(ip):
    ahora = time.time()
    fallos = [t for t in _intentos.get(ip, []) if ahora - t < _VENTANA]
    _intentos[ip] = fallos
    return len(fallos) >= _LIMITE


def _apuntar_fallo(ip):
    _intentos.setdefault(ip, []).append(time.time())


def _ip():
    return (request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            or request.remote_addr or '?')


def _csrf_ok():
    from app import csrf_ok
    return csrf_ok()


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _nuevo_codigo_equipo():
    """Código corto, legible y sin caracteres que se confundan (0/O, 1/I)."""
    from futbol import db
    alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    for _ in range(12):
        codigo = ''.join(secrets.choice(alfabeto) for _ in range(6))
        if not db.one('usuarios', 'codigo libre', codigo_equipo=codigo):
            return codigo
    return secrets.token_hex(4).upper()


# ═══════════════════════ PANTALLAS ═══════════════════════
@bp.route('/entrar')
def entrar():
    if current_user.is_authenticated:
        return redirect(url_for('futbol.home'))
    return render_template('auth_login.html', hide_tabbar=True)


@bp.route('/rol')
def rol():
    if current_user.is_authenticated:
        return redirect(url_for('futbol.home'))
    return render_template('auth_role.html', hide_tabbar=True)


@bp.route('/plan')
def plan():
    """Segundo paso del alta: qué plan.

    Por qué va DESPUÉS del rol y no fundido con él
    ──────────────────────────────────────────────
    Se valoró partir la pantalla de roles en cuatro tarjetas (jugador gratis,
    jugador pro, coach gratis, coach pro). Se descartó: quien acaba de llegar
    todavía no sabe qué hace la app, y pedirle que elija plan a la vez que rol
    le hace elegir a ciegas. Primero QUIÉN ERES —que sí sabe— y luego CUÁNTO
    PAGAS, ya con las ventajas delante.

    Y va antes del formulario, no después, porque el precio tiene que verse
    antes de pedir datos: enseñarlo al final es lo que hace que la gente
    abandone con la cuenta a medio crear.
    """
    if current_user.is_authenticated:
        return redirect(url_for('futbol.home'))

    from admin import ajustes
    import roles

    rol_sel = 'entrenador' if request.args.get('rol') == 'entrenador' else 'jugador'
    es_coach = rol_sel == 'entrenador'
    cfg = ajustes()

    return render_template(
        'auth_plan.html',
        hide_tabbar=True,
        rol_sel=rol_sel, es_coach=es_coach,
        precio=(cfg.get('precio_entrenador') if es_coach else cfg.get('precio_jugador')),
        precio_club=cfg.get('precio_club'),
        limite_plantilla=roles.LIMITE_PLANTILLA_FREE,
        mensajes_ia=roles.IA_MENSAJES_GRATIS,
        aviso=cfg.get('aviso_panel'))


@bp.route('/registro')
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('futbol.home'))

    rol_sel = request.args.get('rol', 'jugador')
    plan_sel = request.args.get('plan', 'free')
    if plan_sel not in ('free', 'pro', 'codigo'):
        plan_sel = 'free'

    return render_template('auth_register.html',
                           hide_tabbar=True,
                           rol_sel=rol_sel,
                           plan_sel=plan_sel,
                           role='especialista' if rol_sel == 'entrenador' else 'paciente',
                           codigo=request.args.get('codigo', ''))


@bp.route('/api/clubes', methods=['POST'])
def api_clubes():
    """Recoge la solicitud de un club y avisa a los administradores.

    Es un formulario público (sin sesión: quien pregunta todavía no tiene
    cuenta), así que se limita por IP con el mismo freno que el acceso — si no,
    es un buzón abierto para spam.
    """
    from flask import jsonify

    ip = _ip()
    if _limitado(ip):
        return jsonify({'error': 'Demasiados envíos. Inténtalo en un rato.'}), 429

    d = request.get_json(silent=True) or {}
    club = (d.get('club') or '').strip()
    nombre = (d.get('nombre') or '').strip()
    contacto = (d.get('contacto') or '').strip()
    if len(club) < 2 or len(nombre) < 2 or len(contacto) < 5:
        return jsonify({'error': 'Faltan el club, tu nombre y un teléfono o correo.'}), 400

    _apuntar_fallo(ip)          # cuenta para el límite, aunque salga bien

    import avisos
    avisos.avisar(
        'info', f'Club interesado: {club[:80]}',
        f'{nombre[:80]}\nContacto: {contacto[:120]}\n'
        f'Categorías: {(d.get("categorias") or "—")[:60]}\n'
        f'Jugadores: {(d.get("jugadores") or "—")[:20]}\n\n'
        f'{(d.get("mensaje") or "")[:800]}',
        datos={'club': club[:80], 'contacto': contacto[:120]})

    return jsonify({'ok': True,
                    'mensaje': 'Recibido. Te escribimos en menos de 24 horas '
                               'para agendar una llamada.'})


@bp.route('/clubes')
def clubes():
    """El plan de Club no se compra con un botón: se agenda.

    Cada club se monta a medida (varias categorías, cuerpo técnico, marca
    propia), así que un cobro automático prometería algo que no se entrega
    solo. Aquí se recogen los datos y se avisa a los administradores.
    """
    from admin import ajustes
    cfg = ajustes()
    return render_template('clubes.html',
                           hide_tabbar=True,
                           desde=cfg.get('precio_club'),
                           whatsapp=cfg.get('contacto_whatsapp'),
                           correo=cfg.get('contacto_correo'))


# ═══════════════════════ ACCESO ═══════════════════════
@bp.route('/login', methods=['POST'])
def login():
    if not _csrf_ok():
        flash('La sesión expiró. Recarga la página e inténtalo de nuevo.', 'error')
        return redirect(url_for('auth.entrar'))

    ip = _ip()
    if _limitado(ip):
        flash('Demasiados intentos. Espera unos minutos e inténtalo de nuevo.', 'error')
        return redirect(url_for('auth.entrar'))

    correo = (request.form.get('correo') or '').strip().lower()
    password = request.form.get('password') or ''

    fila = buscar_por_correo(correo)
    if not fila or not verificar_password(fila.get('password'), password):
        _apuntar_fallo(ip)
        # Mismo mensaje en ambos casos: no revelamos si el correo existe.
        flash('Correo o contraseña incorrectos.', 'error')
        return redirect(url_for('auth.entrar'))

    usuario = User(fila)
    if not login_user(usuario, remember=True):
        # login_user devuelve False cuando la cuenta no está activa.
        flash('Tu cuenta está bloqueada. Escríbenos para reactivarla.', 'error')
        return redirect(url_for('auth.entrar'))

    _intentos.pop(ip, None)
    logger.info('Acceso de %s (%s)', correo, fila.get('rol'))
    return redirect(url_for('futbol.home'))


@bp.route('/logout')
@login_required
def logout():
    # El orden importa: `logout_user()` marca la cookie de "recordarme" para
    # borrarla poniendo `_remember='clear'` EN LA SESIÓN. Si se limpiara la
    # sesión después, se borraría esa marca, la cookie sobreviviría y el
    # usuario volvería a entrar solo en la siguiente petición — en un móvil
    # prestado eso es que no se puede cerrar sesión.
    session.clear()
    logout_user()
    return redirect(url_for('auth.entrar'))


# ═══════════════════════ ALTA ═══════════════════════
@bp.route('/signup', methods=['POST'])
def signup():
    from futbol import db

    if not _csrf_ok():
        flash('La sesión expiró. Recarga la página e inténtalo de nuevo.', 'error')
        return redirect(url_for('auth.rol'))

    rol_form = request.form.get('role', 'paciente')
    es_coach = rol_form == 'especialista'
    plan_sel = request.form.get('plan', 'free')
    if plan_sel not in ('free', 'pro', 'codigo'):
        plan_sel = 'free'
    volver = url_for('auth.registro',
                     rol='entrenador' if es_coach else 'jugador', plan=plan_sel)

    nombre = (request.form.get('name') or '').strip()
    correo = (request.form.get('correo') or '').strip().lower()
    password = request.form.get('password') or ''
    codigo = (request.form.get('codigo_vinculacion') or '').strip().upper()

    # ── Validaciones ──
    if len(nombre) < 3:
        flash('Escribe tu nombre completo.', 'error')
        return redirect(volver)
    if not RE_CORREO.match(correo):
        flash('Ese correo no parece válido.', 'error')
        return redirect(volver)
    if len(password) < 8:
        flash('La contraseña debe tener al menos 8 caracteres.', 'error')
        return redirect(volver)
    if buscar_por_correo(correo):
        flash('Ese correo ya está registrado. Entra con tu contraseña.', 'error')
        return redirect(url_for('auth.entrar'))

    entrenador = None
    if es_coach:
        # El código de alta dejó de ser OBLIGATORIO: un entrenador que descubre
        # la app tiene que poder probarla el mismo día. Antes, sin código de un
        # administrador no había forma de entrar, y eso frena el crecimiento en
        # seco. Si trae uno válido se respeta (lo emitió un admin o un club);
        # si trae uno inventado se avisa en vez de dejarle creer que sirvió.
        if codigo and codigo not in CODIGOS_ENTRENADOR:
            flash('Ese código de alta no es válido. Puedes crear la cuenta sin '
                  'código y activar el plan cuando quieras.', 'warning')
            codigo = ''
    else:
        # El jugador puede registrarse SIN código y unirse a un equipo después,
        # desde /unirme. Antes el código era obligatorio y un chico que se
        # bajaba la app sin tenerlo a mano se quedaba fuera.
        if codigo:
            entrenador = db.one('usuarios', 'coach por codigo',
                                codigo_equipo=codigo, rol='especialista')
            if not entrenador:
                flash('Ese código de equipo no existe. Revísalo con tu '
                      'entrenador, o entra ahora y únete al equipo después.',
                      'error')
                return redirect(volver)

    # ── Crear ──
    datos = {
        'nombre': nombre,
        'correo': correo,
        'password': hash_password(password),
        'rol': 'especialista' if es_coach else 'paciente',
        'telefono': (request.form.get('telefono') or '').strip() or None,
        'genero': request.form.get('gender') or None,
        # Toda cuenta nace en el plan gratuito y funcional: nadie tiene que
        # pagar para probar. El Pro se activa con tarjeta, DeUna o código.
        'activo': False,
        'tier': 'free',
        'plan': 'basico',
        'creado': _ahora(),
    }
    if es_coach:
        datos['codigo_equipo'] = _nuevo_codigo_equipo()
        datos['club'] = (request.form.get('especialidad') or '').strip() or None
    else:
        for campo, destino in (('height', 'estatura'), ('weight', 'peso')):
            v = request.form.get(campo)
            if v:
                try:
                    datos[destino] = float(v)
                except ValueError:
                    pass
        anio = request.form.get('birth_year')
        if anio and anio.isdigit():
            datos['anio_nacimiento'] = int(anio)

    nuevo = db.insert('usuarios', datos, 'alta usuario')
    if not nuevo:
        flash('No pudimos crear tu cuenta. Inténtalo de nuevo en un momento.', 'error')
        return redirect(volver)

    # Vincular al equipo del entrenador
    if entrenador:
        db.insert('fut_plantilla', {
            'coach_id': entrenador['id'],
            'player_id': nuevo['id'],
            'activo': True,
            'creado': _ahora(),
        }, 'vincular jugador')

    # Los tres administradores se enteran de cada alta, por correo y en el panel.
    try:
        import avisos
        avisos.aviso_alta(nuevo)
    except Exception as e:                                    # pragma: no cover
        logger.warning('No se pudo avisar del alta: %s', e)

    login_user(User(nuevo), remember=True)

    # A dónde va después según lo que eligió en el paso del plan.
    # El cobro va SIEMPRE después de crear la cuenta, nunca antes: cobrar
    # primero deja pagos huérfanos que no se pueden ligar a nadie y hay que
    # casar a mano. Con la cuenta ya creada, la suscripción nace atada al
    # usuario y el webhook de PayPal sabe a quién activar o desactivar.
    if plan_sel == 'pro':
        flash('Cuenta creada. Elige cómo quieres pagar y ya está.', 'success')
        return redirect(url_for('pagos.elegir',
                                plan='entrenador_pro' if es_coach else 'jugador_pro'))
    if plan_sel == 'codigo':
        flash('Cuenta creada. Canjea tu código y activamos el plan.', 'success')
        return redirect(url_for('futbol.canjear'))

    if entrenador:
        flash(f'¡Listo! Ya eres parte del equipo de {entrenador["nombre"]}.', 'success')
    elif es_coach:
        flash('¡Cuenta creada! Comparte tu código de equipo con tus jugadores.', 'success')
    else:
        flash('¡Cuenta creada! Únete a tu equipo con el código del entrenador.', 'success')
    return redirect(url_for('futbol.home'))


# ═══════════════════════ CONTRASEÑA ═══════════════════════
def _serializador():
    from app import app
    return URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='profoot-reset')


@bp.route('/olvide', methods=['GET', 'POST'])
def olvide():
    if request.method == 'GET':
        return render_template('auth_olvide.html', hide_tabbar=True)

    if not _csrf_ok():
        flash('La sesión expiró. Recarga la página.', 'error')
        return redirect(url_for('auth.olvide'))

    correo = (request.form.get('correo') or '').strip().lower()
    fila = buscar_por_correo(correo)

    if fila:
        # El token incrusta un trozo del hash actual: al cambiar la contraseña
        # el token deja de valer, así que es de un solo uso sin tabla extra.
        firma = (fila.get('password') or '')[-12:]
        token = _serializador().dumps({'id': fila['id'], 'f': firma})
        enlace = url_for('auth.restablecer', token=token, _external=True)
        _enviar_correo_reset(correo, fila.get('nombre') or '', enlace)

    # Respuesta idéntica exista o no la cuenta: no filtramos quién está registrado.
    flash('Si ese correo está registrado, te enviamos un enlace para crear una '
          'contraseña nueva. Revisa tu bandeja y el spam.', 'info')
    return redirect(url_for('auth.entrar'))


@bp.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer(token):
    from futbol import db

    try:
        datos = _serializador().loads(token, max_age=3600)   # 1 hora
    except SignatureExpired:
        flash('El enlace caducó. Pide uno nuevo.', 'error')
        return redirect(url_for('auth.olvide'))
    except BadSignature:
        flash('Ese enlace no es válido.', 'error')
        return redirect(url_for('auth.olvide'))

    fila = db.one('usuarios', 'reset', id=datos.get('id'))
    if not fila or (fila.get('password') or '')[-12:] != datos.get('f'):
        flash('Ese enlace ya se usó. Pide uno nuevo.', 'error')
        return redirect(url_for('auth.olvide'))

    if request.method == 'GET':
        return render_template('auth_reset.html', hide_tabbar=True, token=token)

    if not _csrf_ok():
        flash('La sesión expiró. Recarga la página.', 'error')
        return redirect(url_for('auth.restablecer', token=token))

    password = request.form.get('password') or ''
    if len(password) < 8:
        flash('La contraseña debe tener al menos 8 caracteres.', 'error')
        return redirect(url_for('auth.restablecer', token=token))

    db.update('usuarios', {'password': hash_password(password)}, 'reset pw', id=fila['id'])
    flash('Contraseña actualizada. Ya puedes entrar.', 'success')
    return redirect(url_for('auth.entrar'))


def _enviar_correo_reset(destino, nombre, enlace):
    """Envía el enlace. Si el SMTP no está configurado, solo lo registra."""
    servidor = os.getenv('SMTP_SERVER')
    usuario = os.getenv('EMAIL_USER')
    clave = os.getenv('EMAIL_PASSWORD')
    if not (servidor and usuario and clave):
        logger.warning('SMTP sin configurar; enlace de reset para %s: %s', destino, enlace)
        return

    import smtplib
    from email.mime.text import MIMEText

    cuerpo = (f'Hola {nombre or ""},\n\n'
              'Pediste crear una contraseña nueva en ProFoot Assistant.\n'
              f'Entra aquí (el enlace vale 1 hora):\n\n{enlace}\n\n'
              'Si no fuiste tú, ignora este correo: tu contraseña sigue igual.\n')
    msg = MIMEText(cuerpo, 'plain', 'utf-8')
    msg['Subject'] = 'ProFoot Assistant — nueva contraseña'
    msg['From'] = usuario
    msg['To'] = destino
    try:
        with smtplib.SMTP(servidor, int(os.getenv('SMTP_PORT', '587')), timeout=20) as s:
            s.starttls()
            s.login(usuario, clave)
            s.send_message(msg)
        logger.info('Enlace de reset enviado a %s', destino)
    except Exception as e:
        logger.error('No se pudo enviar el correo de reset: %s', e)
