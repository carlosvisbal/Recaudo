from collections import defaultdict
from datetime import date
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from . import audit
from .files import validate_soporte
from .models import (
    Actividad,
    AsignacionFamiliaHistorial,
    EnvioCorreo,
    EstadoActividad,
    EstadoRecaudo,
    EstadoRegistro,
    Familia,
    MedioPago,
    Organizacion,
    Padrino,
    Recaudo,
    ReciboPdf,
    ReciboSequence,
    ResultadoEnvio,
    Soporte,
)
from .money import format_cop, money, numero_a_letras
from .pdf import generar_pdf_recibo


def siguiente_numero_recibo() -> int:
    seq, _ = ReciboSequence.objects.select_for_update().get_or_create(
        pk=1, defaults={"ultimo_numero": 0}
    )
    seq.ultimo_numero += 1
    seq.save(update_fields=["ultimo_numero"])
    return seq.ultimo_numero


def reasignar_familia(familia: Familia, padrino: Padrino, usuario, motivo: str = "", request=None) -> Familia:
    if familia.padrino_id == padrino.id:
        raise ValidationError("La familia ya está asignada a ese padrino.")
    anterior = familia.padrino
    familia.padrino = padrino
    familia.save(update_fields=["padrino", "actualizado_en"])
    AsignacionFamiliaHistorial.objects.create(
        familia=familia,
        padrino_anterior=anterior,
        padrino_nuevo=padrino,
        motivo=motivo,
        cambiado_por=usuario,
    )
    audit.registrar(
        usuario,
        "familia.reasignar",
        "familia",
        familia.id,
        {
            "padrino_anterior": str(anterior.id),
            "padrino_nuevo": str(padrino.id),
            "motivo": motivo,
        },
        request,
    )
    return familia


@transaction.atomic
def eliminar_familia(familia: Familia, usuario, request=None) -> dict:
    """Borra la familia. Los pagos quedan; se desliga el vínculo para no perder recibos."""
    pagos = Recaudo.objects.filter(familia=familia).count()
    Recaudo.objects.filter(familia=familia).update(familia=None)
    nombre = familia.nombre
    pk = familia.id
    familia.delete()
    audit.registrar(
        usuario,
        "familia.eliminar",
        "familia",
        pk,
        {"nombre": nombre, "pagos_desligados": pagos},
        request,
    )
    return {"nombre": nombre, "pagos_desligados": pagos}


@transaction.atomic
def eliminar_padrino(padrino: Padrino, usuario, request=None) -> dict:
    """Borra el padrino y sus familias si no tiene pagos. Si hay recaudos, no se elimina."""
    pagos = Recaudo.objects.filter(padrino=padrino).count()
    if pagos:
        raise ValidationError(
            f"No se puede eliminar: este padrino tiene {pagos} pago(s). "
            "Desactívelo o elimine primero la actividad de esos pagos."
        )
    familias = list(padrino.familias.all())
    for familia in familias:
        eliminar_familia(familia, usuario, request)
    AsignacionFamiliaHistorial.objects.filter(
        Q(padrino_anterior=padrino) | Q(padrino_nuevo=padrino)
    ).delete()
    nombre = padrino.nombre_completo
    pk = padrino.id
    padrino.delete()
    audit.registrar(
        usuario,
        "padrino.eliminar",
        "padrino",
        pk,
        {"nombre": nombre, "familias_eliminadas": len(familias)},
        request,
    )
    return {"nombre": nombre, "familias_eliminadas": len(familias)}


def _borrar_campo_archivo(campo) -> None:
    if not campo:
        return
    name = getattr(campo, "name", "")
    storage = getattr(campo, "storage", None)
    if name and storage and storage.exists(name):
        storage.delete(name)


@transaction.atomic
def eliminar_recaudo(recaudo: Recaudo, usuario, request=None) -> dict:
    """Borra el pago, el PDF y los soportes. El número de recibo no se reutiliza."""
    numero = recaudo.numero
    pk = recaudo.id
    recaudo.envios_correo.all().delete()
    for soporte in list(recaudo.soportes.all()):
        _borrar_campo_archivo(soporte.archivo)
        soporte.delete()
    recibo = ReciboPdf.objects.filter(recaudo=recaudo).first()
    if recibo:
        _borrar_campo_archivo(recibo.archivo)
        recibo.delete()
    recaudo.delete()
    audit.registrar(
        usuario,
        "recaudo.eliminar",
        "recaudo",
        pk,
        {"numero": numero},
        request,
    )
    return {"numero": numero}


