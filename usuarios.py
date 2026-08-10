# -*- coding: utf-8 -*-
"""
usuarios.py — El usuario de FutbolApp y el hash de contraseñas.

Tabla propia `usuarios` en el Supabase de FutbolApp. Los roles conservan los
nombres que ya usaban las plantillas para no reescribirlas:
  'especialista' = entrenador   ·   'paciente' = jugador

Sobre eso, `tier` ('free' | 'pro') y `es_admin` componen los cinco roles del
producto. Quién puede hacer qué se decide en roles.py, no aquí.
"""
import hashlib
import hmac
import logging
import os
import secrets

from flask_login import UserMixin

logger = logging.getLogger(__name__)

ADMIN_EMAILS = {c.strip().lower() for c in (os.getenv('ADMIN_EMAILS', '') or '').split(',') if c.strip()}

# Caché del arranque en frío. Un módulo se importa una vez por proceso, así que
# la comprobación se hace una sola vez y no en cada carga de usuario.
_ADMINS_EN_BASE = None


def _hay_admins():
    """¿Ya hay algún administrador nombrado en la base?

    ADMIN_EMAILS solo vale mientras NO lo haya: si valiera siempre, cualquiera
    que se registrara con uno de esos correos entraría al panel, y basta con
    que uno de ellos sea una dirección que nadie controle para regalar el
    acceso a usuarios, cobros y códigos. En cuanto hay un administrador de
    verdad, la lista del entorno deja de conceder nada.
    """
    global _ADMINS_EN_BASE
    if _ADMINS_EN_BASE is None:
        from futbol import db
        if db.sb() is None:
            return False          # sin base no se decide nada: no se cachea
        _ADMINS_EN_BASE = bool(db.rows('usuarios', 'hay admins', es_admin=True))
    return _ADMINS_EN_BASE


def olvidar_cache_admins():
    """Se llama al nombrar o quitar un administrador."""
    global _ADMINS_EN_BASE
    _ADMINS_EN_BASE = None


# ─── Contraseñas ─────────────────────────────────────────────────────────────
# scrypt de la biblioteca estándar: sin dependencias y resistente a GPU.
# Formato guardado:  scrypt$<n>$<r>$<p>$<sal_hex>$<hash_hex>
_N, _R, _P = 2 ** 14, 8, 1


def hash_password(password: str) -> str:
    sal = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode('utf-8'), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return f'scrypt${_N}${_R}${_P}${sal.hex()}${dk.hex()}'


def verificar_password(guardado: str, password: str) -> bool:
    if not guardado or not password:
        return False
    try:
        algo, n, r, p, sal_hex, hash_hex = guardado.split('$')
        if algo != 'scrypt':
            return False
        dk = hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(sal_hex),
                            n=int(n), r=int(r), p=int(p), dklen=len(hash_hex) // 2)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ─── Usuario ─────────────────────────────────────────────────────────────────
class User(UserMixin):
    def __init__(self, fila: dict):
        d = fila or {}
        self.id = str(d.get('id', ''))
        self.name = d.get('nombre') or 'Usuario'
        self.correo = (d.get('correo') or '').lower()
        self.username = self.correo
        self.role = d.get('rol') or 'paciente'
        self.telefono = d.get('telefono')
        self.profile_photo = d.get('foto')
        self.codigo_profesional = d.get('codigo_equipo')
        self.last_weight = d.get('peso')
        self.last_height = d.get('estatura')
        self.gender = d.get('genero')
        self.activo = bool(d.get('activo', False))
        self.plan = d.get('plan') or 'basico'
        self.creado = d.get('creado')
        self.anio_nacimiento = d.get('anio_nacimiento')
        self.club = d.get('club')

        # ── Los cinco roles ──
        self.tier = (d.get('tier') or 'free').lower()
        self.pro_hasta = d.get('pro_hasta')
        self.pro_origen = d.get('pro_origen')
        self.codigo_promo = d.get('codigo_promo')
        self.bloqueado = bool(d.get('bloqueado', False))
        self._es_admin = bool(d.get('es_admin')) or (
            self.correo in ADMIN_EMAILS and not _hay_admins())

    def is_especialista(self):
        return self.role == 'especialista'

    def is_paciente(self):
        return self.role == 'paciente'

    def is_admin(self):
        return self._es_admin

    @property
    def is_active(self):
        """Flask-Login: una cuenta bloqueada por el administrador no entra.

        Tiene que ser PROPIEDAD, no método: Flask-Login lee `user.is_active`
        sin llamarlo, y un método enlazado siempre es verdadero — la cuenta
        bloqueada entraría igual y nadie se enteraría.
        """
        return not self.bloqueado

    # ── Atajos que usan las plantillas ──
    @property
    def es_pro(self):
        from roles import es_pro
        return es_pro(self)

    @property
    def rol_clave(self):
        from roles import clave_de
        return clave_de(self)

    @property
    def rol_etiqueta(self):
        from roles import etiqueta_de
        return etiqueta_de(self)

    @property
    def iniciales(self):
        partes = (self.name or '').strip().split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[1][0]).upper()
        return (self.name or '?')[:2].upper()


def cargar_usuario(user_id):
    """user_loader de Flask-Login."""
    from futbol import db
    if not user_id or db.sb() is None:
        return None
    fila = db.one('usuarios', 'cargar usuario', id=user_id)
    return User(fila) if fila else None


def buscar_por_correo(correo):
    from futbol import db
    if db.sb() is None:
        return None
    return db.one('usuarios', 'buscar correo', correo=(correo or '').strip().lower())
