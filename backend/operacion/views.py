from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404, HttpResponse
from django.middleware.csrf import get_token
from django.utils.encoding import smart_str
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .excel import exportar_consultas
from .pagination import ListaPaginada
from .models import (
    Actividad,
    EstadoRecaudo,
    EstadoRegistro,
    Familia,
    Organizacion,
    Padrino,
    Recaudo,
    ResultadoEnvio,
    Soporte,
)
from .serializers import (
    ActividadSerializer,
    AsignacionSerializer,
    EnvioCorreoSerializer,
    FamiliaBusquedaSerializer,
    FamiliaSerializer,
    OrganizacionSerializer,
    PadrinoSerializer,
    RecaudoCreateSerializer,
    RecaudoDetalleSerializer,
    RecaudoListSerializer,
)
from .services import (
    actualizar_recaudo,
    anular_recaudo,
    confirmar_recaudo,
    eliminar_actividad,
    eliminar_familia,
    eliminar_padrino,
    eliminar_recaudo,
    enviar_recibo_por_correo,
    filtrar_recaudos,
    informe,
    payload_compartir,
    reasignar_familia,
    smtp_configurado,
    totales_de,
)
from .money import format_cop


def _user_payload(user):
    return {
        "username": user.get_username(),
        "nombre": user.get_full_name() or user.get_username(),
        "email": user.email,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_view(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def login_view(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return Response(
            {"detail": "Usuario o contraseña incorrectos."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    login(request, user)
    return Response({"usuario": _user_payload(user)})


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response({"ok": True})


@api_view(["GET"])
def me_view(request):
    org = Organizacion.actual()
    return Response(
        {
            "usuario": _user_payload(request.user),
            "organizacion": OrganizacionSerializer(org).data,
            "smtp_configurado": smtp_configurado(),
        }
    )


@api_view(["GET", "PUT"])
def organizacion_view(request):
    org = Organizacion.actual()
    if request.method == "GET":
        return Response(OrganizacionSerializer(org).data)
    serializer = OrganizacionSerializer(org, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


class PadrinoViewSet(viewsets.ModelViewSet):
    serializer_class = PadrinoSerializer
    pagination_class = ListaPaginada
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = Padrino.objects.annotate(
            familias_activas=Count(
                "familias", filter=Q(familias__estado=EstadoRegistro.ACTIVO)
            )
        )
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(nombre_completo__icontains=q)
                | Q(telefono__icontains=q)
                | Q(correo__icontains=q)
            )
        return qs

    def destroy(self, request, *args, **kwargs):
        eliminar_padrino(self.get_object(), request.user, request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        padrino = self.get_object()
        activas = padrino.familias.filter(estado=EstadoRegistro.ACTIVO).count()
        if activas:
            raise ValidationError(
                f"Reasigne o desactive las {activas} familia(s) activa(s) antes de desactivar el padrino."
            )
        padrino.estado = EstadoRegistro.INACTIVO
        padrino.save(update_fields=["estado", "actualizado_en"])
        return Response(self.get_serializer(padrino).data)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        padrino = self.get_object()
        padrino.estado = EstadoRegistro.ACTIVO
        padrino.save(update_fields=["estado", "actualizado_en"])
        return Response(self.get_serializer(padrino).data)


class FamiliaViewSet(viewsets.ModelViewSet):
    serializer_class = FamiliaSerializer
    pagination_class = ListaPaginada
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        eliminar_familia(self.get_object(), request.user, request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        from .models import AsignacionFamiliaHistorial

        familia = serializer.save()
        AsignacionFamiliaHistorial.objects.create(
            familia=familia,
            padrino_anterior=None,
            padrino_nuevo=familia.padrino,
            motivo="Asignación inicial",
            cambiado_por=self.request.user,
        )

    def perform_update(self, serializer):
        familia = self.get_object()
        nuevo = serializer.validated_data.get("padrino")
        if nuevo and nuevo.id != familia.padrino_id:
            motivo = self.request.data.get("motivo") or "Cambio de padrino"
            reasignar_familia(familia, nuevo, self.request.user, motivo, self.request)
            serializer.validated_data.pop("padrino", None)
        serializer.save()

    def get_queryset(self):
        qs = Familia.objects.select_related("padrino")
        estado = self.request.query_params.get("estado")
        padrino = self.request.query_params.get("padrino")
        q = self.request.query_params.get("q") or self.request.query_params.get("search")
        if estado:
            qs = qs.filter(estado=estado)
        if padrino:
            qs = qs.filter(padrino_id=padrino)
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(contacto_principal__icontains=q)
                | Q(telefono__icontains=q)
            )
        return qs

    def get_serializer_class(self):
        if self.action == "buscar":
            return FamiliaBusquedaSerializer
        return FamiliaSerializer

    @action(detail=False, methods=["get"])
    def buscar(self, request):
        q = (request.query_params.get("q") or "").strip()
        qs = self.get_queryset().filter(estado=EstadoRegistro.ACTIVO)
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(contacto_principal__icontains=q)
                | Q(telefono__icontains=q)
            )
        qs = qs.order_by("nombre")[:20]
        return Response(FamiliaBusquedaSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        familia = self.get_object()
        familia.estado = EstadoRegistro.INACTIVO
        familia.save(update_fields=["estado", "actualizado_en"])
        return Response(self.get_serializer(familia).data)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        familia = self.get_object()
        if familia.padrino.estado != EstadoRegistro.ACTIVO:
            raise ValidationError("El padrino asignado está inactivo. Reasigne la familia primero.")
        familia.estado = EstadoRegistro.ACTIVO
        familia.save(update_fields=["estado", "actualizado_en"])
        return Response(self.get_serializer(familia).data)

    @action(detail=True, methods=["post"])
    def reasignar(self, request, pk=None):
        familia = self.get_object()
        padrino_id = request.data.get("padrino")
        motivo = request.data.get("motivo") or ""
        try:
            padrino = Padrino.objects.get(pk=padrino_id, estado=EstadoRegistro.ACTIVO)
        except Padrino.DoesNotExist:
            raise ValidationError("Padrino no encontrado o inactivo.")
        familia = reasignar_familia(familia, padrino, request.user, motivo, request)
        return Response(self.get_serializer(familia).data)

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        familia = self.get_object()
        items = familia.historial_asignaciones.select_related(
            "padrino_anterior", "padrino_nuevo", "cambiado_por"
        )
        return Response(AsignacionSerializer(items, many=True).data)


class ActividadViewSet(viewsets.ModelViewSet):
    serializer_class = ActividadSerializer
    pagination_class = ListaPaginada
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        eliminar_actividad(self.get_object(), request.user, request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        qs = Actividad.objects.annotate(
            total_recaudado=Sum(
                "recaudos__valor",
                filter=Q(recaudos__estado=EstadoRecaudo.CONFIRMADO),
            ),
            cantidad_recaudos=Count(
                "recaudos", filter=Q(recaudos__estado=EstadoRecaudo.CONFIRMADO)
            ),
        )
        estado = self.request.query_params.get("estado")
        q = self.request.query_params.get("q")
        if estado:
            qs = qs.filter(estado=estado)
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
        return qs


class RecaudoViewSet(viewsets.ReadOnlyModelViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = ListaPaginada
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return filtrar_recaudos(self.request.query_params)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RecaudoDetalleSerializer
        return RecaudoListSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        totales = totales_de(qs)
        page = self.paginate_queryset(qs)
        serializer = RecaudoListSerializer(page, many=True)
        payload = self.get_paginated_response(serializer.data)
        payload.data["resultados"] = payload.data["results"]
        payload.data["totales"] = {
            **totales,
            "total_confirmado_formato": format_cop(totales["total_confirmado"]),
        }
        return payload

    def create(self, request, *args, **kwargs):
        serializer = RecaudoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        archivos = request.FILES.getlist("soportes") or request.FILES.getlist("soportes[]")
        recaudo = confirmar_recaudo(
            usuario=request.user,
            data=serializer.validated_data,
            archivos=archivos,
            request=request,
        )
        recaudo = (
            Recaudo.objects.prefetch_related("soportes")
            .select_related("recibo", "familia")
            .get(pk=recaudo.pk)
        )
        return Response(
            RecaudoDetalleSerializer(recaudo).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        recaudo = self.get_object()
        serializer = RecaudoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        archivos = request.FILES.getlist("soportes") or request.FILES.getlist("soportes[]")
        recaudo = actualizar_recaudo(
            recaudo=recaudo,
            usuario=request.user,
            data=serializer.validated_data,
            archivos=archivos,
            request=request,
        )
        recaudo = (
            Recaudo.objects.prefetch_related("soportes")
            .select_related("recibo", "familia")
            .get(pk=recaudo.pk)
        )
        return Response(RecaudoDetalleSerializer(recaudo).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        eliminar_recaudo(self.get_object(), request.user, request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        recaudo = self.get_object()
        recaudo = anular_recaudo(recaudo, request.user, request.data.get("motivo") or "", request)
        recaudo = Recaudo.objects.prefetch_related("soportes").select_related("recibo").get(pk=recaudo.pk)
        return Response(RecaudoDetalleSerializer(recaudo).data)

    @action(detail=True, methods=["get"])
    def compartir(self, request, pk=None):
        recaudo = self.get_object()
        return Response(payload_compartir(recaudo))

    @action(detail=True, methods=["post"], url_path="telefono-familia")
    def telefono_familia(self, request, pk=None):
        recaudo = self.get_object()
        if not recaudo.familia_id:
            raise ValidationError("Este pago no está ligado a una familia. Guarde el celular en la ficha de la familia.")
        telefono = (request.data.get("telefono") or "").strip()
        digits = "".join(ch for ch in telefono if ch.isdigit())
        if len(digits) < 10:
            raise ValidationError("Indique un celular de al menos 10 dígitos.")
        recaudo.familia.telefono = telefono
        recaudo.familia.save(update_fields=["telefono", "actualizado_en"])
        recaudo.refresh_from_db()
        recaudo = Recaudo.objects.select_related("familia", "padrino").get(pk=recaudo.pk)
        return Response(payload_compartir(recaudo))

    @action(detail=True, methods=["post"], url_path="enviar-correo")
    def enviar_correo(self, request, pk=None):
        recaudo = self.get_object()
        envio = enviar_recibo_por_correo(
            recaudo, request.user, request.data.get("destinatario") or "", request
        )
        data = EnvioCorreoSerializer(envio).data
        data["smtp_configurado"] = smtp_configurado()
        data["enviado"] = envio.resultado == ResultadoEnvio.ENVIADO
        return Response(data)

    @action(detail=True, methods=["get"], url_path="recibo")
    def recibo(self, request, pk=None):
        recaudo = self.get_object()
        if not hasattr(recaudo, "recibo"):
            raise Http404("El recibo aún no está disponible.")
        attachment = request.query_params.get("descargar") == "1"
        recaudo.recibo.archivo.open("rb")
        response = FileResponse(
            recaudo.recibo.archivo,
            content_type="application/pdf",
        )
        disposition = "attachment" if attachment else "inline"
        filename = f"recibo-{recaudo.numero_formateado}.pdf"
        response["Content-Disposition"] = f'{disposition}; filename="{smart_str(filename)}"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response

@api_view(["GET"])
def descargar_soporte(request, pk, soporte_id):
    try:
        recaudo = Recaudo.objects.get(pk=pk)
        soporte = recaudo.soportes.get(pk=soporte_id)
    except (Recaudo.DoesNotExist, Soporte.DoesNotExist):
        raise Http404("Soporte no encontrado.")
    soporte.archivo.open("rb")
    response = FileResponse(soporte.archivo, content_type=soporte.content_type)
    response["Content-Disposition"] = (
        f'inline; filename="{smart_str(soporte.nombre_original)}"'
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@api_view(["GET"])
def informes_view(request):
    data = informe(request.query_params)
    data["total_confirmado_formato"] = format_cop(data["total_confirmado"])
    return Response(data)


@api_view(["GET"])
def consultas_export(request):
    qs = filtrar_recaudos(request.query_params)
    data = informe(request.query_params, paginar_pendientes=False)
    content = exportar_consultas(qs[:5000], data)
    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="informes-recaudo.xlsx"'
    return response


@api_view(["GET"])
def estado_sistema(request):
    return Response(
        {
            "smtp_configurado": smtp_configurado(),
            "debug": settings.DEBUG,
            "organizacion": Organizacion.actual().nombre,
        }
    )
