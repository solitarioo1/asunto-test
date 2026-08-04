# Generador de Asunto + Cuerpo de correo (Memorandums PDF)

Migración del notebook de Colab (`codigo_genear_asunto_contenido.ipynb`) a una web
que se pueda desplegar en un VPS.

## Roadmap (se implementa por pasos)

1. **Unir PDF** — cada PDF de contenido se une con un PDF de firma común
   (10 contenido + 1 firma → 10 PDFs finales). *Pendiente.*
2. **Renombrar PDF** — cada PDF final se renombra como `SINIESTRO_{numero}.pdf`,
   usando el número de siniestro extraído del texto. *Pendiente.*
3. **Exportar PDF** — descarga en `.zip` de todos los PDFs renombrados. *Pendiente.*
4. **Mostrar HTML** — genera el bloque de Asunto + Cuerpo por cada PDF
   (igual que el Colab), para copiar directo al correo. **✅ Hecho**

## Estado actual

- El usuario sube un `.zip`, PDFs sueltos o una carpeta completa (drag & drop o selector).
- Cada archivo se valida por su contenido real (firma `%PDF-` / `PK\x03\x04`), no por su
  extensión — un archivo renombrado para simular un PDF se descarta.
- El formulario está protegido con Cloudflare Turnstile antes de procesar nada.
- Se extraen los campos por regex de cada PDF y se genera el HTML con los bloques de
  Asunto + Cuerpo.

Los pasos 1-3 (unir con firma, renombrar, exportar zip) se agregan en iteraciones
siguientes, ahora sobre la estructura modular en `app/`.

## Estructura

```
app/
  main.py              # crea la app FastAPI, monta /static, incluye el router
  config.py            # carga TURNSTILE_SITE_KEY / TURNSTILE_SECRET_KEY desde .env
  routers/upload.py    # rutas GET / y POST /procesar
  services/
    pdf_extractor.py   # regex + armado de asunto/cuerpo
    file_intake.py      # validación real de PDF/ZIP por firma binaria
    turnstile.py        # verificación del captcha contra Cloudflare
templates/              # HTML (Jinja2), extiende base.html
static/css/              # parciales de CSS (variables, base, layout, components/)
static/js/upload.js      # drag & drop, selección de carpeta
```

## Variables de entorno

Copiar `.env` con:

```
TURNSTILE_SITE_KEY=...
TURNSTILE_SECRET_KEY=...
```

(claves del widget de Cloudflare Turnstile usado para proteger el formulario de subida).

## Stack

- Backend: Python + FastAPI + Jinja2
- PDF: `pypdf`
- Anti-bot: Cloudflare Turnstile
- Frontend: HTML/CSS/JS servidos por el propio backend, sin build step

## Correr en local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abrir `http://127.0.0.1:8000`.

## Correr con Docker (incluye nginx + HTTPS)

`docker-compose.yml` levanta tres servicios: `correos` (la app, no expuesta
directo a internet), `nginx` (reverse proxy en 80/443) y `certbot` (renueva el
certificado automáticamente cada 12h).

Para actualizar tras un cambio de código:

```bash
git pull
docker compose up -d --build
```

## Despliegue en VPS (dominio: `asunto.miagentepersonal.me`)

1. Instalar Docker + Docker Compose en el VPS.
2. Clonar el repo y crear el archivo `.env` en la raíz con `TURNSTILE_SITE_KEY` y
   `TURNSTILE_SECRET_KEY` (no se sube al repo, hay que crearlo manualmente).
3. Confirmar que el dominio ya apunta (registro A) a la IP del VPS, y que los
   puertos 80 y 443 están abiertos en el firewall del VPS.
4. Primer arranque, **en este orden**:
   ```bash
   docker compose up -d --build correos
   bash deploy/init-letsencrypt.sh
   ```
   Ese script emite el certificado real de Let's Encrypt (usa un certificado
   dummy temporal para poder arrancar nginx, lo pide de verdad, y recarga
   nginx). Solo se corre una vez por servidor/dominio.
5. Levantar todo:
   ```bash
   docker compose up -d
   ```
6. Abrir `https://asunto.miagentepersonal.me`.

La renovación del certificado (cada ~60-90 días) la maneja solo el contenedor
`certbot`, no requiere intervención manual.

Si cambias el dominio en el futuro, actualiza `server_name` en
`deploy/nginx/conf.d/app.conf` y el valor de `domain=` en
`deploy/init-letsencrypt.sh`.
