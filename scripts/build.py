#!/usr/bin/env python3
"""Generate the Casper Rentals static site into the repository root.

Overwrites only the generated pages, sitemap, robots.txt, and .nojekyll.
Does not delete or copy anything else. assets/ and data/ stay where they are.

Uses the Python standard library only. If assets/img/manifest.json is missing,
photo tags fall back to the original JPEGs.
"""

import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
COMMERCIAL_IDS = {"GW-SA", "GW-SB", "GW-SC"}
FURNISHED_IDS = {
    "GW-1",
    "GW-2",
    "CH-4023-3",
    "CH-4023-4",
    "CH-428-3",
    "AU-A",
    "AU-B",
    "AU-C",
    "AU-D",
    "AU-E",
    "AU-1",
    "AU-4",
    "AU-6",
}
FURNISHED_LINE = "Furnished. Weekly and monthly stays available - contact us."
DEFAULT_OG = "assets/img/units/aurora-a/01.jpg"
SITE_ICON = "assets/img/apple-touch-icon.png"
SITE_ICON_ALT = "Casper Rentals logo"
HERO_SLUG = "aurora-a"
CREW_BAND_SLUG = "champions-428-3"
CREW_HERO_SLUGS = ("champions-4023-4", "aurora-b")
PLACEHOLDER = "assets/img/placeholder.svg"
PLACEHOLDER_SIZE = (800, 500)
CREW_FOOTNOTE = (
    "Casper Rentals is an independent local rental company and is not affiliated "
    "with any employer or project named on this page."
)
AFFILIATION_NOTE = (
    "Casper Rentals is an independent local company and is not affiliated with SpaceX "
    "or any employer or project named on this site."
)
PORT_HEADING = "Near the Port of Brownsville"
PORT_PARAGRAPHS = (
    "Port and industry workers can stay in Brownsville, a short drive from the Port of Brownsville.",
    "Rio Grande LNG is under construction on the Brownsville Ship Channel, and the Texas LNG export terminal is planned at the port.",
    "Saronic broke ground in September 2026 on Port Alpha, a shipyard at the Port of Brownsville planned to build autonomous (drone) and crewed ships.",
)
BUSINESS_DESCRIPTION = (
    "Casper Rentals offers furnished apartments and townhouses in Brownsville, Texas, "
    "for weekly and monthly stays, along with small commercial suites. "
    "Contact us about availability."
)
HOME_TITLE = "Furnished & Monthly Rentals in Brownsville, TX | Casper Rentals"
HOME_DESCRIPTION = "Furnished apartments, Champion Dr townhouses & suites in Brownsville, TX for crews near the City of Starbase, TX, Port of Brownsville LNG & shipyard work."
UNITS_TITLE = "Brownsville TX Rentals: Apartments, Townhouses & Suites | Casper Rentals"
UNITS_DESCRIPTION = (
    "Apartments, Champion Dr townhouses, and small commercial suites in Brownsville, TX. "
    "See photos and availability, then contact us about a stay."
)
CREWS_TITLE = "Crew Housing in Brownsville near Starbase, LNG & Wind | Casper Rentals"
CREWS_DESCRIPTION = "Weekly & monthly crew housing in Brownsville, TX near the City of Starbase, TX, Port of Brownsville LNG, the Port Alpha shipyard & wind work. Contact us."
CONTACT_TITLE = "Contact Casper Rentals | Brownsville, TX Rentals"
CONTACT_DESCRIPTION = (
    "Contact Casper Rentals about a furnished apartment, Champion Dr townhouse, or small "
    "commercial suite in Brownsville, TX, including a weekly or monthly stay."
)
NOT_FOUND_TITLE = "Page Not Found | Casper Rentals"
NOT_FOUND_DESCRIPTION = (
    "This page is not on the Casper Rentals site. Browse apartments, townhouses, and small "
    "commercial suites in Brownsville, TX, or contact us about a stay."
)
UNIT_FIELDS = (
    "id",
    "slug",
    "name",
    "property",
    "address",
    "locality",
    "region",
    "country",
    "airbnbName",
    "description",
)
CONTENT_FIELDS = (
    "shortName",
    "kind",
    "about",
    "highlights",
    "photoRooms",
    "metaDescription",
    "location",
)
ALLOWED_KINDS = {"furnished apartment", "furnished townhouse", "small commercial suite"}
KIND_TITLE = {
    "furnished apartment": "Furnished Apartment",
    "furnished townhouse": "Furnished Townhouse",
    "small commercial suite": "Small Commercial Suite",
}
GROUP_LABELS = {
    "4 Greenway Dr": "4 Greenway Dr",
    "Champions": "Champions",
    "Aurora": "Aurora at Paredes Line Rd",
}
AT_ROOMS = {
    "pool",
    "spa pool",
    "pond view",
    "building exterior",
    "exterior stairs",
    "exterior stairs of the building",
    "entry balcony",
}
ORDINALS = {2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth"}
IMAGE_SIZES = {
    "card": "(max-width: 700px) 100vw, 400px",
    "thumb": "(max-width: 700px) 22vw, 120px",
    "main": "(max-width: 900px) 100vw, 60vw",
    "hero": "100vw",
    "band": "(max-width: 860px) 100vw, 45vw",
}
IMAGE_SLOT = {
    "card": "800",
    "thumb": "400",
    "main": "1200",
    "hero": "1200",
    "band": "1200",
}
SLUG_RE = re.compile(r"[a-z0-9-]+")
SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
}
NAV = (
    ("home", "Home", "index.html"),
    ("units", "Units", "units.html"),
    ("crews", "Working Crews", "working-crews.html"),
    ("contact", "Contact", "contact.html"),
)
SECTION_META = {
    "4 Greenway Dr": {
        "anchor": "greenway",
        "title": "4 Greenway Dr",
        "intro": "Apartments and small commercial suites at 4 Greenway Dr in Brownsville, Texas.",
    },
    "Champions": {
        "anchor": "champion-dr",
        "title": "Champion Dr",
        "intro": "Townhouses on Champion Dr in Brownsville, Texas.",
    },
    "Aurora": {
        "anchor": "aurora",
        "title": "Aurora at Paredes Line Rd",
        "intro": "Rental units at Aurora on Paredes Line Rd in Brownsville, Texas.",
    },
}
CREW_SECTIONS = (
    (
        "Port of Brownsville LNG projects",
        (
            "Port of Brownsville LNG projects bring seasonal and contract workers to Brownsville, TX for the length of an assignment.",
            "A furnished apartment or townhouse works as a weekly or monthly stay, so a crew has a place in town while the job is underway.",
            "Tell us the dates and how many people need a place.",
        ),
    ),
    (
        "Wind industry and turbine techs",
        (
            "Wind turbine technicians and other wind industry crews often need a furnished place for weeks or months at a time.",
            "Weekly and monthly stays at Casper Rentals fit that kind of contract work.",
            "If several techs are in town together, ask about a crew or group stay.",
        ),
    ),
    (
        "Near the City of Starbase, TX",
        (
            "Contract workers with jobs in the City of Starbase, TX, at Boca Chica can take a furnished weekly or monthly stay in Brownsville, TX.",
            "These rentals are a short drive from that area.",
            "Casper Rentals is a local company with apartments and townhouses for working crews.",
        ),
    ),
    (
        "Weekly and monthly stays",
        (
            "Every home on this page is a furnished apartment or townhouse.",
            "Weekly and monthly stays are available.",
            "Contact us about your dates and we will confirm what is open. Rent is shared when you contact us.",
        ),
    ),
    (
        "Crew and group stays",
        (
            "A crew or group stay can be one furnished unit, or several units for the same dates.",
            "Send the number of people, the dates you need, and whether you want a weekly or monthly stay.",
        ),
    ),
)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"error: missing {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"error: {path} is not valid JSON: {exc}")


