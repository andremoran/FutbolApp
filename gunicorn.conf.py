# -*- coding: utf-8 -*-
"""Configuración de gunicorn para FutbolApp."""
import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Workers sincronos: la app hace poco I/O concurrente y así el consumo de
# memoria es predecible en un VPS pequeño. Tope de 4 para no ahogar 2 vCPU.
workers = min(4, multiprocessing.cpu_count() * 2 + 1)
threads = 2
worker_class = 'gthread'

# Las llamadas a Gemini pueden tardar; 60 s evita que gunicorn mate la petición
# justo cuando la IA está respondiendo.
timeout = 75
graceful_timeout = 30
keepalive = 5

# Reciclar workers cada tantas peticiones corta cualquier fuga lenta de memoria.
max_requests = 800
max_requests_jitter = 100

accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sus'

# La app va DETRÁS del proxy de Dokploy: hay que confiar en sus cabeceras para
# que url_for(_external=True) genere https y no http.
forwarded_allow_ips = '*'
proxy_protocol = False
