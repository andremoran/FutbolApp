# -*- coding: utf-8 -*-
"""
FutbolApp (ProFoot Assistant) — aplicación web independiente.

Antes vivía dentro de ElectroBiomed; ahora es una app propia con su base de
datos, su autenticación y su cobro. No importa nada de aquella plataforma.

Arranque local:   python app.py
En producción:    gunicorn -c gunicorn.conf.py app:app
"""
import logging
import os
import secrets

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for, jsonify
from flask_login import LoginManager, current_user
from supabase import create_client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('futbolapp')


# ─── Aplicación ──────────────────────────────────────────────────────────────
app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_urlsafe(48),
    # La app va detrás del proxy de Dokploy con HTTPS: la cookie viaja solo por TLS.
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('FORZAR_HTTPS', '1') == '1',
    MAX_CONTENT_LENGTH=12 * 1024 * 1024,     # 12 MB por subida
    TEMPLATES_AUTO_RELOAD=False,
    JSON_SORT_KEYS=False,
)

ES_PRODUCCION = os.getenv('ENTORNO', 'produccion') == 'produccion'


# ─── Supabase ────────────────────────────────────────────────────────────────
SUPABASE_URL = (os.getenv('SUPABASE_URL') or '').strip().rstrip('/')
SUPABASE_KEY = (os.getenv('SUPABASE_KEY') or '').strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning('Faltan SUPABASE_URL / SUPABASE_KEY: la app arranca pero no guardará nada.')
    supabase = None
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info('Supabase conectado: %s', SUPABASE_URL)


# ─── Sesiones ────────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.entrar'
login_manager.login_message = 'Entra para continuar.'
login_manager.login_message_category = 'info'


# ─── CSRF (patrón "synchronizer token", sin dependencias) ────────────────────
def csrf_token():
    tok = session.get('_csrf')
    if not tok:
        tok = secrets.token_urlsafe(32)
        session['_csrf'] = tok
    return tok


def csrf_ok():
    enviado = request.form.get('_csrf') or request.headers.get('X-CSRFToken')
    return bool(enviado) and enviado == session.get('_csrf')


@app.context_processor
def _inyectar():
    """Lo que toda plantilla puede dar por hecho.

    `fut_es_pro` y `fut_es_admin` gobiernan los candados de la interfaz; la
    comprobación de verdad la hacen los decoradores de roles.py en el servidor,
    esto solo decide qué se dibuja.
    """
    import roles

    autenticado = bool(getattr(current_user, 'is_authenticated', False))
    return {
        'csrf_token': csrf_token,
        'fut_es_entrenador': autenticado and getattr(current_user, 'role', '') == 'especialista',
        'fut_es_pro': roles.es_pro(current_user) if autenticado else False,
        'fut_es_admin': roles.es_admin(current_user) if autenticado else False,
        'fut_rol': roles.clave_de(current_user) if autenticado else None,
        'fut_rol_etiqueta': roles.etiqueta_de(current_user) if autenticado else '',
        'fut_roles': roles.ROLES,
    }


# ─── Cuentas bloqueadas ──────────────────────────────────────────────────────
@app.before_request
def _echar_bloqueados():
    """Corta la sesión de quien el administrador acaba de bloquear.

    `login_user` ya impide entrar a una cuenta bloqueada, pero eso solo actúa
    al iniciar sesión: sin esto, alguien con la sesión abierta seguiría dentro
    hasta que cerrara el navegador.
    """
    from flask_login import logout_user

    if not getattr(current_user, 'is_authenticated', False):
        return None
    if not getattr(current_user, 'bloqueado', False):
        return None
    if request.endpoint in ('auth.logout', 'auth.entrar', 'static', 'salud'):
        return None

    logout_user()
    session.clear()
    from flask import flash
    flash('Tu cuenta está bloqueada. Escríbenos para reactivarla.', 'error')
    return redirect(url_for('auth.entrar'))


# ─── Cabeceras de seguridad ──────────────────────────────────────────────────
@app.after_request
def _cabeceras(resp):
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    resp.headers.setdefault('Permissions-Policy',
                            'geolocation=(self), camera=(self), microphone=()')
    if ES_PRODUCCION:
        resp.headers.setdefault('Strict-Transport-Security',
                                'max-age=31536000; includeSubDomains')
    return resp


# ─── Módulos ─────────────────────────────────────────────────────────────────
from usuarios import User, cargar_usuario           # noqa: E402
from auth import bp as auth_bp                      # noqa: E402
from pagos import bp as pagos_bp                    # noqa: E402
from admin import bp as admin_bp                    # noqa: E402
from futbol import registrar_futbol                 # noqa: E402

login_manager.user_loader(cargar_usuario)

app.register_blueprint(auth_bp)
app.register_blueprint(pagos_bp)
app.register_blueprint(admin_bp)
registrar_futbol(app, supabase)


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.entrar'))
    return redirect(url_for('futbol.home'))


@app.route('/salud')
def salud():
    """Sonda para Dokploy / Traefik. No toca la base de datos."""
    return {'ok': True, 'app': 'futbolapp'}, 200


@app.errorhandler(404)
def _404(_e):
    if current_user.is_authenticated:
        return redirect(url_for('futbol.home'))
    return redirect(url_for('auth.entrar'))


@app.errorhandler(500)
def _500(e):
    logger.error('Error 500 en %s: %s', request.path, e, exc_info=True)
    #  A una llamada de /api/ hay que responderle JSON. Devolverle la pagina de
    #  error en HTML hacia que PF.api intentara leerla como JSON y el usuario
    #  viera un fallo de sintaxis en vez de lo que paso. Solo `api.py` tenia su
    #  propia red (@api); los otros seis modulos, con 29 endpoints de
    #  escritura, caian aqui.
    if request.path.startswith('/api/'):
        return jsonify({'error': 'No se pudo completar la accion. '
                                 'Vuelve a intentarlo.'}), 500
    from flask import render_template
    return render_template('error.html', hide_tabbar=True), 500


if __name__ == '__main__':
    puerto = int(os.getenv('PORT', '5000'))
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SESSION_COOKIE_SECURE'] = False      # en local no hay HTTPS
    print(f'ProFoot Assistant en http://localhost:{puerto}')
    app.run(host='0.0.0.0', port=puerto, debug=True)
