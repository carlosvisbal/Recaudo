from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path

from operacion.media import servir_media
from operacion.spa import SpaView


def salud(_request):
    return JsonResponse({"estado": "ok", "servicio": "recaudo"})


urlpatterns = [
    path("salud/", salud),
    path("admin/", admin.site.urls),
    path("api/", include("operacion.urls")),
    re_path(r"^media/(?P<path>.*)$", servir_media),
    re_path(r"^(?!api/|admin/|static/|media/|salud/).*$", SpaView.as_view()),
]
