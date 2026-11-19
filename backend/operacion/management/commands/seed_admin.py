from django.core.management.base import BaseCommand

from operacion.seed import asegurar_admin_inicial, asegurar_catalogo_inicial


class Command(BaseCommand):
    help = "Crea el administrador y el catálogo inicial si aún no existen."

    def handle(self, *args, **options):
        if asegurar_admin_inicial():
            self.stdout.write(self.style.SUCCESS("Administrador 'admin' creado."))
        else:
            self.stdout.write("El administrador ya existía; no se modificó la clave.")
        if asegurar_catalogo_inicial():
            self.stdout.write(self.style.SUCCESS("Catálogo inicial de padrinos/familias cargado."))
        else:
            self.stdout.write("El catálogo inicial ya estaba marcado como sembrado.")
        self.stdout.write("Configuración inicial lista.")