@transaction.atomic
def eliminar_actividad(actividad: Actividad, usuario, request=None) -> dict:
    """Borra la actividad, sus pagos y los archivos para liberar disco."""
    recaudos = list(actividad.recaudos.all())
    for recaudo in recaudos:
        eliminar_recaudo(recaudo, usuario, request)
    nombre = actividad.nombre
    pk = actividad.id
    actividad.delete()
    audit.registrar(
        usuario,
        "actividad.eliminar",
        "actividad",
        pk,
        {"nombre": nombre, "pagos_eliminados": len(recaudos)},
        request,
    )
    return {"nombre": nombre, "pagos_eliminados": len(recaudos)}


def _validar_datos_pago(data: dict, archivos: list, *, soportes_actuales: int = 0) -> dict:
    actividad: Actividad = data["actividad"]
    padrino: Padrino = data["padrino"]
    familia: Familia | None = data.get("familia")
    if actividad.estado == EstadoActividad.CERRADA:
        raise ValidationError("No se pueden registrar recaudos en una actividad cerrada.")
    if padrino.estado != EstadoRegistro.ACTIVO:
        raise ValidationError("El padrino responsable está inactivo.")
    if familia and familia.estado != EstadoRegistro.ACTIVO:
        raise ValidationError("La familia está inactiva.")

    valor = money(data["valor"])
    if valor <= Decimal("0.00"):
        raise ValidationError("El valor recibido debe ser mayor que cero.")

    medio = data["medio_pago"]
    if medio not in MedioPago.values:
        raise ValidationError("Medio de pago no válido.")

    aportante = (data.get("aportante_nombre") or "").strip()
    if familia and not aportante:
        aportante = familia.nombre
    if not aportante:
        raise ValidationError("Indique la familia o la persona que entrega el dinero.")

    archivos = archivos or []
    if medio == MedioPago.EFECTIVO and archivos:
        raise ValidationError("El pago en efectivo no lleva soporte. No adjunte archivos.")
    if medio == MedioPago.TRANSFERENCIA and not archivos and soportes_actuales == 0:
        raise ValidationError(
            "La transferencia requiere el comprobante adjunto (PDF o archivo de imagen)."
        )
    if len(archivos) > settings.MAX_SOPORTES_POR_RECAUDO:
        raise ValidationError("Puede adjuntar como máximo 8 soportes.")
    return {
        "actividad": actividad,
        "padrino": padrino,
        "familia": familia,
        "valor": valor,
        "medio": medio,
        "aportante": aportante,
        "archivos": archivos,
    }


def _regenerar_recibo(recaudo: Recaudo) -> None:
    pdf_bytes = generar_pdf_recibo(recaudo)
    recibo, _ = ReciboPdf.objects.get_or_create(recaudo=recaudo)
    recibo.archivo.save(
        f"recibo-{recaudo.numero_formateado}.pdf",
        ContentFile(pdf_bytes),
        save=True,
    )


@transaction.atomic
def actualizar_recaudo(*, recaudo: Recaudo, usuario, data: dict, archivos: list, request=None) -> Recaudo:
    if recaudo.estado == EstadoRecaudo.ANULADO:
        raise ValidationError("No se puede editar un pago anulado. Elimínelo si debe quitarlo.")
    parsed = _validar_datos_pago(data, archivos, soportes_actuales=recaudo.soportes.count())
    recaudo.fecha = data.get("fecha") or recaudo.fecha
    recaudo.actividad = parsed["actividad"]
    recaudo.padrino = parsed["padrino"]
    recaudo.familia = parsed["familia"]
    recaudo.aportante_nombre = parsed["aportante"]
    recaudo.valor = parsed["valor"]
    recaudo.medio_pago = parsed["medio"]
    recaudo.concepto = (data.get("concepto") or "").strip()
    recaudo.referencia_consignacion = (data.get("referencia_consignacion") or "").strip()
    recaudo.actividad_nombre = parsed["actividad"].nombre
    recaudo.padrino_nombre = parsed["padrino"].nombre_completo
    recaudo.familia_nombre = parsed["familia"].nombre if parsed["familia"] else ""
    recaudo.valor_en_letras = numero_a_letras(parsed["valor"])
    recaudo.save()

    if parsed["medio"] == MedioPago.EFECTIVO or parsed["archivos"]:
        for soporte in list(recaudo.soportes.all()):
            _borrar_campo_archivo(soporte.archivo)
            soporte.delete()
    for uploaded in parsed["archivos"]:
        nombre, content_type, tamano = validate_soporte(uploaded)
        Soporte.objects.create(
            recaudo=recaudo,
            archivo=uploaded,
            nombre_original=nombre,
            content_type=content_type,
            tamano=tamano,
        )
    _regenerar_recibo(recaudo)
    audit.registrar(
        usuario,
        "recaudo.actualizar",
        "recaudo",
        recaudo.id,
        {"numero": recaudo.numero, "valor": str(recaudo.valor)},
        request,
    )
    return recaudo


