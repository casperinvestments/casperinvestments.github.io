#!/usr/bin/env python3
"""Import public listing photos into assets/img/units/<slug>/.

Usage:
    python3 scripts/import_photos.py <source_dir>

Each subfolder whose name is a unit id in data/units.json contributes up to
five images, in numeric filename order. Images are converted to RGB, resized
so the width is at most 1200px (aspect ratio kept, no upscaling), stripped of
metadata, and saved as progressive JPEG quality 68 with 4:2:0 subsampling:

    assets/img/units/<slug>/01.jpg
    assets/img/units/<slug>/02.jpg
    ...

Unknown folders are skipped with a warning. Same-named numbered files are
overwritten. Nothing is deleted. This script uses Pillow. The site build
does not.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("error: Pillow is required for scripts/import_photos.py")

ROOT = Path(__file__).resolve().parent.parent
UNITS_PATH = ROOT / "data" / "units.json"
DEST_ROOT = ROOT / "assets" / "img" / "units"
MAX_WIDTH = 1200
JPEG_QUALITY = 68
MAX_PHOTOS = 5
SLUG_RE = re.compile(r"[a-z0-9-]+")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}


def load_units():
    try:
        payload = json.loads(UNITS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"error: missing {UNITS_PATH}")
    except json.JSONDecodeError as exc:
        sys.exit(f"error: {UNITS_PATH} is not valid JSON: {exc}")
    if not isinstance(payload, list) or not payload:
        sys.exit("error: data/units.json must be a non-empty list")
    units = []
    seen = set()
    for unit in payload:
        if not isinstance(unit, dict) or "id" not in unit or "slug" not in unit:
            sys.exit("error: every unit needs an id and a slug")
        unit_id = unit["id"]
        slug = unit["slug"]
        if unit_id in seen:
            sys.exit(f"error: duplicate id in units.json: {unit_id}")
        if not SLUG_RE.fullmatch(slug):
            sys.exit(f"error: unsafe slug {slug}")
        seen.add(unit_id)
        units.append(unit)
    return units


def image_sort_key(path):
    match = re.search(r"\d+", path.stem)
    if match:
        return (0, int(match.group()), path.name.lower())
    return (1, 0, path.name.lower())


def list_images(folder):
    files = []
    for path in folder.iterdir():
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        files.append(path)
    files.sort(key=image_sort_key)
    return files[:MAX_PHOTOS]


def to_rgb(image):
    if image.mode == "RGB":
        return image
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def prepare_image(src):
    with Image.open(src) as original:
        oriented = ImageOps.exif_transpose(original)
        rgb = to_rgb(oriented)
        if rgb.width > MAX_WIDTH:
            new_height = max(1, round(rgb.height * MAX_WIDTH / rgb.width))
            rgb = rgb.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
        clean = Image.frombytes("RGB", rgb.size, rgb.tobytes())
    return clean


def save_jpeg(image, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        dest,
        format="JPEG",
        quality=JPEG_QUALITY,
        progressive=True,
        optimize=True,
        subsampling="4:2:0",
    )


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="import_photos.py",
        description="Import unit photos into assets/img/units/<slug>/.",
    )
    parser.add_argument("source_dir", help="Directory whose subfolders are named with unit ids")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    source = Path(args.source_dir)
    if not source.is_dir():
        sys.exit(f"error: source directory not found: {source}")

    units = load_units()
    folders = {}
    for path in sorted(source.iterdir(), key=lambda item: item.name):
        if path.is_dir():
            folders[path.name] = path

    imported_units = 0
    imported_photos = 0
    imported_bytes = 0

    for unit in units:
        folder = folders.pop(unit["id"], None)
        if folder is None:
            continue
        images = list_images(folder)
        if not images:
            print(f"Warning: no images in {folder.name}; skipped")
            continue
        dest_dir = DEST_ROOT / unit["slug"]
        written = 0
        total = 0
        for image_path in images:
            dest = dest_dir / f"{written + 1:02d}.jpg"
            try:
                clean = prepare_image(image_path)
            except Exception as exc:
                print(f"Warning: could not import {image_path.name} for {unit['id']}: {exc}")
                continue
            try:
                save_jpeg(clean, dest)
            except Exception as exc:
                print(f"Warning: could not save {dest.name} for {unit['id']}: {exc}")
                continue
            finally:
                clean.close()
            written += 1
            total += dest.stat().st_size
        if not written:
            print(f"Warning: no photos written for {unit['id']}")
            continue
        imported_units += 1
        imported_photos += written
        imported_bytes += total
        print(f"{unit['id']}: {written} photos, {total / 1024:.1f} KB")

    for name in folders:
        print(f"Warning: skipped unknown folder: {name}")

    print(
        f"Imported {imported_units} units, {imported_photos} photos, {imported_bytes / 1024:.1f} KB"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
