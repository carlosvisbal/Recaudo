from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("padrinos", views.PadrinoViewSet, basename="padrino")
router.register("familias", views.FamiliaViewSet, basename="familia")
router.register("actividades", views.ActividadViewSet, basename="actividad")
router.register("recaudos", views.RecaudoViewSet, basename="recaudo")

urlpatterns = [
    path("auth/csrf/", views.csrf_view),
    path("auth/login/", views.login_view),
    path("auth/logout/", views.logout_view),
    path("auth/me/", views.me_view),
    path("organizacion/", views.organizacion_view),
    path("consultas/exportar/", views.consultas_export),
    path("informes/", views.informes_view),
    path("informes/exportar/", views.consultas_export),
    path("sistema/", views.estado_sistema),
    path(
        "recaudos/<uuid:pk>/soportes/<uuid:soporte_id>/",
        views.descargar_soporte,
    ),
    path("", include(router.urls)),
]
