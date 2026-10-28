# Modelo de datos

## Núcleo del MVP

- `Organizacion`: nombre y datos impresos en recibos.
- `ReciboSequence`: contador de numeración (nunca decrementa).
- `Padrino`, `Familia`, `AsignacionFamiliaHistorial`.
- `Actividad`.
- `Recaudo`: documento de **ingreso**. Estados `confirmado` | `anulado`.
- `Soporte`, `ReciboPdf`.
- `Auditoria`, `EnvioCorreo`.

Los padrinos y las familias usan UUID. El número de recibo es un entero único.

## Extensión prevista (fase 2)

No hay tablas todavía, a propósito: el recaudo no se mezcla con egresos.

Cuando se incorporen, convienen documentos aparte:

1. **Orden de pago a proveedores** (`OrdenPago`): proveedor, valor, actividad opcional, estado, recibo de egreso con numeración propia.
2. **Conciliación bancaria** (`MovimientoBancario`, `Conciliacion`): extracto vs. recaudos por transferencia y vs. órdenes de pago.
3. **Flujos de aprobación** (`SolicitudAprobacion`, `PasoAprobacion`): sobre órdenes de pago u otros documentos, no sobre el recaudo ya confirmado.

El recaudo permanece inmutable salvo anulación, de modo que esas piezas se pueden enganchar por referencia (`recaudo_id` opcional en una conciliación) sin reescribir la numeración ni los PDF.
