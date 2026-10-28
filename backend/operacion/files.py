from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import ValidationError

ALLOWED_SIGNATURES = (
    (b"%PDF", "application/pdf", ".pdf"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
)


def _detect(header: bytes) -> tuple[str, str] | None:
    for magic, content_type, ext in ALLOWED_SIGNATURES:
        if header.startswith(magic):
            return content_type, ext
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def validate_soporte(uploaded) -> tuple[str, str, int]:
    size = getattr(uploaded, "size", 0) or 0
    if size <= 0:
        raise ValidationError("El archivo de soporte está vacío.")
    if size > settings.MAX_SOPORTE_BYTES:
        raise ValidationError("Cada soporte puede pesar como máximo 5 MB.")
    position = uploaded.tell() if hasattr(uploaded, "tell") else 0
    header = uploaded.read(16)
    if hasattr(uploaded, "seek"):
        uploaded.seek(position)
    detected = _detect(header)
    if not detected:
        raise ValidationError(
            "Solo se aceptan PDF, JPEG, PNG o WebP como soportes de recaudo."
        )
    content_type, ext = detected
    name = Path(getattr(uploaded, "name", "") or "soporte").name
    if len(name) > 200:
        name = name[-200:]
    if not name.lower().endswith(ext) and not (
        ext == ".jpg" and name.lower().endswith(".jpeg")
    ):
        name = f"{name}{ext}"
    return name, content_type, size
