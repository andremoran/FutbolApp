# -*- coding: utf-8 -*-
"""
api/index.py — Punto de entrada para Vercel.

Vercel busca una app WSGI llamada `app` dentro de api/. Aquí solo se añade la
raíz del proyecto al path y se reexporta la app de Flask: toda la lógica sigue
viviendo en app.py, así que el mismo código corre en Vercel, en Docker o en local.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from app import app  # noqa: E402,F401  (Vercel lo detecta por el nombre)
