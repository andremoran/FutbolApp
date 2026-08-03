# -*- coding: utf-8 -*-
"""
usuarios.py — El usuario de FutbolApp y el hash de contraseñas.

Tabla propia `usuarios` en el Supabase de FutbolApp. Los roles conservan los
nombres que ya usaban las plantillas para no reescribirlas:
  'especialista' = entrenador   ·   'paciente' = jugador
"""
import hashlib
import hmac
import logging
import os
import secrets

from flask_login import UserMixin

logger = logging.getLogger(__name__)

ADMIN_EMAILS = {c.strip().lower() for c in (os.getenv('ADMIN_EMAILS', '') or '').split(',') if c.strip()}


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
        self._es_admin = self.correo in ADMIN_EMAILS

    def is_especialista(self):
        return self.role == 'especialista'

    def is_paciente(self):
        return self.role == 'paciente'

    def is_admin(self):
        return self._es_admin

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