@transaction.atomic
def confirmar_recaudo(*, usuario, data: dict, archivos: list, request=None) -> Recaudo:
    parsed = _validar_datos_pago(data, archivos)
    org = Organizacion.actual()
    numero = siguiente_numero_recibo()
    recaudo = Recaudo.objects.create(
        numero=numero,
        fecha=data.get("fecha") or date.today(),
        actividad=parsed["actividad"],
        padrino=parsed["padrino"],
        familia=parsed["familia"],
        aportante_nombre=parsed["aportante"],
        valor=parsed["valor"],
        medio_pago=parsed["medio"],
        concepto=(data.get("concepto") or "").strip(),
        referencia_consignacion=(data.get("referencia_consignacion") or "").strip(),
        estado=EstadoRecaudo.CONFIRMADO,
        registrado_por=usuario,
        organizacion_nombre=org.nombre,
        actividad_nombre=parsed["actividad"].nombre,
        padrino_nombre=parsed["padrino"].nombre_completo,
        familia_nombre=parsed["familia"].nombre if parsed["familia"] else "",
        usuario_nombre=usuario.get_full_name() or usuario.get_username(),
        valor_en_letras=numero_a_letras(parsed["valor"]),
    )

    for uploaded in parsed["archivos"]:
        nombre, content_type, tamano = validate_soporte(uploaded)
        Soporte.objects.create(
            recaudo=recaudo,
            archivo=uploaded,
            nombre_original=nombre,
            content_type=content_type,
            tamano=tamano,
        )

    _regenerar_recibo(recaudo)
    audit.registrar(
        usuario,
        "recaudo.confirmar",
        "recaudo",
        recaudo.id,
        {"numero": recaudo.numero, "valor": str(recaudo.valor)},
        request,
    )
    return recaudo


@transaction.atomic
def anular_recaudo(recaudo: Recaudo, usuario, motivo: str, request=None) -> Recaudo:
    if recaudo.estado == EstadoRecaudo.ANULADO:
        raise ValidationError("Este recaudo ya está anulado.")
    motivo = (motivo or "").strip()
    if len(motivo) < 8:
        raise ValidationError("Indique un motivo de anulación (mínimo 8 caracteres).")
    recaudo.estado = EstadoRecaudo.ANULADO
    recaudo.motivo_anulacion = motivo
    recaudo.anulado_en = timezone.now()
    recaudo.anulado_por = usuario
    recaudo.save(
        update_fields=["estado", "motivo_anulacion", "anulado_en", "anulado_por"]
    )
    pdf_bytes = generar_pdf_recibo(recaudo)
    recaudo.recibo.archivo.save(
        f"recibo-{recaudo.numero_formateado}-anulado.pdf",
        ContentFile(pdf_bytes),
        save=True,
    )
    audit.registrar(
        usuario,
        "recaudo.anular",
        "recaudo",
        recaudo.id,
        {"numero": recaudo.numero, "motivo": motivo},
        request,
    )
    return recaudo


def filtrar_recaudos(params) -> tuple:
    qs = Recaudo.objects.select_related(
        "actividad", "padrino", "familia", "registrado_por", "recibo"
    ).prefetch_related("soportes")
    padrino = params.get("padrino")
    familia = params.get("familia")
    actividad = params.get("actividad")
    medio = params.get("medio_pago")
    recibo = params.get("recibo")
    desde = params.get("fecha_inicial")
    hasta = params.get("fecha_final")
    estado = params.get("estado")
    q = params.get("q")

    if padrino:
        qs = qs.filter(padrino_id=padrino)
    if familia:
        qs = qs.filter(familia_id=familia)
    if actividad:
        qs = qs.filter(actividad_id=actividad)
    if medio:
        qs = qs.filter(medio_pago=medio)
    if recibo:
        digits = "".join(ch for ch in str(recibo) if ch.isdigit())
        if digits:
            qs = qs.filter(numero=int(digits))
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    if estado:
        qs = qs.filter(estado=estado)
    if q:
        texto = (
            Q(aportante_nombre__icontains=q)
            | Q(concepto__icontains=q)
            | Q(referencia_consignacion__icontains=q)
            | Q(padrino_nombre__icontains=q)
            | Q(actividad_nombre__icontains=q)
            | Q(familia_nombre__icontains=q)
        )
        digits = "".join(ch for ch in str(q) if ch.isdigit())
        if digits:
            texto |= Q(numero=int(digits))
        qs = qs.filter(texto)
    return qs


