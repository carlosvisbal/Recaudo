from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
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
    ActividadParticipante,
    ActividadPersona,
    AsignacionFamiliaHistorial,
    CobroCada,
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
    TipoActividad,
)
from .money import format_cop, money, numero_a_letras
from .pdf import generar_pdf_recibo
from .periodos import (
    etiqueta_cobro,
    etiqueta_periodo_clave,
    inicio_periodo,
    listar_periodos,
    rango_cobro,
)


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


def _rango_actividad(actividad: Actividad, ref: date | None = None) -> tuple[date, date]:
    return rango_cobro(
        actividad.cobro_cada or CobroCada.MES,
        ref or date.today(),
        fecha_inicio=actividad.fecha_inicio,
        fecha_fin=actividad.fecha_fin,
    )


def _etiqueta_periodo_actividad(actividad: Actividad, ref: date | None = None) -> str:
    return etiqueta_cobro(
        actividad.cobro_cada or CobroCada.MES,
        ref or date.today(),
        fecha_inicio=actividad.fecha_inicio,
        fecha_fin=actividad.fecha_fin,
    )


def _asegurar_participante(actividad: Actividad, familia: Familia) -> None:
    """Si la familia no está en la actividad, la agrega (flujo fácil al cobrar)."""
    ActividadParticipante.objects.get_or_create(
        actividad=actividad,
        familia=familia,
        defaults={"padrino_id": familia.padrino_id},
    )


def _resolver_periodo_inicio(actividad: Actividad, data: dict) -> date:
    """
    Período al que aplica el pago.
    - Si viene periodo_inicio, se normaliza al inicio del tramo.
    - Si no, se deriva de la fecha de registro (compatibilidad).
    """
    cobro = actividad.cobro_cada or CobroCada.MES
    raw = data.get("periodo_inicio")
    if raw:
        if isinstance(raw, str):
            raw = date.fromisoformat(str(raw)[:10])
        if cobro == CobroCada.UNA_VEZ:
            return actividad.fecha_inicio
        return inicio_periodo(cobro, raw)
    fecha_pago = data.get("fecha") or date.today()
    if cobro == CobroCada.UNA_VEZ:
        return actividad.fecha_inicio
    return inicio_periodo(cobro, fecha_pago)


def ya_pago_en_periodo(
    actividad: Actividad,
    *,
    familia: Familia | None = None,
    persona: ActividadPersona | None = None,
    periodo_inicio: date | None = None,
    fecha: date | None = None,
    exclude_recaudo_id=None,
) -> Recaudo | None:
    """Devuelve el pago confirmado del mismo período cobrado, si existe."""
    cobro = actividad.cobro_cada or CobroCada.MES
    if periodo_inicio is None:
        periodo_inicio = _resolver_periodo_inicio(
            actividad, {"fecha": fecha or date.today()}
        )
    else:
        if cobro != CobroCada.UNA_VEZ:
            periodo_inicio = inicio_periodo(cobro, periodo_inicio)

    qs = Recaudo.objects.filter(
        actividad=actividad,
        estado=EstadoRecaudo.CONFIRMADO,
        periodo_inicio=periodo_inicio,
    ).order_by("-numero")
    # Compatibilidad: pagos antiguos sin periodo_inicio (solo si aún quedan null)
    if not qs.exists():
        inicio, fin = _rango_actividad(actividad, periodo_inicio)
        qs = Recaudo.objects.filter(
            actividad=actividad,
            estado=EstadoRecaudo.CONFIRMADO,
            periodo_inicio__isnull=True,
            fecha__gte=inicio,
            fecha__lte=fin,
        ).order_by("-numero")
    if familia:
        qs = qs.filter(familia=familia)
    elif persona:
        qs = qs.filter(persona=persona)
    else:
        return None
    if exclude_recaudo_id:
        qs = qs.exclude(pk=exclude_recaudo_id)
    return qs.first()