def esc(value):
    return html.escape(str(value), quote=True)


def pretty_date(iso):
    year, month, day = iso.split("-")
    return f"{MONTHS[int(month) - 1]} {int(day)}, {year}"


def status_view(status):
    if status == "Available":
        return "Available", "badge-available"
    if isinstance(status, str) and status.startswith("Available from "):
        iso = status[len("Available from ") :]
        parts = iso.split("-")
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            return f"Available from {pretty_date(iso)}", "badge-soon"
    if status == "Occupied":
        return "Occupied", "badge-occupied"
    return "Contact us for availability", "badge-contact"


def expected_kind(unit_id):
    if unit_id in COMMERCIAL_IDS:
        return "small commercial suite"
    if unit_id.startswith("CH-"):
        return "furnished townhouse"
    return "furnished apartment"


def schema_type(unit):
    if unit["id"] in COMMERCIAL_IDS:
        return "Place"
    if unit["id"].startswith("CH-"):
        return "House"
    return "Apartment"


def jpeg_size(path):
    """Read JPEG width and height from an SOF marker. Fallback is 1200x900."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return 1200, 900
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return 1200, 900
    index = 2
    length = len(data)
    while index + 3 < length:
        if data[index] != 0xFF:
            index += 1
            continue
        while index < length and data[index] == 0xFF:
            index += 1
        if index >= length:
            break
        marker = data[index]
        index += 1
        if marker in (0xD8, 0xD9) or marker == 0xDA:
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        if index + 1 >= length:
            break
        segment = int.from_bytes(data[index : index + 2], "big")
        if segment < 2 or index + segment > length:
            break
        if marker in SOF_MARKERS and segment >= 7:
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            if width > 0 and height > 0:
                return width, height
            break
        index += segment
    return 1200, 900


def load_manifest():
    path = ROOT / "assets" / "img" / "manifest.json"
    if not path.is_file():
        print("Warning: assets/img/manifest.json is missing; using original JPEGs")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Warning: ignoring unreadable manifest ({exc}); using original JPEGs")
        return {}
    if not isinstance(payload, dict):
        print("Warning: manifest is not an object; using original JPEGs")
        return {}
    return payload


def usable_manifest_entry(manifest, source_rel):
    entry = manifest.get(source_rel)
    if not isinstance(entry, dict):
        return None
    variants = entry.get("variants")
    if not isinstance(variants, dict):
        return None
    for slot in ("400", "800", "1200"):
        info = variants.get(slot)
        if not isinstance(info, dict):
            return None
        try:
            width = int(info.get("width"))
            height = int(info.get("height"))
        except (TypeError, ValueError):
            return None
        if width < 1 or height < 1:
            return None
        for key in ("jpg", "webp"):
            variant_path = info.get(key)
            if not isinstance(variant_path, str) or not (ROOT / variant_path).is_file():
                return None
    try:
        int(entry.get("width"))
        int(entry.get("height"))
    except (TypeError, ValueError):
        return None
    return entry


def unit_photo_paths(slug):
    folder = ROOT / "assets" / "img" / "units" / slug
    if not folder.is_dir():
        return []
    names = sorted(
        path.name
        for path in folder.glob("*.jpg")
        if path.is_file() and not path.name.startswith(".")
    )
    return [f"assets/img/units/{slug}/{name}" for name in names]


def photo_records(slug, manifest):
    records = []
    for path in unit_photo_paths(slug):
        entry = usable_manifest_entry(manifest, path)
        if entry:
            width, height = int(entry["width"]), int(entry["height"])
        else:
            width, height = jpeg_size(ROOT / path)
        records.append({"src": path, "entry": entry, "width": width, "height": height})
    return records


def placeholder_record():
    return {"src": PLACEHOLDER, "entry": None, "width": PLACEHOLDER_SIZE[0], "height": PLACEHOLDER_SIZE[1]}


def rel(depth, path):
    return ("../" * depth) + path


def absolute_url(base, path):
    root = base.rstrip("/")
    if path in ("", "/"):
        return root + "/"
    return root + "/" + path.lstrip("/")


def business_id(config):
    return config["baseUrl"].rstrip("/") + "/#business"


def share_image_path(path):
    if path and str(path).endswith((".jpg", ".png")) and (ROOT / path).is_file():
        return path
    if (ROOT / DEFAULT_OG).is_file():
        return DEFAULT_OG
    return PLACEHOLDER


def json_ld(payload):
    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    return raw.replace("<", "\\u003c")


def json_ld_scripts(structured):
    if not structured:
        return ""
    parts = []
    for block in structured:
        parts.append("<script type=\"application/ld+json\">\n" + json_ld(block) + "\n</script>")
    return "\n" + "\n".join(parts)


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def validate_units(units):
    if not isinstance(units, list) or not units:
        sys.exit("error: data/units.json must be a non-empty list")
    seen_ids = set()
    seen_slugs = set()
    for unit in units:
        if not isinstance(unit, dict):
            sys.exit("error: each unit must be an object")
        missing = [field for field in UNIT_FIELDS if field not in unit]
        if missing:
            sys.exit(f"error: unit missing fields {missing}")
        unit_id = unit["id"]
        slug = unit["slug"]
        if unit_id in seen_ids:
            sys.exit(f"error: duplicate unit id {unit_id}")
        if slug in seen_slugs:
            sys.exit(f"error: duplicate slug {slug}")
        if not SLUG_RE.fullmatch(slug):
            sys.exit(f"error: unsafe slug {slug}")
        seen_ids.add(unit_id)
        seen_slugs.add(slug)
    missing_furnished = FURNISHED_IDS - seen_ids
    if missing_furnished:
        sys.exit(f"error: furnished ids missing from units.json: {sorted(missing_furnished)}")
    overlap = FURNISHED_IDS & COMMERCIAL_IDS
    if overlap:
        sys.exit(f"error: commercial suites cannot be marked furnished: {sorted(overlap)}")
    return seen_ids


def load_unit_content(units):
    path = ROOT / "data" / "unit_content.json"
    payload = load_json(path)
    if not isinstance(payload, dict):
        sys.exit("error: data/unit_content.json must be an object keyed by unit id")
    short_names = {}
    for unit in units:
        entry = payload.get(unit["id"])
        if not isinstance(entry, dict):
            sys.exit(f"error: data/unit_content.json missing {unit['id']}")
        missing = [field for field in CONTENT_FIELDS if field not in entry]
        if missing:
            sys.exit(f"error: {unit['id']} content missing {missing}")
        kind = entry["kind"]
        if kind not in ALLOWED_KINDS:
            sys.exit(f"error: {unit['id']} has unknown kind {kind!r}")
        wanted = expected_kind(unit["id"])
        if kind != wanted:
            sys.exit(f"error: {unit['id']} kind must be {wanted!r}")
        if unit["id"] in FURNISHED_IDS and kind == "small commercial suite":
            sys.exit(f"error: {unit['id']} cannot be a commercial suite")
        if unit["id"] in COMMERCIAL_IDS and kind != "small commercial suite":
            sys.exit(f"error: {unit['id']} must stay a small commercial suite")
        for text_key in ("shortName", "about", "metaDescription", "location"):
            if not isinstance(entry[text_key], str) or not entry[text_key].strip():
                sys.exit(f"error: {unit['id']} {text_key} must be text")
        highlights = entry["highlights"]
        rooms = entry["photoRooms"]
        if not isinstance(highlights, list) or not 2 <= len(highlights) <= 4:
            sys.exit(f"error: {unit['id']} highlights must be 2 to 4 strings")
        if not isinstance(rooms, list):
            sys.exit(f"error: {unit['id']} photoRooms must be a list")
        if any(not isinstance(item, str) or not item.strip() for item in highlights + rooms):
            sys.exit(f"error: {unit['id']} highlights and photoRooms must be non-empty strings")
        photos = unit_photo_paths(unit["slug"])
        if len(rooms) != len(photos):
            sys.exit(
                f"error: {unit['id']} photoRooms ({len(rooms)}) "
                f"does not match photo files ({len(photos)})"
            )
        if entry["shortName"] in short_names:
            sys.exit(f"error: duplicate shortName {entry['shortName']}")
        short_names[entry["shortName"]] = unit["id"]
    return payload


def availability_for(availability, unit_id):
    units = availability.get("units", {})
    info = units.get(unit_id)
    if not isinstance(info, dict) or "status" not in info:
        print(f"Warning: no availability for {unit_id}; using Contact us")
        return {"status": "Contact us", "nextOpenDate": None}
    next_open = info.get("nextOpenDate")
    return {"status": info["status"], "nextOpenDate": next_open}


def badge_html(unit_id, status):
    label, kind = status_view(status)
    return f'<span class="badge {kind}" data-unit-status="{esc(unit_id)}">{esc(label)}</span>'


def next_open_html(unit_id, next_open):
    if next_open:
        text = f"Next open date: {pretty_date(next_open)}"
        hidden = ""
    else:
        text = ""
        hidden = " hidden"
    return f'<p class="next-open" data-unit-next-open="{esc(unit_id)}"{hidden}>{esc(text)}</p>'


def room_alt(room, content, occurrence):
    short = content["shortName"]
    kind = content["kind"]
    tail = f"{short} {kind} in Brownsville, TX"
    exterior = room.lower() in AT_ROOMS
    titled = room if not room or not room[0].islower() else room[0].upper() + room[1:]
    lower = room if room.startswith("TV") else (room[0].lower() + room[1:] if room else room)
    link = "at" if exterior else "of"
    if occurrence == 1:
        return f"{titled} {link} {tail}"
    ordinal = ORDINALS.get(occurrence, "Another")
    return f"{ordinal} view of the {lower} {link} {tail}"


def alt_list(content):
    counts = {}
    alts = []
    for room in content.get("photoRooms") or []:
        counts[room] = counts.get(room, 0) + 1
        alts.append(room_alt(room, content, counts[room]))
    return alts


def photo_alt(content, index):
    alts = alt_list(content)
    if 0 <= index < len(alts):
        return alts[index]
    return f"Photo of {content['shortName']} {content['kind']} in Brownsville, TX"


def placeholder_alt(content):
    return f"Photos coming soon for {content['shortName']}, {content['kind']} in Brownsville, TX"


def unit_by_slug(units, slug):
    for unit in units:
        if unit["slug"] == slug:
            return unit
    return None


def build_srcset(variants, kind, depth):
    parts = []
    for slot in ("400", "800", "1200"):
        info = variants[slot]
        parts.append(f"{rel(depth, info[kind])} {int(info['width'])}w")
    return ", ".join(parts)


def render_responsive(record, alt, depth, role, eager=False, extra_class="", element_id=""):
    class_attr = f' class="{extra_class}"' if extra_class else ""
    id_attr = f' id="{element_id}"' if element_id else ""
    loading = ' fetchpriority="high"' if eager else ' loading="lazy" decoding="async"'
    entry = record.get("entry")
    if entry:
        variants = entry["variants"]
        slot = IMAGE_SLOT[role]
        chosen = variants[slot]
        sizes = IMAGE_SIZES[role]
        jpg_srcset = build_srcset(variants, "jpg", depth)
        webp_srcset = build_srcset(variants, "webp", depth)
        src = rel(depth, chosen["jpg"])
        img = (
            f'<img{id_attr}{class_attr} src="{src}" srcset="{jpg_srcset}" sizes="{sizes}" '
            f'width="{int(chosen["width"])}" height="{int(chosen["height"])}" '
            f'alt="{esc(alt)}"{loading}>'
        )
        source = f'<source type="image/webp" srcset="{webp_srcset}" sizes="{sizes}">'
        markup = f"<picture>{source}{img}</picture>"
        meta = {
            "href": rel(depth, variants["1200"]["jpg"]),
            "webp": webp_srcset,
            "jpg": jpg_srcset,
            "width": int(variants["1200"]["width"]),
            "height": int(variants["1200"]["height"]),
        }
        return markup, meta
    src = rel(depth, record["src"])
    img = (
        f'<img{id_attr}{class_attr} src="{src}" width="{int(record["width"])}" '
        f'height="{int(record["height"])}" alt="{esc(alt)}"{loading}>'
    )
    return img, {
        "href": src,
        "webp": "",
        "jpg": "",
        "width": int(record["width"]),
        "height": int(record["height"]),
    }


def render_header(depth, current, site_name):
    links = []
    for key, label, path in NAV:
        current_attr = ' aria-current="page"' if key == current else ""
        links.append(f'        <a href="{rel(depth, path)}"{current_attr}>{label}</a>')
    nav = "\n".join(links)
    return f"""<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="{rel(depth, "index.html")}"><span class="brand-mark" aria-hidden="true"></span>{esc(site_name)}</a>
    <nav aria-label="Primary">
{nav}
    </nav>
  </div>