def totales_de(qs):
    confirmados = qs.filter(estado=EstadoRecaudo.CONFIRMADO)
    anulados = qs.filter(estado=EstadoRecaudo.ANULADO)

    def agrupado(field):
        rows = (
            confirmados.values(field)
            .annotate(total=Sum("valor"), cantidad=Count("id"))
            .order_by()
        )
        nombres = {}
        if field == "actividad_id":
            nombres = {
                str(a.id): a.nombre
                for a in Actividad.objects.filter(id__in=[r[field] for r in rows if r[field]])
            }
        elif field == "padrino_id":
            nombres = {
                str(p.id): p.nombre_completo
                for p in Padrino.objects.filter(id__in=[r[field] for r in rows if r[field]])
            }
        elif field == "familia_id":
            ids = [r[field] for r in rows if r[field]]
            nombres = {str(f.id): f.nombre for f in Familia.objects.filter(id__in=ids)}
        resultado = []
        for row in rows:
            key = row[field]
            nombre = nombres.get(str(key), "Sin familia") if key else "Sin familia"
            if field == "actividad_id":
                nombre = nombres.get(str(key), "")
            if field == "padrino_id":
                nombre = nombres.get(str(key), "")
            total_fila = money(row["total"] or Decimal("0.00"))
            resultado.append(
                {
                    "id": str(key) if key else None,
                    "nombre": nombre,
                    "total": str(total_fila),
                    "total_formato": format_cop(total_fila),
                    "cantidad": row["cantidad"],
                }
            )
        resultado.sort(key=lambda item: item["nombre"])
        return resultado

    total = money(confirmados.aggregate(total=Sum("valor"))["total"] or Decimal("0.00"))
    return {
        "total_confirmado": str(total),
        "cantidad_confirmados": confirmados.count(),
        "cantidad_anulados": anulados.count(),
        "por_actividad": agrupado("actividad_id"),
        "por_padrino": agrupado("padrino_id"),
        "por_familia": agrupado("familia_id"),
        "por_fecha": _agrupar_por_fecha(confirmados),
    }


def _agrupar_por_fecha(confirmados):
    rows = (
        confirmados.values("fecha")
        .annotate(total=Sum("valor"), cantidad=Count("id"))
        .order_by("-fecha")
    )
    resultado = []
    for row in rows:
        total_fila = money(row["total"] or Decimal("0.00"))
        fecha = row["fecha"].isoformat() if hasattr(row["fecha"], "isoformat") else str(row["fecha"])
        resultado.append(
            {
                "fecha": fecha,
                "nombre": fecha,
                "total": str(total_fila),
                "total_formato": format_cop(total_fila),
                "cantidad": row["cantidad"],
            }
        )
    return resultado


def _int_param(params, name, default, *, minimum=1, maximum=50):
    raw = params.get(name)
    try:
        value = int(raw) if raw not in (None, "") else default
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def informe(params, *, paginar_pendientes=True) -> dict:
    """Informes: actividad, padrino, fecha, cruzado padrino×actividad y pendientes."""
    qs = filtrar_recaudos(params)
    data = totales_de(qs)
    cruzado, pendientes = _cruzado_y_pendientes(params, qs, paginar=paginar_pendientes)
    data["por_padrino_actividad"] = cruzado
    data["pendientes"] = pendientes
    return data