def _validar_datos_pago(
    data: dict,
    archivos: list,
    *,
    soportes_actuales: int = 0,
    exclude_recaudo_id=None,
) -> dict:
    actividad: Actividad = data["actividad"]
    padrino: Padrino | None = data.get("padrino")
    familia: Familia | None = data.get("familia")
    persona: ActividadPersona | None = data.get("persona")

    if actividad.estado == EstadoActividad.CERRADA:
        raise ValidationError("No se pueden registrar recaudos en una actividad cerrada.")

    if actividad.tipo == TipoActividad.GENERAL:
        if not persona:
            raise ValidationError("Elija la persona que está pagando.")
        if persona.actividad_id != actividad.id:
            raise ValidationError("Esa persona no pertenece a esta actividad.")
        padrino = None
        familia = None
    else:
        if not padrino:
            raise ValidationError("Elija el padrino a quien se evidencia el pago.")
        if not familia:
            raise ValidationError("Elija la familia que está realizando el pago.")
        if padrino.estado != EstadoRegistro.ACTIVO:
            raise ValidationError("El padrino responsable está inactivo.")
        if familia.estado != EstadoRegistro.ACTIVO:
            raise ValidationError("La familia está inactiva.")
        if familia.padrino_id != padrino.id:
            raise ValidationError("Esa familia no pertenece al padrino elegido.")
        persona = None

    valor = money(data["valor"])
    if valor <= Decimal("0.00"):
        raise ValidationError("El valor recibido debe ser mayor que cero.")

    medio = data["medio_pago"]
    if medio not in MedioPago.values:
        raise ValidationError("Medio de pago no válido.")

    aportante = (data.get("aportante_nombre") or "").strip()
    if not aportante:
        if familia:
            aportante = familia.nombre
        elif persona:
            aportante = persona.nombre
    if not aportante:
        raise ValidationError("Indique quién entrega el dinero.")

    archivos = archivos or []
    if medio == MedioPago.EFECTIVO and archivos:
        raise ValidationError("El pago en efectivo no lleva soporte. No adjunte archivos.")
    if medio == MedioPago.TRANSFERENCIA and not archivos and soportes_actuales == 0:
        raise ValidationError(
            "La transferencia requiere el comprobante adjunto (PDF o archivo de imagen)."
        )
    if len(archivos) > settings.MAX_SOPORTES_POR_RECAUDO:
        raise ValidationError("Puede adjuntar como máximo 8 soportes.")

    periodo = _resolver_periodo_inicio(actividad, data)
    aviso_duplicado = None
    if familia:
        _asegurar_participante(actividad, familia)
        previo = ya_pago_en_periodo(
            actividad,
            familia=familia,
            periodo_inicio=periodo,
            exclude_recaudo_id=exclude_recaudo_id,
        )
        nombre = familia.nombre
    elif persona:
        previo = ya_pago_en_periodo(
            actividad,
            persona=persona,
            periodo_inicio=periodo,
            exclude_recaudo_id=exclude_recaudo_id,
        )
        nombre = persona.nombre
    else:
        previo = None
        nombre = aportante

    if previo:
        etiqueta = etiqueta_periodo_clave(
            actividad.cobro_cada or CobroCada.MES, periodo
        )
        aviso_duplicado = (
            f"{nombre} ya tiene un pago de {etiqueta} "
            f"(recibo {previo.numero_formateado} por {format_cop(previo.valor)}). "
            "Si continúa, se registrará un pago adicional de ese mismo período."
        )

    return {
        "actividad": actividad,
        "padrino": padrino,
        "familia": familia,
        "persona": persona,
        "periodo_inicio": periodo,
        "valor": valor,
        "medio": medio,
        "aportante": aportante,
        "archivos": archivos,
        "aviso_duplicado": aviso_duplicado,
    }


def _regenerar_recibo(recaudo: Recaudo) -> None:
    pdf_bytes = generar_pdf_recibo(recaudo)
    recibo, _ = ReciboPdf.objects.get_or_create(recaudo=recaudo)
    recibo.archivo.save(
        f"recibo-{recaudo.numero_formateado}.pdf",
        ContentFile(pdf_bytes),
        save=True,
    )


def _guardar_soporte(recaudo: Recaudo, uploaded) -> Soporte:
    """Persiste el soporte con nombre de archivo = UUID + extensión."""
    nombre, content_type, tamano = validate_soporte(uploaded)
    ext = Path(nombre).suffix.lower() or ".bin"
    soporte = Soporte(
        recaudo=recaudo,
        nombre_original=nombre,
        content_type=content_type,
        tamano=tamano,
    )
    # El id UUID ya está asignado; upload_to usa instance.id
    soporte.archivo.save(f"{soporte.id}{ext}", uploaded, save=True)
    return soporte


