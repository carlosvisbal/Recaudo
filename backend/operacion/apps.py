import os
import sys

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _en_pruebas() -> bool:
    return "pytest" in sys.modules or "test" in sys.argv


def _seed_tras_migrar(sender, **kwargs):
    if sender.name != "operacion" or _en_pruebas():
        return
    if os.getenv("SKIP_SEED", "").strip().lower() in {"1", "true", "yes", "si", "sí"}:
        return
    from operacion.seed import asegurar_admin_inicial, asegurar_catalogo_inicial

    asegurar_admin_inicial()
    asegurar_catalogo_inicial()


def _configurar_sqlite(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA foreign_keys=ON;")


class OperacionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "operacion"
    verbose_name = "Operación de recaudos"

    def ready(self):
        from django.db.backends.signals import connection_created

        post_migrate.connect(_seed_tras_migrar, sender=self, dispatch_uid="operacion.seed")
        connection_created.connect(_configurar_sqlite, dispatch_uid="operacion.sqlite")
