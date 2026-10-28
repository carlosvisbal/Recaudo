from io import BytesIO

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .money import format_cop

TEAL = HexColor("#0F4C4C")
TEAL_DARK = HexColor("#0A3333")
GOLD = HexColor("#C4A574")
INK = HexColor("#1A2E29")
MUTED = HexColor("#5C6B66")
PAPER = HexColor("#F7F1E6")
LINE = HexColor("#D9CBB3")
DISCLAIMER_BG = HexColor("#F3E7D3")


def _try_fonts() -> tuple[str, str]:
    candidates = [
        ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf", "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    ]
    for regular, bold in candidates:
        try:
            pdfmetrics.registerFont(TTFont("RecaudoSans", regular))
            pdfmetrics.registerFont(TTFont("RecaudoSans-Bold", bold))
            return "RecaudoSans", "RecaudoSans-Bold"
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold"


def _wrap(c: canvas.Canvas, text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if c.stringWidth(trial, font, size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def generar_pdf_recibo(recaudo) -> bytes:
    regular, bold = _try_fonts()
    buffer = BytesIO()
    width, height = letter
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle(f"Recibo de caja {recaudo.numero_formateado}")
    c.setAuthor(recaudo.organizacion_nombre)

    margin = 16 * mm
    c.setFillColor(PAPER)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setFillColor(TEAL)
    c.rect(0, height - 38 * mm, width, 38 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, height - 40 * mm, width, 2.2 * mm, fill=1, stroke=0)

    c.setFillColor(white)
    c.setFont(regular, 9)
    c.drawString(margin, height - 12 * mm, "CONSTANCIA DE RECAUDO")
    c.setFont(bold, 18)
    c.drawString(margin, height - 21 * mm, recaudo.organizacion_nombre)
    c.setFont(regular, 10)
    c.drawString(margin, height - 28 * mm, "Recibo de caja")

    box_x = width - margin - 48 * mm
    c.setFillColor(Color(1, 1, 1, alpha=0.14))
    c.roundRect(box_x, height - 32 * mm, 48 * mm, 20 * mm, 4, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont(regular, 8)
    c.drawRightString(width - margin - 3 * mm, height - 16 * mm, "N.º DE RECIBO")
    c.setFillColor(white)
    c.setFont(bold, 16)
    c.drawRightString(width - margin - 3 * mm, height - 26 * mm, recaudo.numero_formateado)

    y = height - 52 * mm
    c.setFillColor(INK)
    c.setFont(bold, 11)
    c.drawString(margin, y, "Datos del recaudo")
    y -= 4 * mm
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(margin, y, width - margin, y)
    y -= 9 * mm

    fecha = recaudo.fecha.strftime("%d/%m/%Y")
    rows = [
        ("Fecha", fecha),
        ("Actividad", recaudo.actividad_nombre),
        ("Padrino responsable", recaudo.padrino_nombre),
        ("Familia o aportante", recaudo.aportante_nombre),
        ("Medio de pago", recaudo.get_medio_pago_display()),
        ("Concepto", recaudo.concepto or "—"),
        ("Referencia de pago", recaudo.referencia_consignacion or "—"),
    ]
    if recaudo.familia_nombre and recaudo.familia_nombre != recaudo.aportante_nombre:
        rows.insert(4, ("Familia asignada", recaudo.familia_nombre))

    col1 = margin
    col2 = margin + 52 * mm
    for label, value in rows:
        c.setFillColor(MUTED)
        c.setFont(regular, 8.5)
        c.drawString(col1, y, label.upper())
        c.setFillColor(INK)
        c.setFont(bold, 10)
        for i, line in enumerate(_wrap(c, str(value), bold, 10, width - col2 - margin)):
            c.drawString(col2, y - (i * 4.2 * mm), line)
        y -= 9 * mm if len(_wrap(c, str(value), bold, 10, width - col2 - margin)) == 1 else 13 * mm

    y -= 2 * mm
    c.setFillColor(TEAL)
    c.roundRect(margin, y - 22 * mm, width - 2 * margin, 26 * mm, 4, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont(regular, 8)
    c.drawString(margin + 5 * mm, y - 4 * mm, "VALOR RECIBIDO")
    c.setFillColor(white)
    c.setFont(bold, 18)
    c.drawString(margin + 5 * mm, y - 13 * mm, format_cop(recaudo.valor))
    c.setFont(regular, 8.5)
    letras = recaudo.valor_en_letras
    letter_lines = _wrap(c, letras, regular, 8.5, width - 2 * margin - 12 * mm)
    ly = y - 19 * mm
    for line in letter_lines[:2]:
        c.drawString(margin + 5 * mm, ly, line)
        ly -= 3.6 * mm

    y = y - 34 * mm
    soportes = list(recaudo.soportes.all())
    c.setFillColor(INK)
    c.setFont(bold, 11)
    c.drawString(margin, y, "Soportes")
    y -= 6 * mm
    c.setFillColor(MUTED)
    c.setFont(regular, 9)
    if soportes:
        refs = ", ".join(f"{s.nombre_original}" for s in soportes)
        c.drawString(margin, y, f"{len(soportes)} archivo(s) privado(s) adjunto(s) al recaudo.")
        y -= 5 * mm
        for line in _wrap(c, refs, regular, 8.5, width - 2 * margin)[:4]:
            c.drawString(margin, y, line)
            y -= 4 * mm
    else:
        c.drawString(margin, y, "Este recaudo no tiene soportes adjuntos.")
        y -= 6 * mm

    y -= 4 * mm
    c.setFillColor(INK)
    c.setFont(bold, 11)
    c.drawString(margin, y, "Registro")
    y -= 6 * mm
    c.setFillColor(MUTED)
    c.setFont(regular, 9)
    c.drawString(margin, y, f"Registrado por: {recaudo.usuario_nombre}")
    y -= 5 * mm
    creado = recaudo.creado_en.astimezone().strftime("%d/%m/%Y %H:%M")
    c.drawString(margin, y, f"Fecha y hora de registro: {creado}")
    if recaudo.estado == "anulado":
        y -= 8 * mm
        c.setFillColor(HexColor("#9B2C2C"))
        c.setFont(bold, 11)
        c.drawString(margin, y, "RECIBO ANULADO")
        y -= 5 * mm
        c.setFont(regular, 9)
        c.drawString(margin, y, f"Motivo: {recaudo.motivo_anulacion}")

    c.setFillColor(DISCLAIMER_BG)
    c.roundRect(margin, 18 * mm, width - 2 * margin, 22 * mm, 3, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont(bold, 8)
    c.drawString(margin + 4 * mm, 34 * mm, "Aviso")
    c.setFont(regular, 8)
    disclaimer = (
        "Este recibo de caja es una constancia del dinero registrado como recibido. "
        "No constituye un certificado tributario oficial ni un documento de donación "
        "para efectos fiscales. Conserva trazabilidad interna; los números anulados no se reutilizan."
    )
    dy = 29 * mm
    for line in _wrap(c, disclaimer, regular, 8, width - 2 * margin - 8 * mm):
        c.drawString(margin + 4 * mm, dy, line)
        dy -= 3.5 * mm

    c.setFillColor(TEAL_DARK)
    c.rect(0, 0, width, 12 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont(regular, 8)
    c.drawCentredString(width / 2, 5 * mm, "Documento de uso interno · Recaudo")

    if recaudo.estado == "anulado":
        c.saveState()
        c.setFillColor(Color(0.6, 0.15, 0.15, alpha=0.12))
        c.translate(width / 2, height / 2)
        c.rotate(28)
        c.setFont(bold, 48)
        c.setFillColor(Color(0.6, 0.15, 0.15, alpha=0.28))
        c.drawCentredString(0, 0, "ANULADO")
        c.restoreState()

    c.showPage()
    c.save()
    return buffer.getvalue()