def sincronizar_participantes(actividad: Actividad, familia_ids: list) -> None:
    """Reemplaza las familias de la actividad por la lista indicada."""
    ids = []
    for raw in familia_ids or []:
        if raw in (None, ""):
            continue
        ids.append(str(raw))
    # únicos preservando orden
    seen = set()
    uniq = []
    for fid in ids:
        if fid in seen:
            continue
        seen.add(fid)
        uniq.append(fid)

    familias = {
        str(f.id): f
        for f in Familia.objects.select_related("padrino").filter(id__in=uniq)
    }
    faltan = [fid for fid in uniq if fid not in familias]
    if faltan:
        raise ValidationError(
            {"familias": f"No se encontraron {len(faltan)} familia(s) indicada(s)."}
        )

    actuales = {
        str(p.familia_id): p
        for p in ActividadParticipante.objects.filter(actividad=actividad)
    }
    keep = set()
    for fid in uniq:
        familia = familias[fid]
        keep.add(fid)
        existente = actuales.get(fid)
        if existente:
            if existente.padrino_id != familia.padrino_id:
                existente.padrino = familia.padrino
                existente.save(update_fields=["padrino"])
        else:
            ActividadParticipante.objects.create(
                actividad=actividad,
                familia=familia,
                padrino=familia.padrino,
            )
    ActividadParticipante.objects.filter(actividad=actividad).exclude(
        familia_id__in=keep
    ).delete()


def sincronizar_personas(actividad: Actividad, personas: list) -> None:
    """
    Reemplaza las personas de una actividad general.
    cada item: {id?, nombre, telefono}
    """
    keep_ids = set()
    for raw in personas or []:
        if not isinstance(raw, dict):
            continue
        nombre = (raw.get("nombre") or "").strip()
        if not nombre:
            continue
        telefono = (raw.get("telefono") or "").strip()
        pid = raw.get("id")
        if pid:
            try:
                persona = ActividadPersona.objects.get(pk=pid, actividad=actividad)
            except ActividadPersona.DoesNotExist:
                persona = ActividadPersona(actividad=actividad)
            persona.nombre = nombre
            persona.telefono = telefono
            persona.save()
            keep_ids.add(persona.id)
        else:
            persona = ActividadPersona.objects.create(
                actividad=actividad, nombre=nombre, telefono=telefono
            )
            keep_ids.add(persona.id)
    ActividadPersona.objects.filter(actividad=actividad).exclude(id__in=keep_ids).delete()


def _ids_pagaron_periodo(actividad: Actividad, inicio: date, *, por: str) -> set:
    """IDs de familia o persona que ya tienen pago del período (periodo_inicio)."""
    field = "familia_id" if por == "familia" else "persona_id"
    qs = Recaudo.objects.filter(
        actividad=actividad,
        estado=EstadoRecaudo.CONFIRMADO,
        **{f"{field}__isnull": False},
        periodo_inicio=inicio,
    )
    ids = set(qs.values_list(field, flat=True))
    # Compatibilidad con recaudos antiguos sin periodo_inicio
    fin = _rango_actividad(actividad, inicio)[1]
    legacy = Recaudo.objects.filter(
        actividad=actividad,
        estado=EstadoRecaudo.CONFIRMADO,
        periodo_inicio__isnull=True,
        fecha__gte=inicio,
        fecha__lte=fin,
        **{f"{field}__isnull": False},
    ).values_list(field, flat=True)
    ids.update(legacy)
    return ids


