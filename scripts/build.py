#!/usr/bin/env python3
"""Generate the Casper Rentals static site into docs/."""

import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
COMMERCIAL_IDS = {"GW-SA", "GW-SB", "GW-SC"}
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
        "intro": "Rental units on Champion Dr in Brownsville, Texas.",
    },
    "Aurora": {
        "anchor": "aurora",
        "title": "Aurora at Paredes Line Rd",
        "intro": "Rental units at Aurora on Paredes Line Rd in Brownsville, Texas.",
    },
}


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
    # Greenway commercial suites use Accommodation; other units are apartments.
    if unit["id"] in COMMERCIAL_IDS:
        return "Accommodation"
    return "Apartment"


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
    <a class="brand" href="{rel(depth, "index.html")}">{esc(site_name)}</a>
    <nav aria-label="Primary">
{nav}
    </nav>
  </div>
</header>"""


def render_footer(depth, config, year):
    contact = rel(depth, "contact.html")
    return f"""<footer class="site-footer">
  <div class="wrap">
    <p>{esc(config["siteName"])} - {esc(config["company"])} - {esc(config["city"])}, {esc(config["state"])}</p>
    <p>{year}</p>
    <p><a href="{contact}">Contact us</a></p>
  </div>
</footer>"""


def render_document(depth, current, config, year, title, description, canonical, main, structured=None):
    blocks = ""
    if structured:
        encoded = "\n".join(json_ld(block) for block in structured)
        blocks = f'\n<script type="application/ld+json">\n{encoded}\n</script>'
    image = absolute_url(config["baseUrl"], "assets/img/placeholder.svg")
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


def unit_schema(config, unit):
    return {
        "@context": "https://schema.org",
        "@type": schema_type(unit),
        "name": unit["name"],
        "description": unit["description"],
        "url": absolute_url(config["baseUrl"], f"units/{unit['slug']}.html"),
        "image": absolute_url(config["baseUrl"], "assets/img/placeholder.svg"),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": unit["address"],
            "addressLocality": unit["locality"],
            "addressRegion": unit["region"],
            "addressCountry": unit["country"],
        },
    }


def item_list_schema(config, units):
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
        "name": f"{config['siteName']} units in {config['city']}, {config['state']}",
        "itemListElement": elements,
    }


def render_home(config, units, availability, year):
    city = config["city"]
    state = config["state"]
    groups = []
    for unit in units:
        if not groups or groups[-1][0] != unit["property"]:
            groups.append((unit["property"], []))
        groups[-1][1].append(unit)

    sections = []
    for property_name, grouped in groups:
        meta = SECTION_META.get(
            property_name,
            {
                "anchor": "property-" + re.sub(r"[^a-z0-9]+", "-", property_name.lower()).strip("-"),
                "title": property_name,
                "intro": f"Rental units at {property_name} in {city}, {state}.",
            },
        )
        rows = []
        for unit in grouped:
            info = availability_for(availability, unit["id"])
            unit_href = rel(0, f"units/{unit['slug']}.html")
            ask_href = rel(0, f"contact.html?unit={unit['id']}")
            rows.append(
                "        <li class=\"home-unit\">\n"
                f"          <a href=\"{unit_href}\">{esc(unit['name'])}</a>\n"
                f"          {badge_html(unit['id'], info['status'])}\n"
                f"          <a href=\"{ask_href}\">Ask about this unit</a>\n"
                "        </li>"
            )
        property_href = rel(0, "units.html?property=" + property_name.replace(" ", "%20"))
        sections.append(
            f"""    <section class="property-block" id="{esc(meta["anchor"])}">
      <h2>{esc(meta["title"])}</h2>
      <p>{esc(meta["intro"])}</p>
      <ul class="home-units">
{chr(10).join(rows)}
      </ul>
      <p><a class="btn btn-secondary" href="{property_href}">View these units</a></p>
    </section>"""
        )

    as_of = availability.get("asOf", "")
    as_of_text = f"Availability as of {pretty_date(as_of)}" if as_of else "Availability"
    main = f"""  <section class="hero">
    <div class="wrap">
      <h1>Rentals in {esc(city)}, {esc(state)}</h1>
      <p>Casper Rentals offers apartments, townhouse-style units, and small commercial suites in {esc(city)}, Texas. Look through Brownsville apartments and other Brownsville TX rentals in the Rio Grande Valley, then contact us about a unit.</p>
      <div class="hero-actions">
        <a class="btn" href="{rel(0, "units.html?available=1")}">See available units</a>
        <a class="btn btn-secondary" href="{rel(0, "contact.html")}">Contact us</a>
      </div>
    </div>
  </section>
  <div class="wrap section">
    <p class="as-of" data-as-of>{esc(as_of_text)}</p>
{chr(10).join(sections)}
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
        f"{config['siteName']} offers apartments, townhouse-style units, and small commercial "
        f"suites in {city}, {state}. Contact us about Brownsville TX rentals in the Rio Grande Valley."
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
    )


