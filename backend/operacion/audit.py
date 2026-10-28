from .models import Auditoria


def client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def registrar(usuario, accion: str, entidad: str, entidad_id, payload=None, request=None) -> Auditoria:
    return Auditoria.objects.create(
        usuario=usuario,
        accion=accion,
        entidad=entidad,
        entidad_id=str(entidad_id),
        payload=payload or {},
        ip=client_ip(request),
    )