def control_actividad(actividad: Actividad, *, ref: date | None = None) -> dict:
    """Listas Pagaron / Faltan del período cobrado (no de la fecha de registro)."""
    ref = ref or date.today()
    inicio, fin = _rango_actividad(actividad, ref)
    # Normalizar a la clave del período
    if actividad.cobro_cada != CobroCada.UNA_VEZ:
        inicio = inicio_periodo(actividad.cobro_cada or CobroCada.MES, ref)
        fin = _rango_actividad(actividad, inicio)[1]
    base = {
        "actividad_id": str(actividad.id),
        "actividad_nombre": actividad.nombre,
        "tipo": actividad.tipo,
        "tipo_label": actividad.get_tipo_display(),
        "cobro_cada": actividad.cobro_cada,
        "cobro_cada_label": actividad.get_cobro_cada_display(),
        "etiqueta_periodo": _etiqueta_periodo_actividad(actividad, inicio),
        "periodo_inicio": inicio.isoformat(),
        "fecha_inicial": inicio.isoformat(),
        "fecha_final": fin.isoformat(),
        "periodos": listar_periodos(
            actividad.cobro_cada or CobroCada.MES,
            desde=actividad.fecha_inicio,
            hasta=actividad.fecha_fin,
            alrededor=ref,
        ),
    }

    if actividad.tipo == TipoActividad.GENERAL:
        personas = list(actividad.personas.all().order_by("nombre"))
        pagaron_ids = _ids_pagaron_periodo(actividad, inicio, por="persona")
        pagaron = []
        faltan = []
        for persona in personas:
            fila = {
                "persona_id": str(persona.id),
                "persona_nombre": persona.nombre,
                "telefono": persona.telefono or "",
            }
            if persona.id in pagaron_ids:
                pagaron.append(fila)
            else:
                faltan.append(fila)
        return {
            **base,
            "pagaron": pagaron,
            "faltan": faltan,
            "cantidad_pagaron": len(pagaron),
            "cantidad_faltan": len(faltan),
            "cantidad_familias": len(personas),
            "cantidad_personas": len(personas),
        }

    participantes = list(
        ActividadParticipante.objects.filter(actividad=actividad)
        .select_related("familia", "padrino")
        .order_by("padrino__nombre_completo", "familia__nombre")
    )
    pagaron_ids = _ids_pagaron_periodo(actividad, inicio, por="familia")

    pagaron = []
    faltan = []
    for part in participantes:
        fila = {
            "familia_id": str(part.familia_id),
            "familia_nombre": part.familia.nombre,
            "telefono": part.familia.telefono or "",
            "padrino_id": str(part.padrino_id),
            "padrino_nombre": part.padrino.nombre_completo,
        }
        if part.familia_id in pagaron_ids:
            pagaron.append(fila)
        else:
            faltan.append(fila)

    return {
        **base,
        "pagaron": pagaron,
        "faltan": faltan,
        "cantidad_pagaron": len(pagaron),
        "cantidad_faltan": len(faltan),
        "cantidad_familias": len(participantes),
        "cantidad_personas": 0,
    }


