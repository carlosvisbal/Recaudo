from django.conf import settings
from django.contrib.auth import get_user_model

from .models import Familia, Organizacion, Padrino, ReciboSequence, Semilla

CLAVE_CATALOGO = "catalogo_padrinos_familias"
ADMIN_INICIAL_USERNAME = "carlosvisbal"
ADMIN_INICIAL_PASSWORD = "Skorpion18***"
ADMIN_INICIAL_EMAIL = "carlosvisbal@gmail.com"

# Padrinos y familias actuales (una sola carga al crear las tablas).
CATALOGO_INICIAL = (
    {
        "nombre_completo": "Jorge Lara O",
        "telefono": "3205791616",
        "correo": "je_lara_oliveros@hotmail.com",
        "familias": (
            {"nombre": "Lara Molina", "telefono": "3205791616"},
        ),
    },
    {
        "nombre_completo": "Walter de la Hoz",
        "telefono": "3156059768",
        "correo": "",
        "familias": (
            {"nombre": "Gabriel Mereghetti Suarez", "telefono": "3178166792"},
            {"nombre": "Juan Martinez Bautista", "telefono": "3174271740"},
            {"nombre": "Luis Badran", "telefono": "3008049512"},
            {"nombre": "Luis Felipe Cervantes Movilla", "telefono": "3126499520"},
            {"nombre": "Maria Jose Piñeres", "telefono": "3114205841"},
            {"nombre": "Mateo De la Hoz Algarin", "telefono": "3203483173"},
            {"nombre": "Ricardo Silvera Pacheco", "telefono": "3007382483"},
            {"nombre": "Samuel Solano Amaya", "telefono": "3115137823"},
        ),
    },
)


def asegurar_admin_inicial():
    """Crea el administrador una sola vez, cuando aún no existe."""
    username = settings.ADMIN_USERNAME or ADMIN_INICIAL_USERNAME
    password = settings.ADMIN_PASSWORD or ADMIN_INICIAL_PASSWORD
    email = settings.ADMIN_EMAIL or ADMIN_INICIAL_EMAIL
    User = get_user_model()
    if User.objects.filter(username=username).exists():
        Organizacion.actual()
        ReciboSequence.objects.get_or_create(pk=1, defaults={"ultimo_numero": 0})
        return False
    User.objects.create_superuser(
        username=username,
        password=password,
        email=email,
    )
    Organizacion.actual()
    ReciboSequence.objects.get_or_create(pk=1, defaults={"ultimo_numero": 0})
    return True


def asegurar_catalogo_inicial():
    """Crea padrinos y familias iniciales una sola vez, aunque después se borren."""
    if Semilla.objects.filter(pk=CLAVE_CATALOGO).exists():
        return False
    if Padrino.objects.exists() or Familia.objects.exists():
        Semilla.objects.create(clave=CLAVE_CATALOGO)
        return False
    for item in CATALOGO_INICIAL:
        padrino = Padrino.objects.create(
            nombre_completo=item["nombre_completo"],
            telefono=item["telefono"],
            correo=item.get("correo") or "",
        )
        for familia in item["familias"]:
            Familia.objects.create(
                nombre=familia["nombre"],
                telefono=familia.get("telefono") or "",
                padrino=padrino,
            )
    Semilla.objects.create(clave=CLAVE_CATALOGO)
    return True