def render_units_page(config, units, availability, year):
    city = config["city"]
    state = config["state"]
    cards = []
    for unit in units:
        info = availability_for(availability, unit["id"])
        cards.append(
            f"""      <article class="card" data-unit-card data-unit-id="{esc(unit["id"])}" data-property="{esc(unit["property"])}" data-status="{esc(info["status"])}">
        <a href="{rel(0, f"units/{unit['slug']}.html")}">
          <img src="{rel(0, "assets/img/placeholder.svg")}" alt="{esc("Photos coming soon for " + unit["name"])}" width="800" height="500">
        </a>
        <div class="card-body">
          <h2><a href="{rel(0, f"units/{unit['slug']}.html")}">{esc(unit["name"])}</a></h2>
          <p class="property-name">{esc(unit["property"])}</p>
          <p class="locality">{esc(unit["locality"])}, {esc(unit["region"])}</p>
          <p>{badge_html(unit["id"], info["status"])}</p>
          <p class="rent">Rent: Contact us</p>
          <div class="card-actions">
            <a class="btn" href="{rel(0, f"contact.html?unit={unit['id']}")}">Ask about this unit</a>
          </div>
        </div>
      </article>"""
        )
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
    <p class="lead">Every Casper Rentals listing in {esc(city)} is shown here, including Brownsville apartments at 4 Greenway Dr, units on Champion Dr, and Aurora at Paredes Line Rd. These are Brownsville TX rentals in the Rio Grande Valley. Rent: Contact us.</p>
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
        f"Browse Casper Rentals units in {city}, {state}. See Brownsville apartments and "
        f"commercial suites, check availability, and contact us about Brownsville TX rentals."
    )
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
    )


def render_unit_page(config, unit, availability, year):
    info = availability_for(availability, unit["id"])
    city_line = f"{unit['locality']}, {unit['region']}"
    airbnb = ""
    if unit.get("airbnbName"):
        airbnb = f'\n      <p class="airbnb">Also listed on Airbnb as {esc(unit["airbnbName"])}</p>'
    if unit["id"] in COMMERCIAL_IDS:
        keyword_line = (
            "A small commercial space among Casper Rentals listings in Brownsville, TX, "
            "in the Rio Grande Valley."
        )
        meta_kind = "commercial suite"
    else:
        keyword_line = (
            "A Brownsville TX rental from Casper Rentals in the Rio Grande Valley."
        )
        meta_kind = "rental unit"
    main = f"""  <div class="wrap unit-layout">
    <div class="unit-photo">
      <img src="{rel(1, "assets/img/placeholder.svg")}" alt="{esc("Photos coming soon for " + unit["name"])}" width="800" height="500">
    </div>
    <div class="unit-details">
      <h1>{esc(unit["name"])}</h1>
      <p class="property-name">{esc(unit["property"])}</p>
      <p class="address">{esc(unit["address"])}</p>
      <p class="locality">{esc(city_line)}</p>
      <p class="description">{esc(unit["description"])}</p>
      <p>{badge_html(unit["id"], info["status"])}</p>
      {next_open_html(unit["id"], info["nextOpenDate"])}
      <p class="rent">Rent: Contact us for pricing</p>{airbnb}
      <p class="fine">{esc(keyword_line)}</p>
      <div class="unit-actions">
        <a class="btn" href="{rel(1, f"contact.html?unit={unit['id']}")}">Ask about this unit</a>
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
        [unit_schema(config, unit)],
    )


def render_contact(config, units, year):
    city = config["city"]
    state = config["state"]
    endpoint = config["formspreeEndpoint"]
    placeholder = "PLACEHOLDER" in endpoint
    note = ""
    if placeholder:
        note = (
            '    <p class="notice" id="form-setup-note" role="status" tabindex="-1">'
            "The contact form is being set up. Check back soon.</p>\n"
        )
    options = ['          <option value="">Not sure / any unit</option>']
    for unit in units:
        options.append(
            f'          <option value="{esc(unit["id"])}">{esc(unit["name"])}</option>'
        )
    main = f"""  <div class="wrap page-intro">
    <h1>Contact us about a Brownsville, {esc(state)} rental</h1>
    <p class="lead">Ask Casper Rentals about apartments, townhouse-style units, or a small commercial suite. We rent in {esc(city)}, {esc(state)}, in the Rio Grande Valley.</p>
{note}    <form id="contact-form" class="form" method="POST" action="{esc(endpoint)}" accept-charset="UTF-8">
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
      <label for="move-in">Desired move-in date (optional)</label>
      <input id="move-in" name="move_in" type="date">
      <label for="message">Message <span class="req">(required)</span></label>
      <textarea id="message" name="message" rows="6" required></textarea>
      <p class="card-actions"><button class="btn" type="submit">Contact us</button></p>
    </form>
  </div>"""
    title = f"Contact Us - Rentals in {city}, {state} | {config['siteName']}"
    description = (
        f"Contact {config['siteName']} about a rental unit in {city}, {state}. "
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
    paths = ["/", "units.html", "contact.html"]
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
    return f"User-agent: *\nAllow: /\n\nSitemap: {sitemap}\n"


def copy_assets():
    source = ROOT / "assets"
    target = DOCS / "assets"
    if not source.is_dir():
        sys.exit("error: assets/ is missing")
    shutil.copytree(source, target)


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

    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)
    copy_assets()
    data_dir = DOCS / "data"
    data_dir.mkdir()
    shutil.copyfile(ROOT / "data" / "availability.json", data_dir / "availability.json")

    year = date.today().year
    write_text(DOCS / "index.html", render_home(config, units, availability, year))
    write_text(DOCS / "units.html", render_units_page(config, units, availability, year))
    write_text(DOCS / "contact.html", render_contact(config, units, year))
    write_text(DOCS / "404.html", render_404(config, year))
    for unit in units:
        write_text(
            DOCS / "units" / f"{unit['slug']}.html",
            render_unit_page(config, unit, availability, year),
        )
    write_text(DOCS / "sitemap.xml", render_sitemap(config, units, availability))
    write_text(DOCS / "robots.txt", render_robots(config))
    write_text(DOCS / ".nojekyll", "")

    page_count = 4 + len(units)
    print(f"Built {page_count} HTML pages, sitemap, and robots into docs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
