# ProFoot Assistant — FutbolApp

Aplicación web de gestión de equipos y jugadores de fútbol. Réplica en web de la
app móvil ProFoot Assistant: mismas pestañas, mismo diseño, instalable en la
pantalla de inicio del teléfono.

**Stack:** Flask · Supabase · PayPal · Gemini (nivel gratuito).

---

## Puesta en marcha en 4 pasos

### 1. Base de datos

En [supabase.com](https://supabase.com) → tu proyecto → **SQL Editor** → pega
todo el contenido de [`sql/schema.sql`](sql/schema.sql) → **Run**.

Crea 23 tablas. Es idempotente: se puede volver a correr sin romper nada.

Comprobación:

```sql
select table_name from information_schema.tables
where table_schema = 'public' order by 1;
```

### 2. Variables de entorno

```bash
cp .env.example .env
```

Rellena como mínimo `SUPABASE_URL`, `SUPABASE_KEY` (clave `service_role`),
`SECRET_KEY` y `CODIGOS_ENTRENADOR`.

### 3. Planes de cobro (opcional, para cobrar con tarjeta)

```bash
python crear_planes_paypal.py            # vista previa, no crea nada
python crear_planes_paypal.py --crear    # los crea de verdad
```

> ⚠️ Con `PAYPAL_ENV=live` esto da de alta planes de cobro **reales**.
> Revisa los precios en `pagos.py` → `PLANES` antes de ejecutarlo.

Sin este paso la app funciona igual; solo queda desactivado el botón de pagar.

### 4. Arrancar

```bash
pip install -r requirements.txt
python app.py           # http://localhost:5000
```

---

## Despliegue en Dokploy

El VPS ya tiene Dokploy con Traefik: emite el certificado HTTPS solo.

1. **Panel de Dokploy** → *Create Application* → *Provider: GitHub* → repo `FutbolApp`, rama `main`.
2. **Build Type: Dockerfile** (el repo trae el suyo).
3. **Environment**: pega el contenido de tu `.env`. En producción:
   ```
   ENTORNO=produccion
   FORZAR_HTTPS=1
   ```
4. **Domains** → añade el dominio, puerto **5000**, activa *HTTPS* y *Certificate: Let's Encrypt*.
5. **Deploy**.

Traefik solo enruta cuando `/salud` responde 200, así que un despliegue roto no
tumba el que está sirviendo.

### Sin dominio todavía

Se puede usar un dominio comodín que resuelve a la IP y admite Let's Encrypt:

```
147-93-181-76.sslip.io
```

Sirve para probar el cobro con tarjeta antes de comprar el dominio definitivo.

---

## Cómo funciona por dentro

### Roles

| En la app | En la base de datos |
|---|---|
| Entrenador | `usuarios.rol = 'especialista'` |
| Jugador | `usuarios.rol = 'paciente'` |

Un entrenador se registra con un código de `CODIGOS_ENTRENADOR` y recibe su
propio **código de equipo**. Los jugadores se registran con ese código y entran
directo a su plantilla (`fut_plantilla`).

### Estructura

```
app.py                  Flask, configuración, Supabase, sesiones, CSRF
usuarios.py             Modelo de usuario y hash scrypt de contraseñas
auth.py                 Registro, acceso, recuperación de contraseña
pagos.py                Cobro con tarjeta (PayPal Subscriptions)
futbol/
  db.py                 Capa de datos (tolerante a tablas ausentes)
  player.py             5 pestañas del jugador
  coach.py              5 pestañas del entrenador
  mental.py             Salud mental
  social.py             Mensajes, partidos y observaciones
  api.py                Endpoints JSON
  ia.py                 Asistente de IA
  account.py            Perfil y planes
templates/              37 plantillas Jinja
static/                 profoot.css, profoot.js, logo, iconos, manifest PWA
sql/schema.sql          Esquema completo
```

### Decisiones que conviene conocer

- **El diseño es un puerto 1:1** de `theme/design.ts` y `components/ui.tsx` de la
  app nativa. Los números de `static/profoot.css` no son aproximaciones.
- **En móvil se usa la barra de pestañas NATIVA**, no la variante web de la app:
  jugador flotante y redondeada, entrenador plana y alta. Es lo que hace que se
  sienta la app y no una web.
- **Salud mental: el entrenador NUNCA ve las respuestas**, solo un semáforo.
  Las consultas del lado del coach piden columnas explícitas y jamás
  `respuestas`. Si se rompe esa frontera, el módulo deja de servir porque los
  jugadores dejan de ser honestos.
- **La capa de datos no revienta si falta una tabla**: devuelve vacío y la
  pantalla se ve «sin datos». Así la app arranca aunque el esquema no esté aplicado.
- **La IA usa solo el nivel gratuito de Gemini**, y si falla responde con un
  análisis calculado de los datos reales del usuario — nunca un mensaje de error.
- **Los datos de la tarjeta nunca pasan por el servidor**: los captura el SDK de
  PayPal. Nosotros verificamos la suscripción contra su API antes de activar.

---

## Verificación

```bash
python _probar.py
```

Recorre las 38 pantallas con un usuario simulado de cada rol y comprueba que
todas responden 200.
