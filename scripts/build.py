#!/usr/bin/env python3
"""Generate the Casper Rentals static site into the repository root.

Overwrites only the generated pages, sitemap, robots.txt, and .nojekyll.
Does not delete or copy anything else. assets/ and data/ stay where they are.
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
HERO_IMAGE = "assets/img/units/aurora-a/01.jpg"
HERO_ALT = "Photo of Aurora - Unit A in Brownsville, TX"
CREW_IMAGE = "assets/img/units/champions-428-3/01.jpg"
CREW_ALT = "Photo of Champions - 428-3 Champion Dr in Brownsville, TX"
CREW_FOOTNOTE = (
    "Casper Rentals is an independent local rental company and is not affiliated "
    "with any employer or project named on this page."
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
SLUG_RE = re.compile(r"[a-z0-9-]+")
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
        "Near SpaceX Starbase at Boca Chica",
        (
            "Contract workers near SpaceX Starbase at Boca Chica can take a furnished weekly or monthly stay in Brownsville, TX.",
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


def schema_type(unit):
    # Greenway commercial suites use Accommodation. Every other unit uses Apartment.
    if unit["id"] in COMMERCIAL_IDS:
        return "Accommodation"
    return "Apartment"


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


def public_image(path, alt, fallback_alt):
    if (ROOT / path).is_file():
        return path, alt
    return "assets/img/placeholder.svg", fallback_alt


def render_img(alt, src, eager=False, extra_class="", element_id=""):
    id_attr = f' id="{element_id}"' if element_id else ""
    class_attr = f' class="{extra_class}"' if extra_class else ""
    loading = "" if eager else ' loading="lazy"'
    decoding = "" if eager else ' decoding="async"'
    priority = ' fetchpriority="high"' if eager else ""
    return (
        f'<img{id_attr}{class_attr} src="{src}" alt="{esc(alt)}" width="1200" height="900"'
        f"{loading}{decoding}{priority}>"
    )


def photo_bits(unit, photos, depth):
    if photos:
        return rel(depth, photos[0]), f"Photo of {unit['name']}"
    return rel(depth, "assets/img/placeholder.svg"), f"Photos coming soon for {unit['name']}"


def render_card_media(unit, photos, depth, href=None):
    src, alt = photo_bits(unit, photos, depth)
    image = render_img(alt, src)
    if href:
        return f'<a class="card-media" href="{href}">\n          {image}\n        </a>'
    return f'<span class="card-media">{image}</span>'


def render_unit_media(unit, photos):
    name = unit["name"]
    if not photos:
        src, alt = photo_bits(unit, photos, 1)
        image = render_img(alt, src, eager=True)
        return (
            '    <div class="unit-photo">\n'
            f"      {image}\n"
            "    </div>"
        )
    items = []
    for index, path in enumerate(photos, start=1):
        href = rel(1, path)
        alt = f"Photo {index} of {name}"
        current = ' aria-current="true"' if index == 1 else ""
        thumb = render_img(alt, href)
        items.append(
            "        <li>\n"
            f'          <a href="{href}"{current}>\n'
            f"            {thumb}\n"
            "          </a>\n"
            "        </li>"
        )
    main_src, main_alt = photo_bits(unit, photos, 1)
    main_image = render_img(main_alt, main_src, eager=True, element_id="unit-main-photo")
    note = "Photos from the unit's public listing."
    thumbs = "\n".join(items)
    return (
        '    <div class="unit-photo">\n'
        f"      {main_image}\n"
        '      <ul class="photo-thumbs">\n'
        f"{thumbs}\n"
        "      </ul>\n"
        f'      <p class="photo-note">{note}</p>\n'
        "    </div>"
    )


def rel(depth, path):
    return ("../" * depth) + path


def absolute_url(base, path):
    root = base.rstrip("/")
    if path in ("", "/"):
        return root + "/"
    return root + "/" + path.lstrip("/")


def json_ld(payload):
    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    return raw.replace("<", "\\u003c")


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


def render_document(depth, current, config, year, title, description, canonical, main, structured=None, image_path=None):
    blocks = ""
    if structured:
        encoded = "\n".join(json_ld(block) for block in structured)
        blocks = f'\n<script type="application/ld+json">\n{encoded}\n</script>'
    image = absolute_url(config["baseUrl"], image_path or "assets/img/placeholder.svg")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(image)}">
  <link rel="icon" href="{rel(depth, "assets/img/placeholder.svg")}" type="image/svg+xml">
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


def organization_schema(config):
    return {
        "@context": "https://schema.org",
        "@type": "RealEstateAgent",
        "name": config["siteName"],
        "legalName": config["company"],
        "url": absolute_url(config["baseUrl"], "/"),
        "areaServed": {
            "@type": "City",
            "name": config["city"],
            "containedInPlace": {
                "@type": "State",
                "name": "Texas",
            },
        },
    }


def unit_schema(config, unit, photos):
    image_path = photos[0] if photos else "assets/img/placeholder.svg"
    return {
        "@context": "https://schema.org",
        "@type": schema_type(unit),
        "name": unit["name"],
        "description": unit["description"],
        "url": absolute_url(config["baseUrl"], f"units/{unit['slug']}.html"),
        "image": absolute_url(config["baseUrl"], image_path),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": unit["address"],
            "addressLocality": unit["locality"],
            "addressRegion": unit["region"],
            "addressCountry": unit["country"],
        },
    }


def item_list_schema(config, units, name=None):
    elements = []
    for index, unit in enumerate(units, start=1):
        elements.append(
            {
                "@type": "ListItem",
                "position": index,
                "name": unit["name"],
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


def property_photo(grouped):
    preferred = [unit for unit in grouped if unit["id"] not in COMMERCIAL_IDS]
    ordered = preferred + [unit for unit in grouped if unit["id"] in COMMERCIAL_IDS]
    for unit in ordered:
        photos = unit_photo_paths(unit["slug"])
        if photos:
            return unit, photos
    return grouped[0], []


def render_unit_card(unit, info, photos, heading="h2", show_details=True):
    page = rel(0, f"units/{unit['slug']}.html")
    media = render_card_media(unit, photos, 0, href=page)
    details = ""
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
    return f"""      <article class="card" data-unit-card data-unit-id="{esc(unit["id"])}" data-property="{esc(unit["property"])}" data-status="{esc(info["status"])}">
        {media}
        <div class="card-body">
          <{heading}><a href="{page}">{esc(unit["name"])}</a></{heading}>
{details}
        </div>
      </article>"""


def render_home(config, units, availability, year):
    city = config["city"]
    state = config["state"]
    hero_path, hero_alt = public_image(
        HERO_IMAGE,
        HERO_ALT,
        "Photos coming soon for a Casper Rentals unit in Brownsville, TX",
    )
    crew_path, crew_alt = public_image(
        CREW_IMAGE,
        CREW_ALT,
        "Photos coming soon for a Casper Rentals unit in Brownsville, TX",
    )
    hero_img = render_img(hero_alt, rel(0, hero_path), eager=True, extra_class="hero-photo")
    crew_img = render_img(crew_alt, rel(0, crew_path))
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
        photo_unit, photos = property_photo(grouped)
        media = render_card_media(photo_unit, photos[:1], 0)
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
        {crew_img}
      </div>
      <div class="crew-band-copy">
        <p class="eyebrow">Weekly and monthly</p>
        <h2>Stays for Working Crews</h2>
        <p>Furnished apartments and townhouses in {esc(city)}, {esc(state)} are open as weekly and monthly stays for working crews.</p>
        <p>Seasonal and contract workers on Port of Brownsville LNG projects, wind turbine techs, and crews near SpaceX Starbase at Boca Chica can stay for the length of a job.</p>
        <p>Tell us your dates and how many people are in the group.</p>
        <div class="cta-actions">
          <a class="btn" href="{rel(0, "working-crews.html")}">Crew stays</a>
          <a class="btn" href="{rel(0, "contact.html?unit=crew")}">Ask about a crew stay</a>
        </div>
      </div>
    </div>
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
    title = f"Rentals in {city}, {state} | {config['siteName']}"
    description = (
        f"{config['siteName']} offers apartments in {city}, townhouses on Champion Dr, "
        f"and small commercial suites at 4 Greenway Dr, including furnished weekly and monthly stays for working crews. "
        f"Contact us about Brownsville TX rentals in the Rio Grande Valley."
    )
    return render_document(
        0,
        "home",
        config,
        year,
        title,
        description,
        absolute_url(config["baseUrl"], "/"),
        main,
        [organization_schema(config)],
        hero_path,
    )


def render_units_page(config, units, availability, year):
    city = config["city"]
    state = config["state"]
    cards = []
    for unit in units:
        info = availability_for(availability, unit["id"])
        photos = unit_photo_paths(unit["slug"])
        cards.append(render_unit_card(unit, info, photos))
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
    title = f"Rental Units in {city}, {state} | {config['siteName']}"
    description = (
        f"Browse Casper Rentals units in {city}, {state}, including furnished weekly and monthly stays for working crews. "
        f"See Brownsville apartments, townhouses on Champion Dr, and commercial suites, check availability, and contact us about Brownsville TX rentals."
    )
    image_path = None
    for unit in units:
        photos = unit_photo_paths(unit["slug"])
        if photos:
            image_path = photos[0]
            break
    return render_document(
        0,
        "units",
        config,
        year,
        title,
        description,
        absolute_url(config["baseUrl"], "units.html"),
        main,
        [item_list_schema(config, units)],
        image_path,
    )


def crew_page_hero(units):
    # champions-4023-4/01.jpg is a wide pool exterior. aurora-b/01.jpg is an interior fallback.
    names = {unit["slug"]: unit["name"] for unit in units}
    fallback_alt = "Photos coming soon for a Casper Rentals unit in Brownsville, TX"
    for slug in ("champions-4023-4", "aurora-b"):
        path = f"assets/img/units/{slug}/01.jpg"
        if slug in names and (ROOT / path).is_file():
            return path, f"Photo of {names[slug]}"
    return "assets/img/placeholder.svg", fallback_alt


def render_crews_page(config, units, availability, year):
    city = config["city"]
    state = config["state"]
    furnished = [unit for unit in units if unit["id"] in FURNISHED_IDS]
    cards = []
    for unit in furnished:
        info = availability_for(availability, unit["id"])
        photos = unit_photo_paths(unit["slug"])
        cards.append(render_unit_card(unit, info, photos, heading="h3", show_details=False))
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
    hero_path, hero_alt = crew_page_hero(units)
    hero_img = render_img(hero_alt, rel(0, hero_path), eager=True, extra_class="hero-photo")
    as_of = availability.get("asOf", "")
    as_of_text = f"Availability as of {pretty_date(as_of)}" if as_of else "Availability"
    main = f"""  <section class="hero">
    {hero_img}
    <div class="hero-scrim">
      <div class="wrap">
        <div class="hero-copy">
          <p class="eyebrow">{esc(city)}, {esc(state)}</p>
          <h1>Stays for Working Crews in {esc(city)}, {esc(state)}</h1>
          <p class="lead">Furnished apartments and townhouses in {esc(city)}, {esc(state)} are available for seasonal and contract workers. Weekly and monthly stays suit working crews who are in town for Port of Brownsville LNG projects, wind industry work, or a job near SpaceX Starbase at Boca Chica.</p>
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
    title = f"Stays for Working Crews in {city}, {state} | {config['siteName']}"
    description = (
        f"Furnished weekly and monthly rentals in {city}, {state} for working crews: "
        "Port of Brownsville LNG project workers, wind turbine techs, and contract workers "
        "near SpaceX Starbase at Boca Chica."
    )
    return render_document(
        0,
        "crews",
        config,
        year,
        title,
        description,
        absolute_url(config["baseUrl"], "working-crews.html"),
        main,
        [
            webpage_schema(config, title, description, "working-crews.html"),
            item_list_schema(config, furnished, name=f"Furnished units for working crews in {city}, {state}"),
        ],
        hero_path,
    )


