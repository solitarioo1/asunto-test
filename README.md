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
   (igual que el Colab), para copiar directo al correo. **✅ En desarrollo (paso actual)**

## Estado actual

Por ahora la web replica exactamente lo que hacía el Colab:

- El usuario sube un `.zip` con los PDFs (reemplaza la lectura fija desde Google Drive).
- Se extraen los campos por regex de cada PDF.
- Se genera y muestra el HTML con los bloques de Asunto + Cuerpo.

Los pasos 1-3 (unir con firma, renombrar, exportar zip) se agregan en iteraciones
siguientes.

## Stack

- Backend: Python + FastAPI
- PDF: `pypdf`
- Frontend: HTML simple servido por el propio backend

## Correr en local

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Abrir `http://127.0.0.1:8000`.

## Correr con Docker

```bash
docker compose up -d --build
```

Abrir `http://<ip-del-vps>:8000`.

Para actualizar tras un cambio de código:

```bash
git pull
docker compose up -d --build
```

## Despliegue en VPS

1. Instalar Docker + Docker Compose en el VPS.
2. Clonar el repo.
3. `docker compose up -d --build`.
4. (Opcional) poner nginx como reverse proxy delante del puerto 8000 con HTTPS.

Pendiente de documentar el paso de nginx una vez esté desplegado.