</header>"""


def render_footer(depth, config, year):
    links = []
    for _key, label, path in NAV:
        links.append(f'      <a href="{rel(depth, path)}">{label}</a>')
    nav = "\n".join(links)
    return f"""<footer class="site-footer">
  <div class="wrap footer-inner">
    <p>{esc(config["siteName"])} - {esc(config["company"])} - {esc(config["city"])}, {esc(config["state"])}</p>
    <nav class="footer-nav" aria-label="Footer">
{nav}
    </nav>
    <p>{year}</p>
  </div>
</footer>"""


def render_document(
    depth,
    current,
    config,
    year,
    title,
    description,
    canonical,
    main,
    structured=None,
    image_path=None,
    image_alt="",
    robots=None,
    verification=None,
    twitter_card="summary_large_image",
):
    blocks = json_ld_scripts(structured)
    share_path = share_image_path(image_path)
    image = absolute_url(config["baseUrl"], share_path)
    robots_tag = f'\n  <meta name="robots" content="{esc(robots)}">' if robots else ""
    verification_tag = ""
    if verification is not None:
        token = verification.strip() if isinstance(verification, str) else ""
        if token:
            verification_tag = (
                f'\n  <meta name="google-site-verification" content="{esc(token)}">'
            )
        else:
            verification_tag = (
                '\n  <!-- google-site-verification: set "googleSiteVerification" '
                'in site.config.json and rebuild -->'
            )
    alt = image_alt or "Casper Rentals in Brownsville, TX"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">{robots_tag}{verification_tag}
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:site_name" content="{esc(config["siteName"])}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(image)}">
  <meta property="og:image:alt" content="{esc(alt)}">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="{esc(twitter_card)}">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="{esc(image)}">
  <meta name="twitter:image:alt" content="{esc(alt)}">
  <link rel="icon" href="{rel(depth, "assets/img/favicon.svg")}" type="image/svg+xml">
  <link rel="icon" href="{rel(depth, "assets/img/favicon-32.png")}" type="image/png" sizes="32x32">
  <link rel="apple-touch-icon" href="{rel(depth, "assets/img/apple-touch-icon.png")}">
  <meta name="theme-color" content="#0b4f5c">
  <link rel="stylesheet" href="{rel(depth, "assets/css/style.css")}">{blocks}
</head>
<body data-availability-src="{rel(depth, "data/availability.json")}">
{render_header(depth, current, config["siteName"])}
<main id="main">
{main}
</main>
{render_footer(depth, config, year)}
<script src="{rel(depth, "assets/js/main.js")}" defer></script>
</body>
</html>
"""