@transaction.atomic
def actualizar_recaudo(*, recaudo: Recaudo, usuario, data: dict, archivos: list, request=None) -> Recaudo:
    if recaudo.estado == EstadoRecaudo.ANULADO:
        raise ValidationError("No se puede editar un pago anulado. Elimínelo si debe quitarlo.")
    parsed = _validar_datos_pago(
        data,
        archivos,
        soportes_actuales=recaudo.soportes.count(),
        exclude_recaudo_id=recaudo.id,
    )
    recaudo.fecha = data.get("fecha") or recaudo.fecha
    recaudo.periodo_inicio = parsed["periodo_inicio"]
    recaudo.actividad = parsed["actividad"]
    recaudo.padrino = parsed["padrino"]
    recaudo.familia = parsed["familia"]
    recaudo.persona = parsed.get("persona")
    recaudo.aportante_nombre = parsed["aportante"]
    recaudo.valor = parsed["valor"]
    recaudo.medio_pago = parsed["medio"]
    recaudo.concepto = (data.get("concepto") or "").strip()
    recaudo.referencia_consignacion = (data.get("referencia_consignacion") or "").strip()
    recaudo.actividad_nombre = parsed["actividad"].nombre
    recaudo.padrino_nombre = (
        parsed["padrino"].nombre_completo if parsed["padrino"] else ""
    )
    recaudo.familia_nombre = parsed["familia"].nombre if parsed["familia"] else ""
    recaudo.valor_en_letras = numero_a_letras(parsed["valor"])
    recaudo.save()

    if parsed["medio"] == MedioPago.EFECTIVO or parsed["archivos"]:
        for soporte in list(recaudo.soportes.all()):
            _borrar_campo_archivo(soporte.archivo)
            soporte.delete()
    for uploaded in parsed["archivos"]:
        _guardar_soporte(recaudo, uploaded)
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
        periodo_inicio=parsed["periodo_inicio"],
        actividad=parsed["actividad"],
        padrino=parsed["padrino"],
        familia=parsed["familia"],
        persona=parsed.get("persona"),
        aportante_nombre=parsed["aportante"],
        valor=parsed["valor"],
        medio_pago=parsed["medio"],
        concepto=(data.get("concepto") or "").strip(),
        referencia_consignacion=(data.get("referencia_consignacion") or "").strip(),
        estado=EstadoRecaudo.CONFIRMADO,
        registrado_por=usuario,
        organizacion_nombre=org.nombre,
        actividad_nombre=parsed["actividad"].nombre,
        padrino_nombre=(
            parsed["padrino"].nombre_completo if parsed["padrino"] else ""
        ),
        familia_nombre=parsed["familia"].nombre if parsed["familia"] else "",
        usuario_nombre=usuario.get_full_name() or usuario.get_username(),
        valor_en_letras=numero_a_letras(parsed["valor"]),
    )

    for uploaded in parsed["archivos"]:
        _guardar_soporte(recaudo, uploaded)

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
    qs = (
        Recaudo.objects.select_related(
            "actividad", "padrino", "familia", "persona", "registrado_por", "recibo"
        )
        .prefetch_related("soportes")
        .annotate(soportes_count_annot=Count("soportes", distinct=True))
        .order_by("-numero")
    )
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
    """Pendientes = familias de la actividad sin pago confirmado en el tramo (mes/quincena)."""
    padrino_id = params.get("padrino") or None
    actividad_id = params.get("actividad") or None
    ref = date.today()
    # Si el informe trae fecha_final, úsala como referencia del tramo
    raw_fin = params.get("fecha_final")
    if raw_fin:
        try:
            ref = date.fromisoformat(str(raw_fin)[:10])
        except ValueError:
            ref = date.today()

    actividades = Actividad.objects.all()
    if actividad_id:
        actividades = actividades.filter(id=actividad_id)
    else:
        actividades = actividades.exclude(estado=EstadoActividad.CERRADA)
    actividades = list(actividades.order_by("nombre"))
    act_by_id = {a.id: a for a in actividades}

    act_ids = [a.id for a in actividades]
    if act_ids:
        partes_qs = ActividadParticipante.objects.filter(
            actividad_id__in=act_ids
        ).select_related("familia", "padrino", "actividad")
        if padrino_id:
            partes_qs = partes_qs.filter(padrino_id=padrino_id)
        participantes = list(partes_qs)
    else:
        participantes = []

    padrino_ids = {p.padrino_id for p in participantes}
    padrinos = list(
        Padrino.objects.filter(id__in=padrino_ids).order_by("nombre_completo")
        if padrino_ids
        else Padrino.objects.none()
    )
    if padrino_id and not padrinos:
        padrinos = list(Padrino.objects.filter(id=padrino_id))
    padrino_nombres = {p.id: p.nombre_completo for p in padrinos}

    asignadas = defaultdict(int)
    for part in participantes:
        asignadas[(part.padrino_id, part.actividad_id)] += 1

    money_map = {}
    confirmados = qs.filter(estado=EstadoRecaudo.CONFIRMADO)
    for row in confirmados.values("padrino_id", "actividad_id").annotate(
        total=Sum("valor"), cantidad=Count("id")
    ):
        money_map[(row["padrino_id"], row["actividad_id"])] = row

    # Pagos del período cobrado (periodo_inicio), no de la fecha de registro
    paid_pairs = set()
    paid_personas = set()
    claves: dict[date, list] = defaultdict(list)
    for actividad in actividades:
        if actividad.cobro_cada == CobroCada.UNA_VEZ:
            clave = actividad.fecha_inicio
        else:
            clave = inicio_periodo(actividad.cobro_cada or CobroCada.MES, ref)
        claves[clave].append(actividad.id)
    for clave, ids in claves.items():
        for fam_id, act_id in Recaudo.objects.filter(
            estado=EstadoRecaudo.CONFIRMADO,
            familia_id__isnull=False,
            actividad_id__in=ids,
            periodo_inicio=clave,
        ).values_list("familia_id", "actividad_id"):
            paid_pairs.add((fam_id, act_id))
        for persona_id, act_id in Recaudo.objects.filter(
            estado=EstadoRecaudo.CONFIRMADO,
            persona_id__isnull=False,
            actividad_id__in=ids,
            periodo_inicio=clave,
        ).values_list("persona_id", "actividad_id"):
            paid_personas.add((persona_id, act_id))
        # Compatibilidad: recaudos antiguos sin periodo_inicio
        for act_id in ids:
            act = act_by_id.get(act_id)
            if not act:
                continue
            inicio, fin = _rango_actividad(act, clave)
            for fam_id in Recaudo.objects.filter(
                estado=EstadoRecaudo.CONFIRMADO,
                familia_id__isnull=False,
                actividad_id=act_id,
                periodo_inicio__isnull=True,
                fecha__gte=inicio,
                fecha__lte=fin,
            ).values_list("familia_id", flat=True):
                paid_pairs.add((fam_id, act_id))
            for persona_id in Recaudo.objects.filter(
                estado=EstadoRecaudo.CONFIRMADO,
                persona_id__isnull=False,
                actividad_id=act_id,
                periodo_inicio__isnull=True,
                fecha__gte=inicio,
                fecha__lte=fin,
            ).values_list("persona_id", flat=True):
                paid_personas.add((persona_id, act_id))

    pagaron_ahora = defaultdict(set)
    pendientes_list = []
    for part in participantes:
        act = act_by_id.get(part.actividad_id) or part.actividad
        key = (part.familia_id, part.actividad_id)
        if key in paid_pairs:
            pagaron_ahora[(part.padrino_id, part.actividad_id)].add(part.familia_id)
        else:
            pendientes_list.append(
                {
                    "familia_id": str(part.familia_id),
                    "familia_nombre": part.familia.nombre,
                    "telefono": part.familia.telefono or "",
                    "padrino_id": str(part.padrino_id),
                    "padrino_nombre": padrino_nombres.get(
                        part.padrino_id, part.padrino.nombre_completo
                    ),
                    "actividad_id": str(part.actividad_id),
                    "actividad_nombre": act.nombre,
                    "cobro_cada": act.cobro_cada,
                    "tipo": act.tipo,
                }
            )

    # Pendientes de actividades generales (personas)
    generales = [a for a in actividades if a.tipo == TipoActividad.GENERAL]
    if generales:
        personas_qs = ActividadPersona.objects.filter(
            actividad_id__in=[a.id for a in generales]
        ).select_related("actividad")
        for persona in personas_qs:
            if (persona.id, persona.actividad_id) in paid_personas:
                continue
            act = act_by_id.get(persona.actividad_id) or persona.actividad
            pendientes_list.append(
                {
                    "persona_id": str(persona.id),
                    "familia_id": None,
                    "familia_nombre": persona.nombre,
                    "telefono": persona.telefono or "",
                    "padrino_id": None,
                    "padrino_nombre": "Sin padrino",
                    "actividad_id": str(persona.actividad_id),
                    "actividad_nombre": act.nombre,
                    "cobro_cada": act.cobro_cada,
                    "tipo": act.tipo,
                }
            )

    pendientes_list.sort(
        key=lambda item: (
            item["padrino_nombre"],
            item["actividad_nombre"],
            item["familia_nombre"],
        )
    )

    # Cruzado: solo pares padrino×actividad que tienen participantes o dinero
    pares = set(asignadas.keys()) | set(money_map.keys())
    if not pares and padrinos and actividades:
        pares = {(p.id, a.id) for p in padrinos for a in actividades}

    cruzado = []
    for padrino_pk, actividad_pk in sorted(
        pares,
        key=lambda pair: (
            padrino_nombres.get(pair[0], ""),
            act_by_id[pair[1]].nombre if pair[1] in act_by_id else "",
        ),
    ):
        actividad = act_by_id.get(actividad_pk)
        if not actividad:
            continue
        money_row = money_map.get((padrino_pk, actividad_pk), {})
        total_fila = money(money_row.get("total") or Decimal("0.00"))
        asign = asignadas.get((padrino_pk, actividad_pk), 0)
        pagaron = len(pagaron_ahora.get((padrino_pk, actividad_pk), set()))
        cruzado.append(
            {
                "padrino_id": str(padrino_pk),
                "padrino_nombre": padrino_nombres.get(padrino_pk, ""),
                "actividad_id": str(actividad_pk),
                "actividad_nombre": actividad.nombre,
                "total": str(total_fila),
                "total_formato": format_cop(total_fila),
                "cantidad": int(money_row.get("cantidad") or 0),
                "familias_asignadas": asign,
                "familias_pagaron": pagaron,
                "familias_pendientes": max(asign - pagaron, 0),
            }
        )

    personas_count = (
        ActividadPersona.objects.filter(
            actividad_id__in=[a.id for a in generales]
        ).count()
        if generales
        else 0
    )
    asignadas_total = len(participantes) + personas_count
    familias_con_pendiente = {
        item.get("familia_id") or item.get("persona_id") for item in pendientes_list
    }
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
