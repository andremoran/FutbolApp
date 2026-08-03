# ============================================================
#  FutbolApp (ProFoot Assistant)
#  Imagen para Dokploy / cualquier runtime de contenedores.
# ============================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5000

WORKDIR /app

# Las dependencias primero: así el build reusa la capa cuando solo cambia el código.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# La app NO corre como root.
RUN useradd --create-home --shell /usr/sbin/nologin profoot \
    && chown -R profoot:profoot /app
USER profoot

EXPOSE 5000

# Sonda propia: Dokploy/Traefik solo enrutan cuando /salud responde.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/salud', timeout=4).status==200 else 1)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