def _cruzado_y_pendientes(params, qs, *, paginar=True):
    padrino_id = params.get("padrino") or None
    actividad_id = params.get("actividad") or None

    actividades = Actividad.objects.all()
    if actividad_id:
        actividades = actividades.filter(id=actividad_id)
    else:
        actividades = actividades.exclude(estado=EstadoActividad.CERRADA)
    actividades = list(actividades.order_by("nombre"))

    padrinos = Padrino.objects.filter(estado=EstadoRegistro.ACTIVO)
    if padrino_id:
        padrinos = padrinos.filter(id=padrino_id)
    padrinos = list(padrinos.order_by("nombre_completo"))
    padrino_nombres = {p.id: p.nombre_completo for p in padrinos}

    familias = Familia.objects.filter(estado=EstadoRegistro.ACTIVO)
    if padrino_id:
        familias = familias.filter(padrino_id=padrino_id)
    fam_rows = list(familias.values("id", "nombre", "telefono", "padrino_id"))

    asignadas = defaultdict(int)
    for fam in fam_rows:
        asignadas[fam["padrino_id"]] += 1
    faltan_nombres = {fam["padrino_id"] for fam in fam_rows} - set(padrino_nombres)
    if faltan_nombres:
        for extra in Padrino.objects.filter(id__in=faltan_nombres):
            padrino_nombres[extra.id] = extra.nombre_completo

    money_map = {}
    confirmados = qs.filter(estado=EstadoRecaudo.CONFIRMADO)
    for row in confirmados.values("padrino_id", "actividad_id").annotate(
        total=Sum("valor"), cantidad=Count("id")
    ):
        money_map[(row["padrino_id"], row["actividad_id"])] = row

    paid_qs = Recaudo.objects.filter(
        estado=EstadoRecaudo.CONFIRMADO, familia_id__isnull=False
    )
    if actividad_id:
        paid_qs = paid_qs.filter(actividad_id=actividad_id)
    elif actividades:
        paid_qs = paid_qs.filter(actividad_id__in=[a.id for a in actividades])
    else:
        paid_qs = paid_qs.none()
    paid_pairs = set(paid_qs.values_list("familia_id", "actividad_id"))

    pagaron_ahora = defaultdict(set)
    pendientes_list = []
    act_ids_nombres = [(a.id, a.nombre) for a in actividades]
    for fam in fam_rows:
        for act_id, act_nombre in act_ids_nombres:
            if (fam["id"], act_id) in paid_pairs:
                pagaron_ahora[(fam["padrino_id"], act_id)].add(fam["id"])
            else:
                pendientes_list.append(
                    {
                        "familia_id": str(fam["id"]),
                        "familia_nombre": fam["nombre"],
                        "telefono": fam["telefono"] or "",
                        "padrino_id": str(fam["padrino_id"]),
                        "padrino_nombre": padrino_nombres.get(fam["padrino_id"], ""),
                        "actividad_id": str(act_id),
                        "actividad_nombre": act_nombre,
                    }
                )

    pendientes_list.sort(
        key=lambda item: (item["padrino_nombre"], item["actividad_nombre"], item["familia_nombre"])
    )

    cruzado = []
    for padrino in padrinos:
        for actividad in actividades:
            money_row = money_map.get((padrino.id, actividad.id), {})
            total_fila = money(money_row.get("total") or Decimal("0.00"))
            asign = asignadas.get(padrino.id, 0)
            pagaron = len(pagaron_ahora.get((padrino.id, actividad.id), set()))
            cruzado.append(
                {
                    "padrino_id": str(padrino.id),
                    "padrino_nombre": padrino.nombre_completo,
                    "actividad_id": str(actividad.id),
                    "actividad_nombre": actividad.nombre,
                    "total": str(total_fila),
                    "total_formato": format_cop(total_fila),
                    "cantidad": int(money_row.get("cantidad") or 0),
                    "familias_asignadas": asign,
                    "familias_pagaron": pagaron,
                    "familias_pendientes": max(asign - pagaron, 0),
                }
            )

    asignadas_total = len(fam_rows)
    familias_con_pendiente = {item["familia_id"] for item in pendientes_list}
    pendientes_payload = {
        "count": len(pendientes_list),
        "familias_asignadas": asignadas_total,
        "familias_al_dia": max(asignadas_total - len(familias_con_pendiente), 0),
        "results": pendientes_list,
    }
    if paginar:
        page = _int_param(params, "page", 1, minimum=1, maximum=10_000)
        page_size = _int_param(params, "page_size", 20, minimum=1, maximum=50)
        paginator = Paginator(pendientes_list, page_size)
        page_obj = paginator.get_page(page)
        pendientes_payload.update(
            {
                "page": page_obj.number,
                "page_size": page_size,
                "pages": paginator.num_pages or 1,
                "results": list(page_obj.object_list),
            }
        )
    return cruzado, pendientes_payload


def smtp_configurado() -> bool:
    return bool(settings.EMAIL_HOST and settings.EMAIL_HOST_USER)


