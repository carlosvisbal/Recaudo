import hashlib
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _en_railway() -> bool:
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))


def _host_limpio(valor: str) -> str:
    return valor.strip().split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]


def _agregar_publico(host: str, *, csrf: bool = True) -> None:
    host = _host_limpio(host)
    if not host:
        return
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)
    if not csrf:
        return
    origen = f"https://*{host}" if host.startswith(".") else f"https://{host}"
    if origen not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origen)


_CLAVE_INSEGURA = "inseguro-solo-desarrollo"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", _CLAVE_INSEGURA)
if SECRET_KEY == _CLAVE_INSEGURA and _en_railway():
    _material = f"{os.getenv('RAILWAY_PROJECT_ID', '')}:{os.getenv('RAILWAY_SERVICE_ID', 'recaudo')}"
    SECRET_KEY = hashlib.sha256(f"recaudo-railway-{_material}".encode()).hexdigest()

DEBUG = env_bool("DJANGO_DEBUG", default=not _en_railway())
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173",
)
for _host in (
    ".trycloudflare.com",
    ".cfargotunnel.com",
    ".up.railway.app",
    ".railway.app",
):
    _agregar_publico(_host)
_agregar_publico("healthcheck.railway.app", csrf=False)
_agregar_publico(os.getenv("RAILWAY_PUBLIC_DOMAIN", ""), csrf=True)
_agregar_publico(os.getenv("CLOUDFLARE_PUBLIC_HOST", ""), csrf=True)
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "operacion.apps.OperacionConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]


def _opciones_postgres(host: str, query: str = "") -> dict:
    opciones = {"connect_timeout": 5}
    sslmode = (parse_qs(query).get("sslmode") or [os.getenv("PGSSLMODE", "")])[0]
    if sslmode:
        opciones["sslmode"] = sslmode
    elif host.endswith(".railway.app"):
        opciones["sslmode"] = "require"
    return opciones


def _base_datos():
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        parsed = urlparse(url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or 5432),
            "ATOMIC_REQUESTS": False,
            "CONN_MAX_AGE": 60,
            "OPTIONS": _opciones_postgres(parsed.hostname or "", parsed.query),
        }
    postgres_host = os.getenv("POSTGRES_HOST", "").strip()
    if postgres_host:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "recaudo"),
            "USER": os.getenv("POSTGRES_USER", "recaudo"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": postgres_host,
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "ATOMIC_REQUESTS": False,
            "CONN_MAX_AGE": 60,
            "OPTIONS": _opciones_postgres(postgres_host),
        }
    volume = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").rstrip("/")
    sqlite_path = os.getenv("SQLITE_PATH") or (
        f"{volume}/db.sqlite3" if volume else str(BASE_DIR / "db.sqlite3")
    )
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": sqlite_path,
        "OPTIONS": {"timeout": 20},
    }


DATABASES = {"default": _base_datos()}
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = os.getenv("TZ", "America/Bogota")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []
frontend_dist = BASE_DIR / "static" / "frontend"
if frontend_dist.exists():
    STATICFILES_DIRS.append(frontend_dist)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "/media/"
_volume = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").rstrip("/")
MEDIA_ROOT = Path(
    os.getenv("MEDIA_ROOT")
    or (f"{_volume}/media" if _volume else BASE_DIR / "media")
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_AGE = 60 * 60 * 12
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    CORS_ALLOW_CREDENTIALS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "operacion.pagination.ListaPaginada",
    "PAGE_SIZE": 20,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DATE_FORMAT": "%Y-%m-%d",
}

EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587") or "587")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@localhost")
EMAIL_TIMEOUT = 20

ORGANIZATION_NAME = os.getenv("ORGANIZATION_NAME", "Organización de Recaudos")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Skorpion18***")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@localhost")

MAX_SOPORTE_BYTES = 8 * 1024 * 1024
MAX_SOPORTES_POR_RECAUDO = 8

WHITENOISE_ROOT = BASE_DIR / "static" / "frontend" if (BASE_DIR / "static" / "frontend" / "index.html").exists() else None
