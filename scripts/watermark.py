"""
Marca de agua automática para las fotos subidas por el panel /admin.
Se ejecuta desde GitHub Actions cada vez que se sube una foto nueva a images/uploads.

Cómo evita re-marcar la misma foto dos veces: guarda un manifiesto
(images/uploads/.watermarked.json) con el hash de cada archivo YA marcado.
Si una foto nueva tiene un hash distinto al guardado, se marca; si no, se ignora.
"""
import os
import json
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageOps

UPLOADS_DIR = "images/uploads"
MANIFEST_PATH = os.path.join(UPLOADS_DIR, ".watermarked.json")
WATERMARK_TEXT = "GUERRA & GUZMÁN PROPGEST"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
VALID_EXT = (".jpg", ".jpeg", ".png", ".webp")
OPACITY = 55          # 0-255. Más bajo = más sutil.
ROTATION_DEG = -30


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True, ensure_ascii=False)


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def make_tile(text, font_size):
    font = ImageFont.truetype(FONT_PATH, font_size)
    dummy = Image.new("RGBA", (10, 10))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = int(tw * 0.05), int(th * 0.5)
    tile_w, tile_h = tw + pad_x, th + pad_y

    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    draw.text(
        ((tile_w - tw) / 2 - bbox[0], (tile_h - th) / 2 - bbox[1]),
        text, font=font, fill=(255, 255, 255, OPACITY),
        stroke_width=max(1, font_size // 22), stroke_fill=(0, 0, 0, int(OPACITY * 0.6)),
    )
    return tile.rotate(ROTATION_DEG, expand=True)


def watermark_image(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # corrige la rotación de fotos de celular
    img = img.convert("RGBA")
    w, h = img.size

    font_size = max(14, w // 55)
    tile = make_tile(WATERMARK_TEXT, font_size)
    tw, th = tile.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    row = 0
    for y in range(-th, h + th, th):
        offset = (tw // 2) if (row % 2) else 0
        for x in range(-tw - offset, w + tw, tw):
            overlay.alpha_composite(tile, (x, y))
        row += 1

    result = Image.alpha_composite(img, overlay)

    if path.lower().endswith((".jpg", ".jpeg")):
        result.convert("RGB").save(path, quality=90)
    else:
        result.save(path)


def main():
    if not os.path.isdir(UPLOADS_DIR):
        print("No existe la carpeta images/uploads todavía, nada que hacer.")
        return

    manifest = load_manifest()
    changed = False

    for fname in sorted(os.listdir(UPLOADS_DIR)):
        if not fname.lower().endswith(VALID_EXT):
            continue
        path = os.path.join(UPLOADS_DIR, fname)
        current_hash = file_hash(path)
        if manifest.get(fname) == current_hash:
            continue  # ya estaba marcada y no ha cambiado

        watermark_image(path)
        manifest[fname] = file_hash(path)  # hash DESPUÉS de marcar
        changed = True
        print(f"Marcada: {fname}")

    if changed:
        save_manifest(manifest)
    else:
        print("No hay fotos nuevas por marcar.")


if __name__ == "__main__":
    main()
