# Alcance implementado (MVP)

Este repositorio estaba vacío al iniciar el trabajo. El MVP se construyó según los requerimientos del cliente, sin reutilizar código previo.

## 1. Padrinos y familias

- CRUD de padrinos: nombre, teléfono, correo opcional, estado.
- CRUD de familias: nombre, contacto, teléfono, correo, padrino, observaciones, estado.
- No hay tope de 13 padrinos ni de familias.
- Desactivar (no borrar) padrinos y familias.
- Reasignar padrino conservando historial (fecha, usuario, motivo, padrino anterior y nuevo).
- Los padrinos no tienen cuenta de usuario.

## 2. Actividades

- Alta de actividades con nombre, descripción, fechas y estado (programada, activa, cerrada).
- Un padrino puede tener varias familias y recaudos en varias actividades.
- El total recaudado se calcula solo con movimientos confirmados de esa actividad.

## 3. Registro de recaudos

- Número consecutivo, fecha, actividad, padrino, familia o aportante, valor COP, medio (efectivo/transferencia), concepto, referencia, soportes y usuario.
- Formulario móvil con búsqueda de familias por nombre.
- Varios recaudos por familia y actividad, sin mezclar totales entre actividades.
- Actividad cerrada no admite nuevos recaudos.

## 4. Recibos de caja

Al confirmar se genera un PDF con:

- Numeración única (no se reutiliza si se anula).
- Fecha, organización configurable, padrino, aportante, actividad.
- Valor numérico y en letras, medio de pago, concepto, referencia.
- Referencia a soportes y datos de quien registró.
- Aviso explícito de que no es certificado tributario oficial.

Los nombres se congelan en el recaudo para que el PDF histórico no cambie si luego se edita un padrino o una familia.

## 5. Compartir

- Descargar PDF, imprimir, WhatsApp (`wa.me` + Web Share) y correo.
- Sin enlaces públicos permanentes. Descarga autenticada.
- SMTP opcional por variables de entorno, con registro de envío.

## 6. Consultas

Filtros: padrino, familia, actividad, fechas, medio de pago, número de recibo.

Totales por actividad, padrino y familia. Historial con enlace al recibo y a los soportes. Exportación Excel.

## 7. Seguridad

- Un administrador (sesión).
- Anulación con motivo y auditoría.
- Numeración con `select_for_update`.
- Importes `Decimal(14,2)`.
- Soportes validados y almacenados en `MEDIA_ROOT` privado.

## 8. Docker y PWA

`docker compose up --build` levanta la app con SQLite (sin contenedor de base de datos). En Railway se usa el dominio por defecto `*.up.railway.app`. El frontend es una PWA instalable en PC, Android e iPhone (este último requiere HTTPS fuera de localhost).
