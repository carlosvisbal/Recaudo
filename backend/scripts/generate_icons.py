#!/usr/bin/env python
"""Icono PWA de Recaudo: marca R.CO sobre recibo azul."""
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont


AZUL = (27, 132, 255)
AZUL_OSCURO = (5, 110, 233)
AZUL_CLARO = (91, 168, 255)
BLANCO = (255, 255, 255)
DORADO = (246, 177, 0)
def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), AZUL)
    px = img.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        color = tuple(
            int(AZUL_CLARO[i] + (AZUL_OSCURO[i] - AZUL_CLARO[i]) * t) for i in range(3)
        )
        for x in range(size):
            px[x, y] = color
    return img


def _centered(draw: ImageDraw.ImageDraw, text: str, font, y: float, fill, width: int) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (width - tw) / 2 - bbox[0]
    draw.text((x, y - bbox[1]), text, fill=fill, font=font)


def draw_icon(size: int, *, maskable: bool = False) -> Image.Image:
    master = 1024
    canvas = _gradient(master)
    overlay = Image.new("RGBA", (master, master), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    safe = 0.22 if maskable else 0.11
    pad = master * safe
    inner = master - pad * 2
    paper = [
        pad + inner * 0.08,
        pad + inner * 0.08,
        master - pad - inner * 0.08,
        master - pad - inner * 0.08,
    ]
    radius = inner * 0.12

    shadow = Image.new("RGBA", (master, master), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [paper[0] + master * 0.02, paper[1] + master * 0.03, paper[2] + master * 0.02, paper[3] + master * 0.03],
        radius=radius,
        fill=(7, 20, 55, 55),
    )
    overlay = Image.alpha_composite(overlay, shadow.filter(ImageFilter.GaussianBlur(master * 0.018)))
    draw = ImageDraw.Draw(overlay)

    draw.rounded_rectangle(paper, radius=radius, fill=(*BLANCO, 255))

    r_font = _font(int(inner * 0.48))
    co_font = _font(int(inner * 0.18))
    r_bbox = draw.textbbox((0, 0), "R", font=r_font)
    co_bbox = draw.textbbox((0, 0), ".CO", font=co_font)
    r_h = r_bbox[3] - r_bbox[1]
    co_h = co_bbox[3] - co_bbox[1]
    gap = inner * 0.02
    block_h = r_h + gap + co_h
    paper_h = paper[3] - paper[1]
    start_y = paper[1] + (paper_h - block_h) / 2

    _centered(draw, "R", r_font, start_y, (*AZUL, 255), master)
    _centered(draw, ".CO", co_font, start_y + r_h + gap, (*DORADO, 255), master)

    composed = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    return composed.resize((size, size), Image.Resampling.LANCZOS).convert("RGB")


def main(out_dir: str) -> None:
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    public = dest.parent if dest.name == "icons" else dest

    assets = [
        (192, dest / "icon-192.png", False),
        (512, dest / "icon-512.png", False),
        (512, dest / "icon-512-maskable.png", True),
        (180, dest / "apple-touch-icon.png", False),
        (180, public / "apple-touch-icon.png", False),
        (32, public / "favicon-32.png", False),
        (48, dest / "icon-48.png", False),
    ]
    for size, path, maskable in assets:
        draw_icon(size, maskable=maskable).save(path, "PNG", optimize=True)

    draw_icon(64).save(public / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main(str(Path(__file__).resolve().parents[2] / "frontend" / "public" / "icons"))