def postal_address(unit=None):
    locality = unit["locality"] if unit else "Brownsville"
    region = unit["region"] if unit else "TX"
    country = unit["country"] if unit else "US"
    return {
        "@type": "PostalAddress",
        "addressLocality": locality,
        "addressRegion": region,
        "addressCountry": country,
    }


def organization_schema(config):
    return {
        "@context": "https://schema.org",
        "@type": ["LodgingBusiness", "LocalBusiness"],
        "@id": business_id(config),
        "name": config["siteName"],
        "legalName": config["company"],
        "url": absolute_url(config["baseUrl"], "/"),
        "image": absolute_url(config["baseUrl"], share_image_path(DEFAULT_OG)),
        "logo": absolute_url(config["baseUrl"], "assets/img/apple-touch-icon.png"),
        "description": BUSINESS_DESCRIPTION,
        "address": postal_address(),
        "areaServed": {
            "@type": "City",
            "name": "Brownsville",
            "containedInPlace": {
                "@type": "State",
                "name": "Texas",
            },
        },
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer service",
            "url": absolute_url(config["baseUrl"], "contact.html"),
            "areaServed": "US",
            "availableLanguage": ["English"],
        },
    }


def unit_schema(config, unit, content, photos):
    if photos:
        images = [absolute_url(config["baseUrl"], path) for path in photos]
    else:
        images = [absolute_url(config["baseUrl"], PLACEHOLDER)]
    address = postal_address(unit)
    return {
        "@context": "https://schema.org",
        "@type": schema_type(unit),
        "name": content["shortName"],
        "description": content["about"],
        "url": absolute_url(config["baseUrl"], f"units/{unit['slug']}.html"),
        "image": images,
        "address": address,
        "containedInPlace": {
            "@type": "Place",
            "name": "Brownsville, TX",
            "address": postal_address(unit),
        },
    }


def breadcrumb_schema(config, unit, content):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": absolute_url(config["baseUrl"], "/"),
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Units",
                "item": absolute_url(config["baseUrl"], "units.html"),
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": content["shortName"],
                "item": absolute_url(config["baseUrl"], f"units/{unit['slug']}.html"),
            },
        ],
    }


def item_list_schema(config, units, content, name=None):
    elements = []
    for index, unit in enumerate(units, start=1):
        elements.append(
            {
                "@type": "ListItem",
                "position": index,
                "name": content[unit["id"]]["shortName"],
                "url": absolute_url(config["baseUrl"], f"units/{unit['slug']}.html"),
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": name or f"{config['siteName']} units in {config['city']}, {config['state']}",
        "itemListElement": elements,
    }


def webpage_schema(config, title, description, path):
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": absolute_url(config["baseUrl"], path),
        "isPartOf": {
            "@type": "WebSite",
            "name": config["siteName"],
            "url": absolute_url(config["baseUrl"], "/"),
        },
    }


def grouped_properties(units):
    groups = []
    for unit in units:
        if not groups or groups[-1][0] != unit["property"]:
            groups.append((unit["property"], []))
        groups[-1][1].append(unit)
    return groups


def property_photo(grouped, manifest):
    preferred = [unit for unit in grouped if unit["id"] not in COMMERCIAL_IDS]
    ordered = preferred + [unit for unit in grouped if unit["id"] in COMMERCIAL_IDS]
    for unit in ordered:
        records = photo_records(unit["slug"], manifest)
        if records:
            return unit, records[:1]
    return grouped[0], []


def render_card_media(content, records, depth, href=None):
    if records:
        alt = photo_alt(content, 0)
        image, _meta = render_responsive(records[0], alt, depth, "card")
    else:
        image, _meta = render_responsive(placeholder_record(), placeholder_alt(content), depth, "card")
    if href:
        return f'<a class="card-media" href="{href}">\n          {image}\n        </a>'
    return f'<span class="card-media">{image}</span>'


