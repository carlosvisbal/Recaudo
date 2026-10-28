import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class EstadoRegistro(models.TextChoices):
    ACTIVO = "activo", "Activo"
    INACTIVO = "inactivo", "Inactivo"


class EstadoActividad(models.TextChoices):
    PROGRAMADA = "programada", "Programada"
    ACTIVA = "activa", "Activa"
    CERRADA = "cerrada", "Cerrada"


class MedioPago(models.TextChoices):
    EFECTIVO = "efectivo", "Efectivo"
    TRANSFERENCIA = "transferencia", "Transferencia"


class EstadoRecaudo(models.TextChoices):
    CONFIRMADO = "confirmado", "Confirmado"
    ANULADO = "anulado", "Anulado"


class ResultadoEnvio(models.TextChoices):
    ENVIADO = "enviado", "Enviado"
    ERROR = "error", "Error"
    NO_CONFIGURADO = "no_configurado", "SMTP no configurado"
    CLIENTE_LOCAL = "cliente_local", "Cliente de correo del dispositivo"


class Organizacion(models.Model):
    """Configuración única de la organización (nombre impreso en recibos)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    nombre = models.CharField(max_length=180)
    nit = models.CharField(max_length=40, blank=True)
    ciudad = models.CharField(max_length=80, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    correo = models.EmailField(blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "organización"
        verbose_name_plural = "organización"

    def __str__(self) -> str:
        return self.nombre

    @classmethod
    def actual(cls) -> "Organizacion":
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={"nombre": settings.ORGANIZATION_NAME},
        )
        return obj


class ReciboSequence(models.Model):
    """Contador de numeración consecutiva. Nunca decrementa ni reutiliza anulados."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "secuencia de recibos"


class Semilla(models.Model):
    """Marca de datos iniciales aplicados una sola vez (no se vuelven a cargar)."""

    clave = models.CharField(max_length=64, primary_key=True)
    aplicada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "semilla"
        verbose_name_plural = "semillas"


class Padrino(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_completo = models.CharField(max_length=160)
    telefono = models.CharField(max_length=40)
    correo = models.EmailField(blank=True)
    estado = models.CharField(
        max_length=12, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre_completo"]
        verbose_name = "padrino"
        verbose_name_plural = "padrinos"

    def __str__(self) -> str:
        return self.nombre_completo


class Familia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=160, db_index=True)
    contacto_principal = models.CharField(max_length=160, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    correo = models.EmailField(blank=True)
    padrino = models.ForeignKey(
        Padrino, on_delete=models.PROTECT, related_name="familias"
    )
    observaciones = models.TextField(blank=True)
    estado = models.CharField(
        max_length=12, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "familia"
        verbose_name_plural = "familias"
        indexes = [
            models.Index(fields=["padrino", "estado"]),
            models.Index(fields=["nombre"]),
        ]

    def __str__(self) -> str:
        return self.nombre


class AsignacionFamiliaHistorial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    familia = models.ForeignKey(
        Familia, on_delete=models.CASCADE, related_name="historial_asignaciones"
    )
    padrino_anterior = models.ForeignKey(
        Padrino,
        on_delete=models.PROTECT,
        related_name="asignaciones_salientes",
        null=True,
        blank=True,
    )
    padrino_nuevo = models.ForeignKey(
        Padrino, on_delete=models.PROTECT, related_name="asignaciones_entrantes"
    )
    motivo = models.CharField(max_length=255, blank=True)
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reasignaciones"
    )
    cambiado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cambiado_en"]
        verbose_name = "historial de asignación"


class Actividad(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(
        max_length=12, choices=EstadoActividad.choices, default=EstadoActividad.ACTIVA
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_inicio", "nombre"]
        verbose_name = "actividad"
        verbose_name_plural = "actividades"

    def __str__(self) -> str:
        return self.nombre


class Recaudo(models.Model):
    """
    Documento de ingreso. Los confirmados se anulan o se eliminan; el número no se reutiliza.

    Extensión fase 2 (sin tablas aún): órdenes de pago a proveedores, conciliación
    bancaria y flujos de aprobación se modelarán como documentos de egreso /
    conciliación independientes, sin alterar la numeración de estos recibos.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.PositiveIntegerField(unique=True)
    fecha = models.DateField()
    actividad = models.ForeignKey(
        Actividad, on_delete=models.PROTECT, related_name="recaudos"
    )
    padrino = models.ForeignKey(
        Padrino, on_delete=models.PROTECT, related_name="recaudos"
    )
    familia = models.ForeignKey(
        Familia,
        on_delete=models.PROTECT,
        related_name="recaudos",
        null=True,
        blank=True,
    )
    aportante_nombre = models.CharField(max_length=180)
    valor = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    medio_pago = models.CharField(max_length=16, choices=MedioPago.choices)
    concepto = models.CharField(max_length=255, blank=True)
    referencia_consignacion = models.CharField(max_length=80, blank=True)
    estado = models.CharField(
        max_length=12, choices=EstadoRecaudo.choices, default=EstadoRecaudo.CONFIRMADO
    )
    motivo_anulacion = models.TextField(blank=True)
    anulado_en = models.DateTimeField(null=True, blank=True)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recaudos_anulados",
        null=True,
        blank=True,
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recaudos"
    )
    organizacion_nombre = models.CharField(max_length=180)
    actividad_nombre = models.CharField(max_length=160)
    padrino_nombre = models.CharField(max_length=160)
    familia_nombre = models.CharField(max_length=160, blank=True)
    usuario_nombre = models.CharField(max_length=160)
    valor_en_letras = models.CharField(max_length=400)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-numero"]
        verbose_name = "recaudo"
        verbose_name_plural = "recaudos"
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["actividad", "estado"]),
            models.Index(fields=["padrino", "estado"]),
            models.Index(fields=["familia", "estado"]),
            models.Index(fields=["medio_pago"]),
        ]

    def __str__(self) -> str:
        return f"Recibo {self.numero_formateado}"

    @property
    def numero_formateado(self) -> str:
        return f"{self.numero:06d}"


class Soporte(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recaudo = models.ForeignKey(
        Recaudo, on_delete=models.PROTECT, related_name="soportes"
    )
    archivo = models.FileField(upload_to="private/soportes/%Y/%m/")
    nombre_original = models.CharField(max_length=255)
    content_type = models.CharField(max_length=80)
    tamano = models.PositiveIntegerField()
    subido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["subido_en"]


class ReciboPdf(models.Model):
    recaudo = models.OneToOneField(
        Recaudo, on_delete=models.PROTECT, related_name="recibo"
    )
    archivo = models.FileField(upload_to="private/recibos/%Y/%m/")
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "recibo PDF"


class Auditoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accion = models.CharField(max_length=80)
    entidad = models.CharField(max_length=40)
    entidad_id = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="auditorias"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "registro de auditoría"


class EnvioCorreo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recaudo = models.ForeignKey(
        Recaudo, on_delete=models.PROTECT, related_name="envios_correo"
    )
    destinatario = models.EmailField()
    asunto = models.CharField(max_length=180)
    resultado = models.CharField(max_length=20, choices=ResultadoEnvio.choices)
    detalle = models.TextField(blank=True)
    enviado_en = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="envios_correo"
    )

    class Meta:
        ordering = ["-enviado_en"]
