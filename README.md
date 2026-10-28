# Recaudo

Aplicación para el control operativo de recaudos: padrinos, familias asignadas, actividades, registro de dinero, recibos de caja en PDF y consultas.

El recaudo confirmado genera un **recibo de caja** (constancia interna del dinero recibido). No es un certificado tributario oficial.

## Alcance de esta versión

1. Padrinos y familias (sin tope de cantidad; historial al reasignar).
2. Actividades independientes, con totales separados.
3. Registro de recaudos y soportes (móvil).
4. Recibo PDF con numeración consecutiva que no se reutiliza al anular.
5. Compartir: descargar, imprimir, WhatsApp y correo.
6. Consultas, totales y exportación a Excel.
7. Un administrador autenticado. Despliegue Docker y PWA para PC, iPhone y Android.

Órdenes de pago a proveedores, conciliación bancaria y flujos de aprobación quedan para una segunda fase. El modelo deja esos ingresos como documento propio para no bloquear esa extensión.

Detalle de requisitos: `docs/ALCANCE.md`. Lo que no entra en este MVP: `docs/PENDIENTE.md`.

## Arranque con Docker

```bash
cp .env.example .env
# Edite DJANGO_SECRET_KEY
docker compose up --build
```

- Aplicación local: http://localhost:8010 (el puerto interno del contenedor es 8000; en el anfitrión se usa 8010 para no chocar con otros servicios)
- Exposición a internet: `cloudflared` abre un túnel HTTPS.
  - Sin token: URL temporal `*.trycloudflare.com` (cambia cada vez que arranca el contenedor). Véase `docker compose logs -f cloudflared`.
  - URL fija: cree un túnel en [Zero Trust → Tunnels](https://one.dash.cloudflare.com/), ponga `CLOUDFLARE_TUNNEL_TOKEN` y `CLOUDFLARE_PUBLIC_HOST` (ej. `recaudo.sudominio.com`) en `.env`, y un Public Hostname HTTP hacia `http://app:8000`. Luego `docker compose up -d --build cloudflared`.
- Usuario: `admin`
- Contraseña: `Skorpion18***` (se crea sola la primera vez que existen las tablas)

La base de datos es **SQLite** (un archivo en el volumen `recaudo-sqlite`): no hay contenedor de Postgres ni imagen de ~600 MB. Los soportes y recibos quedan en `recaudo-media` (privados; solo se sirven a la sesión autenticada).

Para instalarla como PWA en el teléfono, sirva la app por **HTTPS** (en localhost el navegador de escritorio sí permite instalar). En iPhone: Safari → Compartir → Agregar a pantalla de inicio.

## Despliegue en Railway

No hace falta dominio propio. Use el hostname que Railway asigna al generar dominio (`algo.up.railway.app`). La app ya acepta `*.up.railway.app` y CSRF en HTTPS.

1. En [Railway](https://railway.app) cree un proyecto y despliegue este repositorio (detecta el `Dockerfile`).
2. En el servicio: **Settings → Networking → Generate Domain**. Esa URL es la pública.
3. En **Settings → Healthcheck Path** ponga `/salud/`.
4. Agregue un **Volume** montado en `/data` (SQLite y archivos de recibos/soportes). Sin volumen, los datos se pierden al redesplegar.
5. No hace falta pegar claves en el panel: van quemadas en el `Dockerfile` (`admin` / `Skorpion18***`).

No configure `DJANGO_ALLOWED_HOSTS` ni un dominio custom. Railway inyecta `PORT` y `RAILWAY_PUBLIC_DOMAIN`; el contenedor escucha en `$PORT`.

Usuario inicial: `admin` / `Skorpion18***`.

## Desarrollo local

Necesita Python 3.13 y Node 22.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8010
```

En otra terminal:

```bash
cd frontend
npm install
python ../backend/scripts/generate_icons.py
npm run dev
```

El frontend en http://localhost:5173 proxy hacia la API en el puerto 8000.

```bash
cd backend
pytest
```

## Correo y WhatsApp

- **WhatsApp:** se abre `wa.me` con un texto prellenado. El PDF se adjunta con el menú Compartir del dispositivo cuando el navegador lo permite. Abrir WhatsApp **no** significa que el mensaje se haya enviado.
- **Correo:** si `EMAIL_HOST` y `EMAIL_HOST_USER` están en `.env`, el servidor envía el PDF y registra el resultado. Si no, se abre el cliente de correo del dispositivo; hay que descargar el PDF y adjuntarlo.

No se publican enlaces permanentes a recibos ni soportes.

## Seguridad financiera

- Los recaudos confirmados no se borran. La anulación pide motivo, conserva el PDF y deja auditoría.
- El número de recibo se asigna con bloqueo de fila (`SELECT FOR UPDATE`) para operaciones simultáneas.
- Los importes se guardan en `Decimal` (no en punto flotante).
- Solo se aceptan soportes PDF, JPEG, PNG o WebP, de hasta 5 MB.