def mensaje_recibo(recaudo: Recaudo) -> str:
    org = recaudo.organizacion_nombre
    return (
        f"{org}: recibo de caja N.º {recaudo.numero_formateado} "
        f"por {format_cop(recaudo.valor)} ({recaudo.valor_en_letras}). "
        f"Actividad: {recaudo.actividad_nombre}. Familia: {recaudo.aportante_nombre}. "
        f"Es una constancia de recaudo, no un certificado tributario. "
        f"Adjunte el PDF del recibo en este chat."
    )


def telefono_whatsapp(raw: str) -> str:
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(digits) == 10 and digits.startswith("3"):
        return "57" + digits
    return digits


def payload_compartir(recaudo: Recaudo) -> dict:
    mensaje = mensaje_recibo(recaudo)
    texto = quote(mensaje)
    telefono_familia = ""
    if recaudo.familia and recaudo.familia.telefono:
        telefono_familia = telefono_whatsapp(recaudo.familia.telefono)
    wa_general = f"https://wa.me/?text={texto}"
    wa_familia = (
        f"https://wa.me/{telefono_familia}?text={texto}" if telefono_familia else None
    )
    destinatario = ""
    if recaudo.familia and recaudo.familia.correo:
        destinatario = recaudo.familia.correo
    asunto = quote(f"Recibo de caja {recaudo.numero_formateado} · {recaudo.organizacion_nombre}")
    mailto = f"mailto:{destinatario}?subject={asunto}&body={texto}"
    return {
        "mensaje": mensaje,
        "whatsapp_url": wa_general,
        "whatsapp_url_destino": wa_familia or wa_general,
        "telefono_destino": telefono_familia or None,
        "familia_id": str(recaudo.familia_id) if recaudo.familia_id else None,
        "familia_nombre": recaudo.familia.nombre if recaudo.familia_id else recaudo.aportante_nombre,
        "tiene_telefono_familia": bool(telefono_familia),
        "mailto": mailto,
        "destinatario_sugerido": destinatario or None,
        "smtp_configurado": smtp_configurado(),
        "aviso_whatsapp": (
            "Se abre el chat de WhatsApp de la familia con el mensaje del recibo. "
            "El envío no es automático: adjunte el PDF con el clip o con Compartir."
        ),
        "aviso_correo": (
            "Si el envío por servidor no está configurado, se abre el cliente de correo "
            "con destinatario, asunto y texto. Descargue el PDF para adjuntarlo."
        ),
    }


def enviar_recibo_por_correo(recaudo: Recaudo, usuario, destinatario: str, request=None) -> EnvioCorreo:
    destinatario = (destinatario or "").strip()
    if not destinatario:
        raise ValidationError("Indique un correo destinatario.")
    asunto = f"Recibo de caja {recaudo.numero_formateado} · {recaudo.organizacion_nombre}"
    cuerpo = mensaje_recibo(recaudo)
    if not smtp_configurado():
        envio = EnvioCorreo.objects.create(
            recaudo=recaudo,
            destinatario=destinatario,
            asunto=asunto,
            resultado=ResultadoEnvio.NO_CONFIGURADO,
            detalle="SMTP no configurado. Use el cliente de correo del dispositivo y adjunte el PDF descargado.",
            usuario=usuario,
        )
        audit.registrar(
            usuario,
            "correo.no_configurado",
            "recaudo",
            recaudo.id,
            {"destinatario": destinatario},
            request,
        )
        return envio

    email = EmailMessage(
        subject=asunto,
        body=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
    )
    try:
        recaudo.recibo.archivo.open("rb")
        pdf = recaudo.recibo.archivo.read()
        recaudo.recibo.archivo.close()
        email.attach(
            f"recibo-{recaudo.numero_formateado}.pdf",
            pdf,
            "application/pdf",
        )
        email.send(fail_silently=False)
        envio = EnvioCorreo.objects.create(
            recaudo=recaudo,
            destinatario=destinatario,
            asunto=asunto,
            resultado=ResultadoEnvio.ENVIADO,
            detalle="Enviado por SMTP.",
            usuario=usuario,
        )
        audit.registrar(
            usuario,
            "correo.enviado",
            "recaudo",
            recaudo.id,
            {"destinatario": destinatario},
            request,
        )
        return envio
    except Exception as exc:
        envio = EnvioCorreo.objects.create(
            recaudo=recaudo,
            destinatario=destinatario,
            asunto=asunto,
            resultado=ResultadoEnvio.ERROR,
            detalle=str(exc),
            usuario=usuario,
        )
        audit.registrar(
            usuario,
            "correo.error",
            "recaudo",
            recaudo.id,
            {"destinatario": destinatario, "error": str(exc)},
            request,
        )
        return envio
