# Pendientes

- [ ] **Unir PDF** — cada PDF de contenido se une con un PDF de firma común
  (10 contenido + 1 firma → 10 PDFs finales).
- [ ] **Renombrar PDF** — cada PDF final se renombra como `SINIESTRO_{numero}.pdf`,
  usando el número de siniestro extraído del texto.
- [ ] **Exportar PDF** — descarga en `.zip` de todos los PDFs renombrados.

## Hecho recientemente

- [x] Reestructuración del proyecto (`app/routers`, `app/services`, `templates/`, `static/css`, `static/js`).
- [x] Zona de carga grande con drag & drop, PDFs sueltos o carpeta completa.
- [x] Validación real de tipo de archivo por firma binaria (`%PDF-` / `PK\x03\x04`), descarta archivos con extensión falsa.
- [x] Protección del formulario con Cloudflare Turnstile (se oculta al verificarse).
- [x] nginx + HTTPS (Let's Encrypt/Certbot) delante del contenedor, dominio `asunto.miagentepersonal.me`.
