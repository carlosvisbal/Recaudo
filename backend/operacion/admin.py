from django.contrib import admin

from .models import (
    Actividad,
    ActividadParticipante,
    ActividadPersona,
    AsignacionFamiliaHistorial,
    Auditoria,
    EnvioCorreo,
    Familia,
    Organizacion,
    Padrino,
    Recaudo,
    ReciboPdf,
    ReciboSequence,
    Semilla,
    Soporte,
)

admin.site.site_header = "Recaudo — administración"
admin.site.site_title = "Recaudo admin"
admin.site.index_title = "Panel general (uso de emergencia o soporte)"


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "ciudad", "telefono", "correo", "actualizado_en")


@admin.register(ReciboSequence)
class ReciboSequenceAdmin(admin.ModelAdmin):
    list_display = ("pk", "ultimo_numero")


@admin.register(Semilla)
class SemillaAdmin(admin.ModelAdmin):
    list_display = ("clave", "aplicada_en")
    readonly_fields = ("clave", "aplicada_en")


@admin.register(Padrino)
class PadrinoAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "telefono", "correo", "estado", "creado_en")
    search_fields = ("nombre_completo", "telefono", "correo")
    list_filter = ("estado",)


@admin.register(Familia)
class FamiliaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "padrino", "contacto_principal", "telefono", "estado", "creado_en")
    search_fields = ("nombre", "contacto_principal", "telefono")
    list_filter = ("estado", "padrino")
    raw_id_fields = ("padrino",)


@admin.register(AsignacionFamiliaHistorial)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ("familia", "padrino_anterior", "padrino_nuevo", "cambiado_en", "cambiado_por")
    search_fields = ("familia__nombre",)
    readonly_fields = (
        "familia",
        "padrino_anterior",
        "padrino_nuevo",
        "motivo",
        "cambiado_por",
        "cambiado_en",
    )


class ActividadParticipanteInline(admin.TabularInline):
    model = ActividadParticipante
    extra = 0
    raw_id_fields = ("familia", "padrino")


class ActividadPersonaInline(admin.TabularInline):
    model = ActividadPersona
    extra = 0


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "tipo",
        "cobro_cada",
        "fecha_inicio",
        "fecha_fin",
        "estado",
        "creado_en",
    )
    search_fields = ("nombre",)
    list_filter = ("estado", "tipo", "cobro_cada")
    inlines = [ActividadParticipanteInline, ActividadPersonaInline]


@admin.register(ActividadParticipante)
class ActividadParticipanteAdmin(admin.ModelAdmin):
    list_display = ("actividad", "padrino", "familia", "creado_en")
    search_fields = ("actividad__nombre", "familia__nombre", "padrino__nombre_completo")
    raw_id_fields = ("actividad", "familia", "padrino")


class SoporteInline(admin.TabularInline):
    model = Soporte
    extra = 0
    readonly_fields = ("nombre_original", "content_type", "tamano", "subido_en", "archivo")
    fields = ("nombre_original", "content_type", "tamano", "archivo", "subido_en")


@admin.register(Recaudo)
class RecaudoAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "fecha",
        "actividad_nombre",
        "padrino_nombre",
        "aportante_nombre",
        "valor",
        "medio_pago",
        "estado",
        "creado_en",
    )
    list_filter = ("estado", "medio_pago", "actividad")
    search_fields = ("numero", "aportante_nombre", "concepto", "familia_nombre", "padrino_nombre")
    date_hierarchy = "fecha"
    raw_id_fields = ("actividad", "padrino", "familia", "registrado_por", "anulado_por")
    readonly_fields = (
        "numero",
        "valor_en_letras",
        "organizacion_nombre",
        "actividad_nombre",
        "padrino_nombre",
        "familia_nombre",
        "usuario_nombre",
        "creado_en",
    )
    inlines = [SoporteInline]


@admin.register(Soporte)
class SoporteAdmin(admin.ModelAdmin):
    list_display = ("nombre_original", "recaudo", "content_type", "tamano", "subido_en")
    search_fields = ("nombre_original", "recaudo__numero")
    raw_id_fields = ("recaudo",)
    readonly_fields = ("nombre_original", "content_type", "tamano", "subido_en")


@admin.register(ReciboPdf)
class ReciboAdmin(admin.ModelAdmin):
    list_display = ("recaudo", "generado_en")
    raw_id_fields = ("recaudo",)
    readonly_fields = ("generado_en",)


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "accion", "entidad", "entidad_id", "usuario", "ip")
    list_filter = ("accion", "entidad")
    search_fields = ("accion", "entidad", "entidad_id")
    readonly_fields = ("accion", "entidad", "entidad_id", "payload", "usuario", "creado_en", "ip")


@admin.register(EnvioCorreo)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ("enviado_en", "destinatario", "resultado", "recaudo", "usuario")
    list_filter = ("resultado",)
    search_fields = ("destinatario", "asunto")
    readonly_fields = (
        "recaudo",
        "destinatario",
        "asunto",
        "resultado",
        "detalle",
        "enviado_en",
        "usuario",
    )