def render_unit_media(unit, content, records):
    if not records:
        image, _meta = render_responsive(
            placeholder_record(),
            placeholder_alt(content),
            1,
            "main",
            eager=True,
            element_id="unit-main-photo",
        )
        return (
            '    <div class="unit-photo">\n'
            f"      {image}\n"
            "    </div>"
        )
    alts = alt_list(content)
    items = []
    for index, record in enumerate(records):
        alt = alts[index] if index < len(alts) else photo_alt(content, index)
        thumb, meta = render_responsive(record, alt, 1, "thumb")
        current = ' aria-current="true"' if index == 0 else ""
        data = ""
        if meta["jpg"]:
            data = (
                f' data-webp-srcset="{esc(meta["webp"])}"'
                f' data-jpg-srcset="{esc(meta["jpg"])}"'
                f' data-width="{meta["width"]}"'
                f' data-height="{meta["height"]}"'
            )
        items.append(
            "        <li>\n"
            f'          <a href="{esc(meta["href"])}"{data}{current}>\n'
            f"            {thumb}\n"
            "          </a>\n"
            "        </li>"
        )
    main_image, _meta = render_responsive(
        records[0],
        alts[0],
        1,
        "main",
        eager=True,
        element_id="unit-main-photo",
    )
    thumbs = "\n".join(items)
    return (
        '    <div class="unit-photo">\n'
        f"      {main_image}\n"
        '      <ul class="photo-thumbs">\n'
        f"{thumbs}\n"
        "      </ul>\n"
        '      <p class="photo-note">Photos from the unit\'s public listing.</p>\n'
        "    </div>"
    )


def render_unit_card(unit, content, info, records, heading="h2", show_details=True):
    page = rel(0, f"units/{unit['slug']}.html")
    media = render_card_media(content, records[:1], 0, href=page)
    if show_details:
        ask_href = rel(0, f"contact.html?unit={quote(unit['id'])}")
        details = f"""          <p class="property-name">{esc(unit["property"])}</p>
          <p class="locality">{esc(unit["locality"])}, {esc(unit["region"])}</p>
          <p>{badge_html(unit["id"], info["status"])}</p>
          <p class="rent">Rent: Contact us</p>
          <div class="card-actions">
            <a class="btn" href="{ask_href}">Ask about this unit</a>
          </div>"""
    else:
        details = f"""          <p>{badge_html(unit["id"], info["status"])}</p>"""
    short = content["shortName"]
    return f"""      <article class="card" data-unit-card data-unit-id="{esc(unit["id"])}" data-property="{esc(unit["property"])}" data-status="{esc(info["status"])}">
        {media}
        <div class="card-body">
          <{heading}><a href="{page}">{esc(short)}</a></{heading}>
{details}
        </div>
      </article>"""


def render_home(config, units, content, availability, manifest, year):
    city = config["city"]
    state = config["state"]
    hero_unit = unit_by_slug(units, HERO_SLUG)
    hero_content = content[hero_unit["id"]]
    hero_records = photo_records(HERO_SLUG, manifest)
    if hero_records:
        hero_record = hero_records[0]
        hero_alt = photo_alt(hero_content, 0)
        hero_path = hero_record["src"]
    else:
        hero_record = placeholder_record()
        hero_alt = placeholder_alt(hero_content)
        hero_path = None
    hero_img, _meta = render_responsive(
        hero_record, hero_alt, 0, "hero", eager=True, extra_class="hero-photo"
    )
    band_unit = unit_by_slug(units, CREW_BAND_SLUG)
    band_content = content[band_unit["id"]]
    band_records = photo_records(CREW_BAND_SLUG, manifest)
    if band_records:
        band_record = band_records[0]
        band_alt = photo_alt(band_content, 0)
    else:
        band_record = placeholder_record()
        band_alt = placeholder_alt(band_content)
    band_img, _meta = render_responsive(band_record, band_alt, 0, "band")
    cards = []
    for property_name, grouped in grouped_properties(units):
        meta = SECTION_META.get(
            property_name,
            {
                "anchor": "property-" + re.sub(r"[^a-z0-9]+", "-", property_name.lower()).strip("-"),
                "title": property_name,
                "intro": f"Rental units at {property_name} in {city}, {state}.",
            },
        )
        photo_unit, records = property_photo(grouped, manifest)
        media = render_card_media(content[photo_unit["id"]], records, 0)
        href = rel(0, "units.html?property=" + quote(property_name))
        cards.append(
            f"""      <a class="card property-card" id="{esc(meta["anchor"])}" href="{href}">
        {media}
        <div class="card-body">
          <h3>{esc(meta["title"])}</h3>
          <p>{esc(meta["intro"])}</p>
          <span class="card-cta">View these units</span>
        </div>
      </a>"""
        )
    as_of = availability.get("asOf", "")
    as_of_text = f"Availability as of {pretty_date(as_of)}" if as_of else "Availability"
    port_paragraphs = "\n".join(
        f"    <p>{esc(paragraph)}</p>" for paragraph in PORT_PARAGRAPHS
    )
    main = f"""  <section class="hero">
    {hero_img}
    <div class="hero-scrim">
      <div class="wrap">
        <div class="hero-copy">
          <p class="eyebrow">{esc(city)}, {esc(state)}</p>
          <h1>Rentals in {esc(city)}, {esc(state)}</h1>
          <p>Casper Rentals offers apartments in {esc(city)}, townhouses on Champion Dr, and small commercial suites at 4 Greenway Dr. Look through Brownsville apartments and other Brownsville TX rentals in the Rio Grande Valley, then contact us about a unit.</p>
          <div class="hero-actions">
            <a class="btn" href="{rel(0, "units.html?available=1")}">See available units</a>
            <a class="btn btn-secondary" href="{rel(0, "working-crews.html")}">Crew stays</a>
          </div>
        </div>
      </div>
    </div>
  </section>
  <section class="crew-band">
    <div class="wrap crew-band-inner">
      <div class="crew-band-photo">
        {band_img}
      </div>
      <div class="crew-band-copy">
        <p class="eyebrow">Weekly and monthly</p>
        <h2>Stays for Working Crews</h2>
        <p>Furnished apartments and townhouses in {esc(city)}, {esc(state)} are open as weekly and monthly stays for working crews.</p>
        <p>Seasonal and contract workers on Port of Brownsville LNG projects, wind turbine techs, and crews working in the City of Starbase, TX can stay for the length of a job.</p>
        <p>Tell us your dates and how many people are in the group.</p>
        <div class="cta-actions">
          <a class="btn" href="{rel(0, "working-crews.html")}">Crew stays</a>
          <a class="btn" href="{rel(0, "contact.html?unit=crew")}">Ask about a crew stay</a>
        </div>
        <p class="footnote">{esc(CREW_FOOTNOTE)}</p>
      </div>
    </div>
  </section>
  <section class="wrap section port-section" id="port-of-brownsville">
    <div class="section-heading">
      <h2>{PORT_HEADING}</h2>
    </div>
{port_paragraphs}
    <p class="affiliation-note">{esc(AFFILIATION_NOTE)}</p>
  </section>
  <div class="wrap section">
    <p class="as-of" data-as-of>{esc(as_of_text)}</p>
    <div class="section-heading">
      <h2>Brownsville rental properties</h2>
      <p>Apartments, townhouses, and small commercial suites. Open a property to see its units and availability.</p>
    </div>
    <div class="card-grid property-grid">
{chr(10).join(cards)}
    </div>
    <section class="cta">
      <h2>Ask about a Brownsville rental</h2>
      <p>Tell us which unit you want to know more about. Rent is shared when you contact us.</p>
      <div class="cta-actions">
        <a class="btn" href="{rel(0, "contact.html")}">Contact us</a>
        <a class="btn btn-secondary" href="{rel(0, "units.html")}">Browse all units</a>
      </div>
    </section>
  </div>"""
    return render_document(
        0,
        "home",
        config,
        year,
        HOME_TITLE,
        HOME_DESCRIPTION,
        absolute_url(config["baseUrl"], "/"),
        main,
        [organization_schema(config)],
        hero_path,
        hero_alt,
        verification=config.get("googleSiteVerification", ""),
    )


