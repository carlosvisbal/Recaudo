from rest_framework import serializers

from .models import (
    Actividad,
    AsignacionFamiliaHistorial,
    EnvioCorreo,
    Familia,
    Organizacion,
    Padrino,
    Recaudo,
    ReciboPdf,
    Soporte,
)
from .money import format_cop


class OrganizacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizacion
        fields = ("nombre", "nit", "ciudad", "telefono", "correo")


class PadrinoSerializer(serializers.ModelSerializer):
    familias_activas = serializers.IntegerField(read_only=True)

    class Meta:
        model = Padrino
        fields = (
            "id",
            "nombre_completo",
            "telefono",
            "correo",
            "estado",
            "familias_activas",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("id", "creado_en", "actualizado_en", "familias_activas")


class AsignacionSerializer(serializers.ModelSerializer):
    padrino_anterior_nombre = serializers.CharField(
        source="padrino_anterior.nombre_completo", read_only=True, allow_null=True
    )
    padrino_nuevo_nombre = serializers.CharField(
        source="padrino_nuevo.nombre_completo", read_only=True
    )
    cambiado_por_nombre = serializers.CharField(source="cambiado_por.username", read_only=True)

    class Meta:
        model = AsignacionFamiliaHistorial
        fields = (
            "id",
            "padrino_anterior",
            "padrino_anterior_nombre",
            "padrino_nuevo",
            "padrino_nuevo_nombre",
            "motivo",
            "cambiado_por_nombre",
            "cambiado_en",
        )


class FamiliaSerializer(serializers.ModelSerializer):
    padrino_nombre = serializers.CharField(source="padrino.nombre_completo", read_only=True)

    class Meta:
        model = Familia
        fields = (
            "id",
            "nombre",
            "contacto_principal",
            "telefono",
            "correo",
            "padrino",
            "padrino_nombre",
            "observaciones",
            "estado",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("id", "creado_en", "actualizado_en", "padrino_nombre")


class FamiliaBusquedaSerializer(serializers.ModelSerializer):
    padrino_nombre = serializers.CharField(source="padrino.nombre_completo", read_only=True)

    class Meta:
        model = Familia
        fields = (
            "id",
            "nombre",
            "contacto_principal",
            "telefono",
            "correo",
            "padrino",
            "padrino_nombre",
            "estado",
        )


class ActividadSerializer(serializers.ModelSerializer):
    total_recaudado = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    cantidad_recaudos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Actividad
        fields = (
            "id",
            "nombre",
            "descripcion",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "total_recaudado",
            "cantidad_recaudos",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = (
            "id",
            "total_recaudado",
            "cantidad_recaudos",
            "creado_en",
            "actualizado_en",
        )

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha final no puede ser anterior a la inicial."}
            )
        return attrs


class SoporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Soporte
        fields = ("id", "nombre_original", "content_type", "tamano", "subido_en")


class ReciboSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReciboPdf
        fields = ("generado_en",)


class RecaudoListSerializer(serializers.ModelSerializer):
    valor_formato = serializers.SerializerMethodField()
    medio_pago_display = serializers.CharField(source="get_medio_pago_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    soportes_count = serializers.IntegerField(source="soportes.count", read_only=True)

    class Meta:
        model = Recaudo
        fields = (
            "id",
            "numero",
            "numero_formateado",
            "fecha",
            "actividad",
            "actividad_nombre",
            "padrino",
            "padrino_nombre",
            "familia",
            "familia_nombre",
            "aportante_nombre",
            "valor",
            "valor_formato",
            "medio_pago",
            "medio_pago_display",
            "concepto",
            "referencia_consignacion",
            "estado",
            "estado_display",
            "usuario_nombre",
            "soportes_count",
            "creado_en",
        )

    def get_valor_formato(self, obj):
        return format_cop(obj.valor)


class RecaudoDetalleSerializer(RecaudoListSerializer):
    soportes = SoporteSerializer(many=True, read_only=True)
    recibo = ReciboSerializer(read_only=True)
    valor_en_letras = serializers.CharField(read_only=True)
    motivo_anulacion = serializers.CharField(read_only=True)
    anulado_en = serializers.DateTimeField(read_only=True)
    organizacion_nombre = serializers.CharField(read_only=True)
    familia_telefono = serializers.SerializerMethodField()

    class Meta(RecaudoListSerializer.Meta):
        fields = RecaudoListSerializer.Meta.fields + (
            "soportes",
            "recibo",
            "valor_en_letras",
            "motivo_anulacion",
            "anulado_en",
            "organizacion_nombre",
            "familia_telefono",
        )

    def get_familia_telefono(self, obj):
        return obj.familia.telefono if obj.familia_id else ""


class RecaudoCreateSerializer(serializers.Serializer):
    fecha = serializers.DateField(required=False)
    actividad = serializers.PrimaryKeyRelatedField(queryset=Actividad.objects.all())
    padrino = serializers.PrimaryKeyRelatedField(queryset=Padrino.objects.all())
    familia = serializers.PrimaryKeyRelatedField(
        queryset=Familia.objects.all(), required=False, allow_null=True
    )
    aportante_nombre = serializers.CharField(required=False, allow_blank=True, max_length=180)
    valor = serializers.DecimalField(max_digits=14, decimal_places=2)
    medio_pago = serializers.ChoiceField(choices=["efectivo", "transferencia"])
    concepto = serializers.CharField(required=False, allow_blank=True, max_length=255)
    referencia_consignacion = serializers.CharField(
        required=False, allow_blank=True, max_length=80
    )


class EnvioCorreoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvioCorreo
        fields = ("id", "destinatario", "asunto", "resultado", "detalle", "enviado_en")
