from django.core.management.base import BaseCommand

from operacion.seed import asegurar_admin_inicial


class Command(BaseCommand):
    help = "Crea el usuario administrador si las tablas ya existen y aún no hay admin."

    def handle(self, *args, **options):
        creado = asegurar_admin_inicial()
        if creado:
            self.stdout.write(self.style.SUCCESS("Administrador 'admin' creado."))
        else:
            self.stdout.write("El administrador ya existía; no se modificó la clave.")
        self.stdout.write("Configuración inicial lista.")