def render_units_page(config, units, content, availability, manifest, year):
    city = config["city"]
    state = config["state"]
    cards = []
    image_path = None
    image_alt = ""
    for unit in units:
        info = availability_for(availability, unit["id"])
        records = photo_records(unit["slug"], manifest)
        if image_path is None and records:
            image_path = records[0]["src"]
            image_alt = photo_alt(content[unit["id"]], 0)
        cards.append(render_unit_card(unit, content[unit["id"]], info, records))
    properties = []
    seen = set()
    for unit in units:
        if unit["property"] not in seen:
            seen.add(unit["property"])
            properties.append(unit["property"])
    options = ['        <option value="">All</option>']
    for name in properties:
        options.append(f'        <option value="{esc(name)}">{esc(name)}</option>')
    as_of = availability.get("asOf", "")
    as_of_text = f"Availability as of {pretty_date(as_of)}" if as_of else "Availability"
    main = f"""  <div class="wrap page-intro">
    <h1>Rental units in {esc(city)}, {esc(state)}</h1>
    <p class="lead">Every Casper Rentals listing in {esc(city)} is shown here, including Brownsville apartments at 4 Greenway Dr, townhouses on Champion Dr, and Aurora at Paredes Line Rd. These are Brownsville TX rentals in the Rio Grande Valley. Rent: Contact us.</p>
    <p class="crew-link">Working in town on a contract? See <a href="{rel(0, "working-crews.html")}">stays for working crews</a> with furnished weekly and monthly stays.</p>
    <p class="as-of" data-as-of>{esc(as_of_text)}</p>
    <div class="filters" role="group" aria-label="Filter units">
      <label class="filter-field" for="property-filter">Property
        <select id="property-filter">
{chr(10).join(options)}
        </select>
      </label>
      <label class="check-field" for="available-only">
        <input id="available-only" type="checkbox">
        Show only available units
      </label>
    </div>
    <p id="filter-summary" aria-live="polite">{len(units)} rental units in {esc(city)}, {esc(state)}.</p>
    <p id="filter-empty" hidden>No units match these filters. <a href="{rel(0, "contact.html")}">Contact us</a> and we can help you find a {esc(city)}, {esc(state)} rental.</p>
    <noscript><p>All units are listed below. Availability is shown on each one.</p></noscript>
    <div class="card-grid" id="unit-list">
{chr(10).join(cards)}
    </div>
    <section class="cta">
      <h2>Ready to ask about a unit?</h2>
      <p>Contact Casper Rentals about any Brownsville, TX rental on this page.</p>
      <div class="cta-actions">
        <a class="btn" href="{rel(0, "contact.html")}">Contact us</a>
      </div>
    </section>
  </div>"""
    return render_document(
        0,
        "units",
        config,
        year,
        UNITS_TITLE,
        UNITS_DESCRIPTION,
        absolute_url(config["baseUrl"], "units.html"),
        main,
        [item_list_schema(config, units, content)],
        image_path,
        image_alt,
    )


def crew_page_hero(units, content, manifest):
    for slug in CREW_HERO_SLUGS:
        unit = unit_by_slug(units, slug)
        records = photo_records(slug, manifest) if unit else []
        if unit and records:
            return records[0], photo_alt(content[unit["id"]], 0), records[0]["src"]
    return placeholder_record(), "Photos coming soon for a Casper Rentals unit in Brownsville, TX", None


def render_crews_page(config, units, content, availability, manifest, year):
    city = config["city"]
    state = config["state"]
    furnished = [unit for unit in units if unit["id"] in FURNISHED_IDS]
    cards = []
    for unit in furnished:
        info = availability_for(availability, unit["id"])
        records = photo_records(unit["slug"], manifest)
        cards.append(
            render_unit_card(
                unit,
                content[unit["id"]],
                info,
                records,
                heading="h3",
                show_details=False,
            )
        )
    sections = []
    for heading, paragraphs in CREW_SECTIONS:
        body = "\n".join(f"          <p>{esc(paragraph)}</p>" for paragraph in paragraphs)
        sections.append(
            f"""      <section class="feature-card">
        <h2>{esc(heading)}</h2>
        <div class="feature-body">
{body}
        </div>
      </section>"""
        )
    port_paragraphs = "\n".join(
        f"      <p>{esc(paragraph)}</p>" for paragraph in PORT_PARAGRAPHS
    )
    hero_record, hero_alt, hero_path = crew_page_hero(units, content, manifest)
    hero_img, _meta = render_responsive(
        hero_record, hero_alt, 0, "hero", eager=True, extra_class="hero-photo"
    )
    as_of = availability.get("asOf", "")
    as_of_text = f"Availability as of {pretty_date(as_of)}" if as_of else "Availability"
    main = f"""  <section class="hero">
    {hero_img}
    <div class="hero-scrim">
      <div class="wrap">
        <div class="hero-copy">
          <p class="eyebrow">{esc(city)}, {esc(state)}</p>
          <h1>Stays for Working Crews in {esc(city)}, {esc(state)}</h1>
          <p class="lead">Furnished apartments and townhouses in {esc(city)}, {esc(state)} are available for seasonal and contract workers. Weekly and monthly stays suit working crews who are in town for Port of Brownsville LNG projects, wind industry work, or a job in the City of Starbase, TX.</p>
          <div class="hero-actions">
            <a class="btn" href="{rel(0, "contact.html?unit=crew")}">Ask about a crew stay</a>
            <a class="btn btn-secondary" href="{rel(0, "units.html")}">See all units</a>
          </div>
        </div>
      </div>
    </div>
  </section>
  <div class="wrap page-intro">
    <p class="as-of" data-as-of>{esc(as_of_text)}</p>
    <div class="feature-grid">
{chr(10).join(sections)}
    </div>
    <section class="prose-block port-section" id="port-of-brownsville">
      <h2>{PORT_HEADING}</h2>
{port_paragraphs}
      <p class="affiliation-note">{esc(AFFILIATION_NOTE)}</p>
    </section>
    <section class="prose-block">
      <h2>Furnished units</h2>
      <p>These apartments and townhouses are furnished. Weekly and monthly stays are available. Open a unit to see its photos and current status.</p>
    </section>
    <div class="card-grid" id="crew-units">
{chr(10).join(cards)}
    </div>
    <section class="cta">
      <h2>Ask about a crew stay</h2>
      <p>Tell us how many people, your dates, and whether you need a weekly or monthly stay.</p>
      <div class="cta-actions">
        <a class="btn" href="{rel(0, "contact.html?unit=crew")}">Ask about a crew stay</a>
      </div>
    </section>
    <p class="footnote">{esc(CREW_FOOTNOTE)}</p>
  </div>"""
    return render_document(
        0,
        "crews",
        config,
        year,
        CREWS_TITLE,
        CREWS_DESCRIPTION,
        absolute_url(config["baseUrl"], "working-crews.html"),
        main,
        [
            webpage_schema(config, CREWS_TITLE, CREWS_DESCRIPTION, "working-crews.html"),
            item_list_schema(
                config,
                furnished,
                content,
                name=f"Furnished units for working crews in {city}, {state}",
            ),
        ],
        hero_path,
        hero_alt,
    )


