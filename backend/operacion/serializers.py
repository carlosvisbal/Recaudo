from rest_framework import serializers

from .models import (
    Actividad,
    ActividadParticipante,
    ActividadPersona,
    AsignacionFamiliaHistorial,
    CobroCada,
    EnvioCorreo,
    Familia,
    Organizacion,
    Padrino,
    Recaudo,
    ReciboPdf,
    Soporte,
    TipoActividad,
)
from .money import format_cop
from .services import sincronizar_participantes, sincronizar_personas


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


class ActividadParticipanteSerializer(serializers.ModelSerializer):
    familia_nombre = serializers.CharField(source="familia.nombre", read_only=True)
    padrino_nombre = serializers.CharField(
        source="padrino.nombre_completo", read_only=True
    )

    class Meta:
        model = ActividadParticipante
        fields = (
            "id",
            "familia",
            "familia_nombre",
            "padrino",
            "padrino_nombre",
        )


class ActividadPersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadPersona
        fields = ("id", "nombre", "telefono", "creado_en")
        read_only_fields = ("id", "creado_en")


class ActividadSerializer(serializers.ModelSerializer):
    total_recaudado = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    cantidad_recaudos = serializers.IntegerField(read_only=True)
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)
    cobro_cada_label = serializers.CharField(
        source="get_cobro_cada_display", read_only=True
    )
    participantes = ActividadParticipanteSerializer(many=True, read_only=True)
    personas = ActividadPersonaSerializer(many=True, read_only=True)
    familias = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    personas_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    cantidad_familias = serializers.SerializerMethodField()
    cantidad_personas = serializers.SerializerMethodField()

    class Meta:
        model = Actividad
        fields = (
            "id",
            "nombre",
            "descripcion",
            "fecha_inicio",
            "fecha_fin",
            "tipo",
            "tipo_label",
            "cobro_cada",
            "cobro_cada_label",
            "estado",
            "participantes",
            "personas",
            "familias",
            "personas_data",
            "cantidad_familias",
            "cantidad_personas",
            "total_recaudado",
            "cantidad_recaudos",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = (
            "id",
            "tipo_label",
            "cobro_cada_label",
            "participantes",
            "personas",
            "cantidad_familias",
            "cantidad_personas",
            "total_recaudado",
            "cantidad_recaudos",
            "creado_en",
            "actualizado_en",
        )

    def get_cantidad_familias(self, obj):
        if hasattr(obj, "cantidad_familias_annot"):
            return obj.cantidad_familias_annot
        return obj.participantes.count()

    def get_cantidad_personas(self, obj):
        if hasattr(obj, "cantidad_personas_annot"):
            return obj.cantidad_personas_annot
        return obj.personas.count()

    def validate_tipo(self, value):
        if value not in TipoActividad.values:
            raise serializers.ValidationError(
                "Elija Con padrinos y familias, o Personas."
            )
        return value

    def validate_cobro_cada(self, value):
        if value not in CobroCada.values:
            raise serializers.ValidationError(
                "Elija Un solo pago, Cada mes o Cada quincena."
            )
        return value

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha final no puede ser anterior a la inicial."}
            )
        return attrs

    def create(self, validated_data):
        familias = validated_data.pop("familias", [])
        personas_data = validated_data.pop("personas_data", [])
        actividad = super().create(validated_data)
        if actividad.tipo == TipoActividad.GENERAL:
            sincronizar_personas(actividad, personas_data)
        else:
            sincronizar_participantes(actividad, familias)
        return actividad

    def update(self, instance, validated_data):
        familias = validated_data.pop("familias", None)
        personas_data = validated_data.pop("personas_data", None)
        actividad = super().update(instance, validated_data)
        if actividad.tipo == TipoActividad.GENERAL:
            if personas_data is not None:
                sincronizar_personas(actividad, personas_data)
        elif familias is not None:
            sincronizar_participantes(actividad, familias)
        return actividad


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
    soportes_count = serializers.SerializerMethodField()

    class Meta:
        model = Recaudo
        fields = (
            "id",
            "numero",
            "numero_formateado",
            "fecha",
            "periodo_inicio",
            "actividad",
            "actividad_nombre",
            "padrino",
            "padrino_nombre",
            "familia",
            "familia_nombre",
            "persona",
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

    def get_soportes_count(self, obj):
        # Preferir anotación o prefetch (evita N+1 en listados/consultas).
        annotated = getattr(obj, "soportes_count_annot", None)
        if annotated is not None:
            return annotated
        cache = getattr(obj, "_prefetched_objects_cache", None)
        if cache is not None and "soportes" in cache:
            return len(obj.soportes.all())
        return obj.soportes.count()


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
    periodo_inicio = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Período cobrado (mes o quincena). Puede ser atrasado o adelantado.",
    )
    actividad = serializers.PrimaryKeyRelatedField(queryset=Actividad.objects.all())
    padrino = serializers.PrimaryKeyRelatedField(
        queryset=Padrino.objects.all(), required=False, allow_null=True
    )
    familia = serializers.PrimaryKeyRelatedField(
        queryset=Familia.objects.all(), required=False, allow_null=True
    )
    persona = serializers.PrimaryKeyRelatedField(
        queryset=ActividadPersona.objects.all(), required=False, allow_null=True
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
