"""
Fetches the live IPO GMP table from investorgain.com.

The table is rendered client-side (DataTables + AJAX), so we use Playwright
(a real headless browser) instead of a plain HTTP request - a plain request
just returns "Loading..." with no data.

Returns a list of dicts like:
    {
        "name": "Example Company Ltd",
        "category": "mainboard",   # or "sme"
        "price": 212.0,
        "gmp_rupees": 17.0,
        "gmp_percent": 8.02,
        "est_listing": 229.0,
        "open_date": "12-Aug-2026",
        "close_date": "14-Aug-2026",
        "status": "open",          # open / upcoming / closed / listed, if detectable
        "raw": {...}                # original cell text, for debugging
    }

NOTE: investorgain.com can change its markup at any time. If this stops
returning rows, run `python run.py --debug` (see bottom of file) to dump the
raw header/row text and adjust COLUMN_ALIASES below.
"""

import datetime
import re

from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright

MAINBOARD_URL = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
SME_URL = "https://www.investorgain.com/report/live-ipo-gmp/331/sme/"

# The site glues a status badge (Open/Closed/Upcoming/Listed, sometimes with
# a listing price/gain like "L@72.00 (35.85%)") directly onto the name cell
# with no space, e.g. "Ardee Industries IPOL@72.00 (35.85%)". Trim
# everything from just after the first "IPO"/"SME" onward.
_NAME_CUTOFF = re.compile(r"^(.*?(?:IPO|SME))")


def _clean_name(text):
    if not text:
        return text
    text = text.strip()
    match = _NAME_CUTOFF.match(text)
    return match.group(1).strip() if match else text


def _parse_date(text):
    """Parse dates like '12-Aug-25' or '12-Aug-2026'. Returns a date or None."""
    if not text:
        return None
    try:
        return dateparser.parse(text, dayfirst=True, fuzzy=True).date()
    except (ValueError, OverflowError, TypeError):
        return None


def _days_from_today(d):
    if d is None:
        return None
    return (d - datetime.date.today()).days

# Maps our internal field name -> substrings that might appear in the
# site's column headers (checked case-insensitively). Order matters where
# ambiguous - more specific/exact aliases should come first since we check
# fields in dict order and skip a field once it's already mapped.
COLUMN_ALIASES = {
    "name": ["name"],
    "price": ["price"],
    "gmp_rupees": ["gmp"],
    "open_date": ["open"],
    "close_date": ["close"],
    "est_listing": ["listing"],  # NOTE: also matches "LISTING" header; fine, no other column contains "listing"
}
# investorgain's table has no separate GMP% column - it's computed from
# gmp_rupees / price, same formula the site itself uses.


def _parse_number(text):
    """Extract a number from text. If a range like '115-121' appears,
    take the LAST number found (the upper bound), which is more useful
    for filtering than a garbled concatenation of both bounds."""
    if not text:
        return None
    text = text.replace(",", "")
    matches = re.findall(r"[-+]?\d*\.?\d+", text)
    if not matches:
        return None
    try:
        return float(matches[-1])
    except ValueError:
        return None


def _map_headers(header_cells):
    """Given a list of header texts, return {field_name: column_index}."""
    mapping = {}
    for idx, header_text in enumerate(header_cells):
        h = header_text.strip().lower()
        for field, aliases in COLUMN_ALIASES.items():
            if field in mapping:
                continue
            if any(alias in h for alias in aliases):
                mapping[field] = idx
    return mapping


def _scrape_url(page, url, category, debug=False):
    page.goto(url, wait_until="networkidle", timeout=45000)
    # The results table is populated by JS after load; give it a moment and
    # wait for at least one row OR the "No data available" placeholder.
    page.wait_for_timeout(3000)

    table = page.query_selector("table")
    if table is None:
        if debug:
            print(f"[debug] no <table> found on {url}")
        return []

    header_cells = [th.inner_text() for th in table.query_selector_all("thead th")]
    if debug:
        print(f"[debug] headers on {url}: {header_cells}")

    col_map = _map_headers(header_cells)
    if debug:
        print(f"[debug] column map: {col_map}")

    rows = table.query_selector_all("tbody tr")
    results = []
    for row in rows:
        cells = row.query_selector_all("td")
        if not cells:
            continue
        texts = [c.inner_text().strip() for c in cells]
        if len(texts) < 2:
            continue
        # Skip the "No data available" placeholder row.
        if len(texts) == 1 and "no data" in texts[0].lower():
            continue

        def get(field):
            idx = col_map.get(field)
            if idx is None or idx >= len(texts):
                return None
            return texts[idx]

        name = get("name")
        if not name:
            continue

        price = _parse_number(get("price"))
        gmp_rupees = _parse_number(get("gmp_rupees"))
        gmp_percent = None
        if price and gmp_rupees is not None and price != 0:
            gmp_percent = round((gmp_rupees / price) * 100, 2)

        open_date_text = get("open_date")
        close_date_text = get("close_date")
        open_dt = _parse_date(open_date_text)
        close_dt = _parse_date(close_date_text)

        item = {
            "name": _clean_name(name),
            "category": category,
            "price": price,
            "gmp_rupees": gmp_rupees,
            "gmp_percent": gmp_percent,
            "est_listing": _parse_number(get("est_listing")),
            "open_date": open_date_text,
            "close_date": close_date_text,
            "days_until_open": _days_from_today(open_dt),
            "days_until_close": _days_from_today(close_dt),
            "raw": dict(zip(header_cells, texts)) if header_cells else texts,
        }
        results.append(item)

        if debug:
            print(f"[debug] row: name={item['name']!r} price={price} "
                  f"gmp_rupees={gmp_rupees} gmp_percent={gmp_percent} "
                  f"days_until_open={item['days_until_open']} "
                  f"days_until_close={item['days_until_close']}")

    return results


def fetch(debug=False):
    """Fetch both mainboard and SME IPO GMP tables. Returns a combined list."""
    all_items = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ))
        all_items += _scrape_url(page, MAINBOARD_URL, "mainboard", debug=debug)
        all_items += _scrape_url(page, SME_URL, "sme", debug=debug)
        browser.close()
    return all_items


if __name__ == "__main__":
    import json
    import sys
    items = fetch(debug="--debug" in sys.argv)
    print(json.dumps(items, indent=2))