def render_related(unit, units, content):
    label = GROUP_LABELS.get(unit["property"], unit["property"])
    others = [
        other
        for other in units
        if other["property"] == unit["property"] and other["id"] != unit["id"]
    ]
    if others:
        links = []
        for other in others:
            short = content[other["id"]]["shortName"]
            links.append(f'        <li><a href="{esc(other["slug"] + ".html")}">{esc(short)}</a></li>')
        body = "      <ul class=\"related-units\">\n" + "\n".join(links) + "\n      </ul>"
    else:
        body = "      <p>Contact us and we can suggest another unit.</p>"
    return f"""    <section>
      <h2>More units at {esc(label)}</h2>
{body}
    </section>"""


def render_unit_page(config, unit, units, content, availability, manifest, year):
    info = availability_for(availability, unit["id"])
    entry = content[unit["id"]]
    records = photo_records(unit["slug"], manifest)
    photos = [record["src"] for record in records]
    city_line = f"{unit['locality']}, {unit['region']}"
    airbnb = ""
    if unit.get("airbnbName"):
        airbnb = f'\n        <p class="airbnb">Also listed on Airbnb as {esc(unit["airbnbName"])}</p>'
    stay = ""
    if unit["id"] in FURNISHED_IDS:
        stay = f'\n        <p class="stay-note">{esc(FURNISHED_LINE)}</p>'
    ask_href = rel(1, "contact.html?unit=" + quote(unit["id"]))
    highlights = "\n".join(f"        <li>{esc(item)}</li>" for item in entry["highlights"])
    footnote = ""
    if unit["id"] in FURNISHED_IDS:
        footnote = f'\n      <p class="footnote">{esc(CREW_FOOTNOTE)}</p>'
    if unit["id"] in FURNISHED_IDS:
        noun = "townhouse" if entry["kind"] == "furnished townhouse" else "apartment"
        stays = f"""    <section>
      <h2>Stays for working crews</h2>
      <p>This furnished {noun} can be booked as a weekly or monthly stay. <a href="{rel(1, "working-crews.html")}">See stays for working crews</a>.</p>
    </section>"""
    else:
        stays = f"""    <p class="crew-link">Looking for a furnished weekly or monthly stay instead? See our <a href="{rel(1, "working-crews.html")}">furnished units for working crews</a>.</p>"""
    main = f"""  <div class="wrap unit-page">
    <div class="unit-layout">
{render_unit_media(unit, entry, records)}
      <div class="unit-details">
        <p class="eyebrow">{esc(unit["property"])}</p>
        <h1>{esc(entry["shortName"])}</h1>
        <p class="address">{esc(unit["address"])}</p>
        <p class="locality">{esc(city_line)}</p>
        <div class="info-panel">
          <h2>Availability and rent</h2>
          <p>{badge_html(unit["id"], info["status"])}</p>
          {next_open_html(unit["id"], info["nextOpenDate"])}
          <p class="rent">Rent: Contact us for pricing</p>{stay}{airbnb}
          <div class="unit-actions">
            <a class="btn" href="{ask_href}">Ask about this unit</a>
          </div>
        </div>
        <p class="back-link"><a href="{rel(1, "units.html")}">All units</a></p>
      </div>
    </div>
    <div class="unit-copy">
      <section>
        <h2>About {esc(entry["shortName"])}</h2>
        <p>{esc(entry["about"])}</p>
      </section>
      <section>
        <h2>Highlights</h2>
        <ul>
{highlights}
        </ul>
      </section>
      <section>
        <h2>Location: Brownsville, TX</h2>
        <p>{esc(entry["location"])}</p>{footnote}
      </section>
{render_related(unit, units, content)}
{stays}
    </div>
  </div>"""
    title = (
        f"{entry['shortName']} - {KIND_TITLE[entry['kind']]} in Brownsville, TX | {config['siteName']}"
    )
    description = entry["metaDescription"]
    if photos:
        image_path = photos[0]
        image_alt = photo_alt(entry, 0)
        twitter_card = "summary_large_image"
    else:
        image_path = SITE_ICON
        image_alt = SITE_ICON_ALT
        twitter_card = "summary"
    return render_document(
        1,
        "units",
        config,
        year,
        title,
        description,
        absolute_url(config["baseUrl"], f"units/{unit['slug']}.html"),
        main,
        [unit_schema(config, unit, entry, photos), breadcrumb_schema(config, unit, entry)],
        image_path,
        image_alt,
        twitter_card=twitter_card,
    )


