from django.contrib import admin

from .models import (
    Actividad,
    AsignacionFamiliaHistorial,
    Auditoria,
    EnvioCorreo,
    Familia,
    Organizacion,
    Padrino,
    Recaudo,
    ReciboPdf,
    Soporte,
)


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ciudad", "correo")


@admin.register(Padrino)
class PadrinoAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "telefono", "correo", "estado")
    search_fields = ("nombre_completo", "telefono", "correo")
    list_filter = ("estado",)


@admin.register(Familia)
class FamiliaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "padrino", "contacto_principal", "telefono", "estado")
    search_fields = ("nombre", "contacto_principal")
    list_filter = ("estado", "padrino")


@admin.register(AsignacionFamiliaHistorial)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ("familia", "padrino_anterior", "padrino_nuevo", "cambiado_en")
    readonly_fields = (
        "familia",
        "padrino_anterior",
        "padrino_nuevo",
        "motivo",
        "cambiado_por",
        "cambiado_en",
    )


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "fecha_inicio", "fecha_fin", "estado")
    list_filter = ("estado",)


class SoporteInline(admin.TabularInline):
    model = Soporte
    extra = 0
    readonly_fields = ("nombre_original", "content_type", "tamano", "subido_en")


@admin.register(Recaudo)
class RecaudoAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "fecha",
        "actividad_nombre",
        "padrino_nombre",
        "aportante_nombre",
        "valor",
        "estado",
    )
    list_filter = ("estado", "medio_pago", "actividad")
    search_fields = ("numero", "aportante_nombre", "concepto")
    readonly_fields = (
        "numero",
        "valor",
        "valor_en_letras",
        "organizacion_nombre",
        "actividad_nombre",
        "padrino_nombre",
        "familia_nombre",
        "usuario_nombre",
        "creado_en",
        "registrado_por",
        "anulado_por",
        "anulado_en",
    )
    inlines = [SoporteInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReciboPdf)
class ReciboAdmin(admin.ModelAdmin):
    list_display = ("recaudo", "generado_en")
    readonly_fields = ("recaudo", "archivo", "generado_en")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "accion", "entidad", "usuario")
    readonly_fields = ("accion", "entidad", "entidad_id", "payload", "usuario", "creado_en", "ip")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EnvioCorreo)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ("enviado_en", "destinatario", "resultado", "recaudo")
    readonly_fields = (
        "recaudo",
        "destinatario",
        "asunto",
        "resultado",
        "detalle",
        "enviado_en",
        "usuario",
    )
