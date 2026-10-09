#!/usr/bin/env python3
"""Build data/availability.json from a derived unit-calendar text file.

Usage:
    python3 scripts/update_availability.py <input.txt> [--as-of YYYY-MM-DD]

Input lines look like "unit_id | status | next_open_date". The date may be
blank. Lines starting with # are ignored. Ids listed in hiddenUnits in
site.config.json are never written. This script writes only
data/availability.json.
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNITS_PATH = ROOT / "data" / "units.json"
CONFIG_PATH = ROOT / "site.config.json"
OUTPUT_PATH = ROOT / "data" / "availability.json"
SOURCE = "Casper Master Unit Calendar (derived)"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
AVAILABLE_FROM_RE = re.compile(r"Available from (\d{4}-\d{2}-\d{2})")
PLAIN_STATUSES = {"Available", "Occupied", "Contact us"}


def parse_date(value):
    if not value or not DATE_RE.fullmatch(value):
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


def canonical_status(status):
    if status in PLAIN_STATUSES:
        return status
    match = AVAILABLE_FROM_RE.fullmatch(status)
    if match and parse_date(match.group(1)):
        return status
    return None


def load_units():
    try:
        payload = json.loads(UNITS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"error: missing {UNITS_PATH}")
    except json.JSONDecodeError as exc:
        sys.exit(f"error: {UNITS_PATH} is not valid JSON: {exc}")
    if not isinstance(payload, list):
        sys.exit("error: data/units.json must be a list")
    ids = []
    seen = set()
    for unit in payload:
        if not isinstance(unit, dict) or "id" not in unit:
            sys.exit("error: every unit needs an id")
        unit_id = unit["id"]
        if unit_id in seen:
            sys.exit(f"error: duplicate id in units.json: {unit_id}")
        seen.add(unit_id)
        ids.append(unit_id)
    return ids


def load_hidden_ids(known_ids):
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"error: missing {CONFIG_PATH}")
    except json.JSONDecodeError as exc:
        sys.exit(f"error: {CONFIG_PATH} is not valid JSON: {exc}")
    if not isinstance(payload, dict):
        sys.exit("error: site.config.json must be an object")
    raw = payload.get("hiddenUnits", [])
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        sys.exit("error: site.config.json hiddenUnits must be a list of unit ids")
    hidden = []
    for item in raw:
        if not isinstance(item, str) or not item:
            sys.exit("error: site.config.json hiddenUnits must be a list of unit ids")
        if item not in known_ids:
            sys.exit(f"error: hiddenUnits id {item} is not in data/units.json")
        if item not in hidden:
            hidden.append(item)
    return hidden


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="update_availability.py",
        description="Write data/availability.json from a derived calendar text file.",
    )
    parser.add_argument("input_txt", help="Path to the derived availability text file")
    parser.add_argument(
        "--as-of",
        dest="as_of",
        default=date.today().isoformat(),
        help="As-of date YYYY-MM-DD (default: today)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    as_of = parse_date(args.as_of)
    if not as_of:
        sys.exit("error: --as-of must be a real date in YYYY-MM-DD form")

    input_path = Path(args.input_txt)
    if not input_path.is_file():
        sys.exit(f"error: input file not found: {input_path}")

    known_ids = load_units()
    known = set(known_ids)
    hidden_ids = set(load_hidden_ids(known))
    parsed = {}
    ignored_hidden = []

    for line_number, raw_line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in raw_line.split("|")]
        if len(parts) < 2 or not parts[0]:
            print(f"Warning: skipped malformed line {line_number}: {raw_line.strip()}")
            continue
        unit_id = parts[0]
        if unit_id in hidden_ids:
            if unit_id not in ignored_hidden:
                ignored_hidden.append(unit_id)
            continue
        if len(parts) > 3:
            print(f"Warning: extra fields on line {line_number} ignored for {parts[0]}")
        status_raw = parts[1]
        next_raw = parts[2] if len(parts) > 2 else ""
        if unit_id not in known:
            print(f"Warning: unknown unit id ignored: {unit_id}")
            continue
        if unit_id in parsed:
            print(f"Warning: duplicate unit id {unit_id}; using the last value")

        status = canonical_status(status_raw)
        if status is None:
            print(f"Warning: invalid status for {unit_id}: {status_raw!r} -> Contact us")
            status = "Contact us"

        if next_raw == "":
            next_open = None
        else:
            next_open = parse_date(next_raw)
            if next_open is None:
                print(f"Warning: invalid next open date for {unit_id}: {next_raw!r} -> null")

        parsed[unit_id] = {"status": status, "nextOpenDate": next_open}

    if ignored_hidden:
        print("Info: ignored hidden units: " + ", ".join(ignored_hidden))

    missing = [
        unit_id for unit_id in known_ids if unit_id not in parsed and unit_id not in hidden_ids
    ]
    if missing:
        print("Warning: units missing from input, set to Contact us: " + ", ".join(missing))

    units_out = {}
    for unit_id in known_ids:
        if unit_id in hidden_ids:
            continue
        units_out[unit_id] = parsed.get(unit_id, {"status": "Contact us", "nextOpenDate": None})

    payload = {
        "asOf": as_of,
        "source": SOURCE,
        "units": units_out,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote data/availability.json (as of {as_of}, {len(units_out)} units)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