def render_unit_page(config, unit, availability, year):
    info = availability_for(availability, unit["id"])
    photos = unit_photo_paths(unit["slug"])
    city_line = f"{unit['locality']}, {unit['region']}"
    airbnb = ""
    if unit.get("airbnbName"):
        airbnb = f'\n      <p class="airbnb">Also listed on Airbnb as {esc(unit["airbnbName"])}</p>'
    stay = ""
    if unit["id"] in FURNISHED_IDS:
        stay = f'\n      <p class="stay-note">{esc(FURNISHED_LINE)}</p>'
    if unit["id"] in COMMERCIAL_IDS:
        keyword_line = (
            "A small commercial space among Casper Rentals listings in Brownsville, TX, "
            "in the Rio Grande Valley."
        )
        meta_kind = "commercial suite"
    elif unit["property"] == "Champions":
        keyword_line = (
            "A townhouse on Champion Dr from Casper Rentals in Brownsville, TX, "
            "in the Rio Grande Valley."
        )
        meta_kind = "townhouse"
    else:
        keyword_line = (
            "A Brownsville TX rental from Casper Rentals in the Rio Grande Valley."
        )
        meta_kind = "rental unit"
    ask_href = rel(1, "contact.html?unit=" + quote(unit["id"]))
    main = f"""  <div class="wrap unit-layout">
{render_unit_media(unit, photos)}
    <div class="unit-details">
      <p class="eyebrow">{esc(unit["property"])}</p>
      <h1>{esc(unit["name"])}</h1>
      <p class="address">{esc(unit["address"])}</p>
      <p class="locality">{esc(city_line)}</p>
      <p class="description">{esc(unit["description"])}</p>
      <div class="info-panel">
        <p>{badge_html(unit["id"], info["status"])}</p>
        {next_open_html(unit["id"], info["nextOpenDate"])}
        <p class="rent">Rent: Contact us for pricing</p>{stay}{airbnb}
        <p class="fine">{esc(keyword_line)}</p>
        <div class="unit-actions">
          <a class="btn" href="{ask_href}">Ask about this unit</a>
        </div>
      </div>
      <p class="back-link"><a href="{rel(1, "units.html")}">All units</a></p>
    </div>
  </div>"""
    title = f"{unit['name']} - Rental in {unit['locality']}, {unit['region']} | {config['siteName']}"
    description = (
        f"See {unit['name']}, a {meta_kind} in {unit['locality']}, {unit['region']}. "
        f"Contact {config['siteName']} about this Brownsville TX rental."
    )
    return render_document(
        1,
        "units",
        config,
        year,
        title,
        description,
        absolute_url(config["baseUrl"], f"units/{unit['slug']}.html"),
        main,
        [unit_schema(config, unit, photos)],
        photos[0] if photos else None,
    )


