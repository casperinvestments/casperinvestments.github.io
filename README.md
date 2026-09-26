# Casper Rentals

Static website for Casper Rentals, the public name of Casper Investments LLC, a rental company in Brownsville, TX. The site lists apartments, townhouse-style units, and small commercial suites and asks visitors to contact the company about a unit.

It is plain HTML, CSS, and a small vanilla JavaScript file. Python scripts in `scripts/` use the standard library only. The generated site lives in `docs/` and is published as the GitHub user-site repo [casperinvestments/casperinvestments.github.io](https://github.com/casperinvestments/casperinvestments.github.io) at https://casperinvestments.github.io/ . GitHub Pages settings should publish from the `docs/` folder on the default branch. For a user site, the owner may instead choose to publish `docs/` via Pages settings "Deploy from a branch" -> /docs. Internal links and asset paths stay relative so they work both at the domain root and in local preview.

There is no custom domain, no npm build, and no paid hosting. Photos are placeholders until real ones are available.

## Build

From the repository root:

```bash
python3 scripts/build.py
```

The script reads `site.config.json`, `data/units.json`, and `data/availability.json`, then rewrites `docs/`. Re-running it is safe. It only replaces files inside `docs/`. Edit styles and scripts in `assets/`, then build again. Do not hand-edit `docs/`.

## Preview locally

```bash
cd docs && python3 -m http.server 8000
```

Open http://localhost:8000/

## Daily availability sync

Availability text on the site comes from `data/availability.json`. Produce the derived input outside this repository (do not commit the upstream calendar export). Each line looks like:

```text
unit_id | status | next_open_date
```

The date may be blank. Lines that start with `#` are ignored.

1. Produce the derived input text file outside the repo.
2. `python3 scripts/update_availability.py /path/to/availability-input.txt`
3. `python3 scripts/build.py`
4. Commit only `data/availability.json` and `docs/`.

`update_availability.py` checks each id against `data/units.json`. A unit missing from the input becomes status `Contact us` with no next open date, and the script prints a warning. Unknown ids are ignored with a warning. Allowed statuses are `Available`, `Available from YYYY-MM-DD`, `Occupied`, and `Contact us`. Anything else is stored as `Contact us` with a warning. Optional `--as-of YYYY-MM-DD` sets the as-of date (the default is today). The script writes only `data/availability.json`.

The HTML is static, so the status you see is the status at build time. `assets/js/main.js` also fetches `data/availability.json` (unit pages use `../data/availability.json`) and refreshes each `data-unit-status` badge. Replacing `docs/data/availability.json` alone updates those badges on the next page load. A full build still refreshes titles, schema, and the sitemap lastmod date.

## Formspree endpoint

The Formspree endpoint is set in `site.config.json` and forwards submissions to the owner's inbox configured in Formspree. Rebuild after changing that value. While `formspreeEndpoint` contains `PLACEHOLDER`, the contact page shows “The contact form is being set up. Check back soon.” and JavaScript blocks the submit so nothing is posted to the placeholder address.

`contactEmailNote` in the same file is a reminder about that Formspree forwarding. The site does not publish an email address, phone number, or company mailing address.

## Canonical base URL

`baseUrl` in `site.config.json` is `https://casperinvestments.github.io` (no trailing slash). The site is served at the domain root, https://casperinvestments.github.io/ . Sitemap URLs, the robots.txt Sitemap line, canonical links, Open Graph URLs, and JSON-LD `url` and `image` values use that absolute base. Page-to-page links and assets stay relative.

## Photo policy

Use only public Airbnb listing photos, or image files the owner sends later. Until then, every unit uses `assets/img/placeholder.svg` (“Photos coming soon”). Do not add other photos to the repo.

## Rent

Every unit shows rent as “Contact us”. Do not add prices or other money amounts to the site.
