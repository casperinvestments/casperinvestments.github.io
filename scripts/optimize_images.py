#!/usr/bin/env python3
"""Write responsive image derivatives and favicon PNGs.

For each source JPEG in assets/img/units/<slug>/*.jpg, write:

    assets/img/units/<slug>/opt/NN-400.webp
    assets/img/units/<slug>/opt/NN-400.jpg
    assets/img/units/<slug>/opt/NN-800.webp
    assets/img/units/<slug>/opt/NN-800.jpg
    assets/img/units/<slug>/opt/NN-1200.webp
    assets/img/units/<slug>/opt/NN-1200.jpg

Widths are 400, 800, and a large size named 1200. Images are never
upscaled. If a source is wider than 1600 pixels, the large size is 1600.
Aspect ratio is kept. A derivative newer than its source is left in place.

Also writes assets/img/manifest.json and draws the favicon PNGs
(assets/img/apple-touch-icon.png at 180px and assets/img/favicon-32.png
at 32px). Source JPEGs are never overwritten or deleted. This script uses
Pillow. scripts/build.py does not.
"""

import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    sys.exit("error: Pillow is required for scripts/optimize_images.py")

ROOT = Path(__file__).resolve().parent.parent
UNITS_ROOT = ROOT / "assets" / "img" / "units"
MANIFEST_PATH = ROOT / "assets" / "img" / "manifest.json"
FAVICON_32 = ROOT / "assets" / "img" / "favicon-32.png"
APPLE_TOUCH = ROOT / "assets" / "img" / "apple-touch-icon.png"
SLOTS = (400, 800, 1200)
LARGE_CAP = 1600
WEBP_QUALITY = 72
JPEG_QUALITY = 72
TEAL = (11, 79, 92, 255)
CORAL = (255, 107, 61, 255)


def to_rgb(image):
    if image.mode == "RGB":
        return image
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def strip_metadata(image):
    rgb = image if image.mode == "RGB" else image.convert("RGB")
    return Image.frombytes("RGB", rgb.size, rgb.tobytes())


def target_width(src_width, slot):
    if slot == 1200 and src_width > LARGE_CAP:
        return LARGE_CAP
    return min(src_width, slot)


def scaled_size(src_width, src_height, slot):
    width = target_width(src_width, slot)
    if width == src_width:
        return src_width, src_height
    height = max(1, round(src_height * width / src_width))
    return width, height


def fresh(src, dest):
    return dest.is_file() and dest.stat().st_mtime >= src.stat().st_mtime


def save_variant(image, dest, ext):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if ext == "webp":
        image.save(dest, format="WEBP", quality=WEBP_QUALITY, method=6)
        return
    image.save(
        dest,
        format="JPEG",
        quality=JPEG_QUALITY,
        progressive=True,
        optimize=True,
        subsampling="4:2:0",
    )


def source_jpegs():
    if not UNITS_ROOT.is_dir():
        return []
    files = []
    for folder in sorted(UNITS_ROOT.iterdir(), key=lambda item: item.name):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        for path in sorted(folder.glob("*.jpg"), key=lambda item: item.name):
            if path.is_file() and not path.name.startswith("."):
                files.append(path)
    return files


def rel_path(path):
    return path.relative_to(ROOT).as_posix()


def process_source(src):
    with Image.open(src) as original:
        oriented = ImageOps.exif_transpose(original)
        rgb = strip_metadata(to_rgb(oriented))
    src_width, src_height = rgb.size
    sizes = {slot: scaled_size(src_width, src_height, slot) for slot in SLOTS}
    opt_dir = src.parent / "opt"
    stale = []
    for slot in SLOTS:
        for ext in ("jpg", "webp"):
            dest = opt_dir / f"{src.stem}-{slot}.{ext}"
            if not fresh(src, dest):
                stale.append((slot, ext, dest))
    wrote = 0
    if stale:
        opt_dir.mkdir(parents=True, exist_ok=True)
        cache = {}
        try:
            for slot, ext, dest in stale:
                size = sizes[slot]
                if size not in cache:
                    if size == (src_width, src_height):
                        frame = rgb
                    else:
                        frame = rgb.resize(size, Image.Resampling.LANCZOS)
                    cache[size] = strip_metadata(frame)
                save_variant(cache[size], dest, ext)
                wrote += 1
        finally:
            for frame in cache.values():
                if frame is not rgb:
                    frame.close()
    rgb.close()
    variants = {}
    for slot in SLOTS:
        width, height = sizes[slot]
        variants[str(slot)] = {
            "jpg": rel_path(opt_dir / f"{src.stem}-{slot}.jpg"),
            "webp": rel_path(opt_dir / f"{src.stem}-{slot}.webp"),
            "width": width,
            "height": height,
        }
    entry = {"width": src_width, "height": src_height, "variants": variants}
    return entry, wrote, len(stale) == 0


def draw_mark(size):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = max(2, round(size * 7 / 32))
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=TEAL)
    scale = size / 32.0

    def xy(x, y):
        return (x * scale, y * scale)

    house = [
        xy(16, 6.5),
        xy(27, 15.5),
        xy(23.4, 15.5),
        xy(23.4, 25.2),
        xy(8.6, 25.2),
        xy(8.6, 15.5),
        xy(5, 15.5),
    ]
    draw.polygon(house, fill=CORAL)
    draw.rectangle([xy(13.6, 18.4), xy(18.4, 25.2)], fill=TEAL)
    return image


def write_favicons():
    for path, size in ((FAVICON_32, 32), (APPLE_TOUCH, 180)):
        mark = draw_mark(size)
        path.parent.mkdir(parents=True, exist_ok=True)
        mark.save(path, format="PNG", optimize=True)
        mark.close()


def main():
    manifest = {}
    written = 0
    skipped = 0
    for src in source_jpegs():
        entry, count, was_fresh = process_source(src)
        manifest[rel_path(src)] = entry
        written += count
        if was_fresh:
            skipped += 1
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    MANIFEST_PATH.write_text(payload, encoding="utf-8")
    write_favicons()
    print(
        f"Optimized {len(manifest)} source photos "
        f"({skipped} already current, {written} derivative files written)"
    )
    print(f"Wrote {MANIFEST_PATH.relative_to(ROOT).as_posix()}")
    print("Wrote assets/img/favicon-32.png and assets/img/apple-touch-icon.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