def render_contact(config, units, year):
    city = config["city"]
    state = config["state"]
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
    main = f"""  <div class="wrap page-intro">
    <div class="contact-layout">
      <div class="contact-intro">
        <h1>Contact us about a Brownsville, {esc(state)} rental</h1>
        <p class="lead">Ask Casper Rentals about apartments in {esc(city)}, townhouses on Champion Dr, or small commercial suites at 4 Greenway Dr. Furnished weekly and monthly stays are available for working crews. We rent in {esc(city)}, {esc(state)}, in the Rio Grande Valley.</p>
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
    title = f"Contact Us - Rentals in {city}, {state} | {config['siteName']}"
    description = (
        f"Contact {config['siteName']} about a rental unit in {city}, {state}, "
        f"including a furnished weekly or monthly stay for a working crew. "
        f"Ask about Brownsville apartments and Brownsville TX rentals in the Rio Grande Valley."
    )
    return render_document(
        0,
        "contact",
        config,
        year,
        title,
        description,
        absolute_url(config["baseUrl"], "contact.html"),
        main,
    )


def render_404(config, year):
    city = config["city"]
    state = config["state"]
    main = f"""  <div class="wrap page-intro">
    <h1>Page not found</h1>
    <p>That page is not on the {esc(config["siteName"])} site. Browse {esc(city)}, {esc(state)} rentals from the home page or contact us about a unit.</p>
    <div class="cta-actions">
      <a class="btn" href="{rel(0, "index.html")}">Back to home</a>
      <a class="btn btn-secondary" href="{rel(0, "units.html")}">View units</a>
      <a class="btn btn-secondary" href="{rel(0, "contact.html")}">Contact us</a>
    </div>
  </div>"""
    title = f"Page Not Found - {city}, {state} | {config['siteName']}"
    description = (
        f"This page is not on the {config['siteName']} site. "
        f"Browse {city}, {state} rentals and contact us about a Brownsville TX rental."
    )
    return render_document(
        0,
        "",
        config,
        year,
        title,
        description,
        absolute_url(config["baseUrl"], "404.html"),
        main,
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
    availability = load_json(ROOT / "data" / "availability.json")
    if not isinstance(availability, dict) or "units" not in availability:
        sys.exit("error: data/availability.json must contain units")

    year = date.today().year
    write_text(ROOT / "index.html", render_home(config, units, availability, year))
    write_text(ROOT / "units.html", render_units_page(config, units, availability, year))
    write_text(ROOT / "working-crews.html", render_crews_page(config, units, availability, year))
    write_text(ROOT / "contact.html", render_contact(config, units, year))
    write_text(ROOT / "404.html", render_404(config, year))
    for unit in units:
        write_text(
            ROOT / "units" / f"{unit['slug']}.html",
            render_unit_page(config, unit, availability, year),
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