def render_contact(config, units, content, year):
    endpoint = config["formspreeEndpoint"]
    placeholder = "PLACEHOLDER" in endpoint
    note = ""
    if placeholder:
        note = (
            '      <p class="notice" id="form-setup-note" role="status" tabindex="-1">'
            "The contact form is being set up. Check back soon.</p>\n"
        )
    options = [
        '          <option value="">Not sure / any unit</option>',
        '          <option value="crew">Crew or group stay (weekly or monthly)</option>',
    ]
    for unit in units:
        options.append(
            f'          <option value="{esc(unit["id"])}">{esc(unit["name"])}</option>'
        )
    hero = unit_by_slug(units, HERO_SLUG)
    image_alt = photo_alt(content[hero["id"]], 0) if hero else ""
    main = f"""  <div class="wrap page-intro">
    <div class="contact-layout">
      <div class="contact-intro">
        <h1>Contact us about a Brownsville, {esc(config["state"])} rental</h1>
        <p class="lead">Ask Casper Rentals about apartments in {esc(config["city"])}, townhouses on Champion Dr, or small commercial suites at 4 Greenway Dr. Furnished weekly and monthly stays are available for working crews. We rent in {esc(config["city"])}, {esc(config["state"])}, in the Rio Grande Valley.</p>
      </div>
      <aside class="how-panel">
        <h2>How it works</h2>
        <ol>
          <li>Choose a unit, or a crew or group stay.</li>
          <li>Tell us your dates. For a crew, add how many people and whether you want a weekly or monthly stay.</li>
          <li>We reply about availability. Rent is shared when you contact us.</li>
        </ol>
      </aside>
      <div class="contact-form-wrap">
{note}        <form id="contact-form" class="form" method="POST" action="{esc(endpoint)}" accept-charset="UTF-8">
          <input type="hidden" name="_subject" value="New Casper Rentals inquiry">
          <div hidden>
            <label for="gotcha">Leave this field blank</label>
            <input id="gotcha" type="text" name="_gotcha" tabindex="-1" autocomplete="off">
          </div>
          <label for="name">Name <span class="req">(required)</span></label>
          <input id="name" name="name" type="text" autocomplete="name" required>
          <label for="email">Email <span class="req">(required)</span></label>
          <input id="email" name="email" type="email" autocomplete="email" required>
          <label for="phone">Phone (optional)</label>
          <input id="phone" name="phone" type="tel" autocomplete="tel">
          <label for="unit-interest">Unit of interest</label>
          <select id="unit-interest" name="unit">
{chr(10).join(options)}
          </select>
          <label for="people">Number of people (optional)</label>
          <input id="people" name="people" type="text" inputmode="numeric" autocomplete="off">
          <label for="move-in">Desired move-in date (optional)</label>
          <input id="move-in" name="move_in" type="date">
          <label for="message">Message <span class="req">(required)</span></label>
          <textarea id="message" name="message" rows="6" required aria-describedby="message-hint"></textarea>
          <p class="field-hint" id="message-hint">For crew or group stays, tell us how many people, your dates, and weekly or monthly.</p>
          <p class="card-actions"><button class="btn" type="submit">Contact us</button></p>
        </form>
      </div>
    </div>
  </div>"""
    return render_document(
        0,
        "contact",
        config,
        year,
        CONTACT_TITLE,
        CONTACT_DESCRIPTION,
        absolute_url(config["baseUrl"], "contact.html"),
        main,
        image_path=DEFAULT_OG,
        image_alt=image_alt,
    )


def render_404(config, units, content, year):
    hero = unit_by_slug(units, HERO_SLUG)
    image_alt = photo_alt(content[hero["id"]], 0) if hero else ""
    main = f"""  <div class="wrap page-intro">
    <h1>Page not found</h1>
    <p>That page is not on the {esc(config["siteName"])} site. Browse {esc(config["city"])}, {esc(config["state"])} rentals from the home page or contact us about a unit.</p>
    <div class="cta-actions">
      <a class="btn" href="{rel(0, "index.html")}">Back to home</a>
      <a class="btn btn-secondary" href="{rel(0, "units.html")}">View units</a>
      <a class="btn btn-secondary" href="{rel(0, "contact.html")}">Contact us</a>
    </div>
  </div>"""
    return render_document(
        0,
        "",
        config,
        year,
        NOT_FOUND_TITLE,
        NOT_FOUND_DESCRIPTION,
        absolute_url(config["baseUrl"], "404.html"),
        main,
        image_path=DEFAULT_OG,
        image_alt=image_alt,
        robots="noindex",
    )


def render_sitemap(config, units, availability):
    as_of = availability.get("asOf") or date.today().isoformat()
    paths = ["/", "units.html", "working-crews.html", "contact.html"]
    paths.extend(f"units/{unit['slug']}.html" for unit in units)
    body = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in paths:
        loc = absolute_url(config["baseUrl"], path)
        body.append("  <url>")
        body.append(f"    <loc>{esc(loc)}</loc>")
        body.append(f"    <lastmod>{esc(as_of)}</lastmod>")
        body.append("  </url>")
    body.append("</urlset>")
    return "\n".join(body) + "\n"


def render_robots(config):
    sitemap = absolute_url(config["baseUrl"], "sitemap.xml")
    return f"User-agent: *\nAllow: /\nDisallow: /Archive/\n\nSitemap: {sitemap}\n"


def main():
    config = load_json(ROOT / "site.config.json")
    for key in ("siteName", "company", "city", "state", "baseUrl", "formspreeEndpoint"):
        if key not in config or not str(config[key]).strip():
            sys.exit(f"error: site.config.json missing {key}")
    units = load_json(ROOT / "data" / "units.json")
    validate_units(units)
    content = load_unit_content(units)
    availability = load_json(ROOT / "data" / "availability.json")
    if not isinstance(availability, dict) or "units" not in availability:
        sys.exit("error: data/availability.json must contain units")
    manifest = load_manifest()
    for name in (
        "assets/img/favicon.svg",
        "assets/img/favicon-32.png",
        "assets/img/apple-touch-icon.png",
    ):
        if not (ROOT / name).is_file():
            print(f"Warning: missing {name}")

    year = date.today().year
    write_text(ROOT / "index.html", render_home(config, units, content, availability, manifest, year))
    write_text(
        ROOT / "units.html",
        render_units_page(config, units, content, availability, manifest, year),
    )
    write_text(
        ROOT / "working-crews.html",
        render_crews_page(config, units, content, availability, manifest, year),
    )
    write_text(ROOT / "contact.html", render_contact(config, units, content, year))
    write_text(ROOT / "404.html", render_404(config, units, content, year))
    for unit in units:
        write_text(
            ROOT / "units" / f"{unit['slug']}.html",
            render_unit_page(config, unit, units, content, availability, manifest, year),
        )
    sitemap = render_sitemap(config, units, availability)
    write_text(ROOT / "sitemap.xml", sitemap)
    write_text(ROOT / "robots.txt", render_robots(config))
    write_text(ROOT / ".nojekyll", "")

    html_pages = 5 + len(units)
    url_count = sitemap.count("<loc>")
    print(
        f"Built {html_pages} HTML pages, sitemap with {url_count} URLs, robots.txt, and .nojekyll "
        "at the repository root"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
