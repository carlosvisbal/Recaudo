from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.views.static import serve


@login_required(login_url="/admin/login/")
def servir_media(request, path: str):
    """Sirve archivos privados (recibos/soportes) solo con sesión autenticada.

    La PWA usa /api/.../recibo y /api/.../soportes. Esta ruta cubre el panel
    /admin/ y cualquier enlace a MEDIA_URL en Railway sin exponer /media público.
    """
    root = Path(settings.MEDIA_ROOT).resolve()
    objetivo = (root / path).resolve()
    if not str(objetivo).startswith(str(root)) or not objetivo.is_file():
        raise Http404("Archivo no encontrado.")
    return serve(request, path, document_root=str(root))
