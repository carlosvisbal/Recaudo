# Funcionalidades no cubiertas o cubiertas a medias

## Segunda fase (fuera de este MVP, por requerimiento)

- Órdenes de pago a proveedores.
- Conciliación bancaria.
- Flujos de aprobación.

El modelo actual no las implementa, pero tampoco las impide (ver `docs/MODELO.md`).

## Compartir

- No hay envío automático a WhatsApp Business API. Se abre WhatsApp o el menú nativo Compartir. En iPhone, adjuntar el PDF requiere un navegador que soporte Web Share Level 2 y, fuera de localhost, HTTPS.
- El envío de correo desde el servidor solo funciona si se configuran las variables SMTP. Sin ellas, se abre el cliente de correo local.

## PWA y despliegue

- No hay aplicaciones nativas en App Store ni Play Store. La vía soportada es la PWA.
- En iPhone, “Agregar a pantalla de inicio” no ofrece todas las APIs de Android (por ejemplo, compartir archivos es más limitado).
- Este entorno de desarrollo puede no dejar HTTPS de producción configurado; en Docker local la app corre en HTTP en el puerto 8000.

## Operación

- Un solo usuario administrador. No hay roles para padrinos ni para varios tesoreros.
- No hay carga masiva de familias desde Excel.
- La numeración concurrente usa bloqueo de fila. Docker y las pruebas locales usan SQLite (WAL); basta para este volumen de operación.

## Verificación en navegador

La pantalla de login de la PWA se abrió en el navegador embebido. El recorrido interactivo (clic, contraseña, registro) no se completó ahí; el flujo se verificó con `pytest` (13 pruebas) y con una sesión HTTP real: padrino, familia, actividad, recaudo con soporte, PDF privado, WhatsApp/mailto y Excel.
