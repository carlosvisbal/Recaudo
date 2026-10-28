from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views import View


class SpaView(View):
    """Sirve el index.html de la PWA para las rutas del frontend."""

    def get(self, request, *args, **kwargs):
        index = Path(settings.BASE_DIR) / "static" / "frontend" / "index.html"
        if not index.exists():
            from django.http import HttpResponse

            return HttpResponse(
                "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<title>Recaudo</title></head><body style='font-family:sans-serif;padding:2rem'>"
                "<h1>Recaudo</h1><p>El frontend aún no está compilado. "
                "En desarrollo ejecute <code>npm run dev</code> en <code>frontend/</code>.</p>"
                "</body></html>",
                content_type="text/html; charset=utf-8",
            )
        return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
