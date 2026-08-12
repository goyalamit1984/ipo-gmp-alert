"""
Shared scraper for chittorgarh.com's report pages (OFS, Rights Issue,
Buyback). These use the same JS-rendered DataTables pattern as
investorgain.com's IPO GMP page, so this reuses that approach: Playwright
to render, header-keyword matching to find columns.

NOTE: column headers for Rights Issue and Buyback haven't been confirmed
against a live render yet (OFS has - see ofs.py's custom aliases). Run
`python run.py --debug` and check the [debug] headers / column map lines -
the aliases may need tweaking, same as ipo_gmp.py's calibration.
"""

import datetime
import re

from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright

# Only matches actual day-month(-year) patterns, e.g. "12-Aug-25" or
# "12 Aug 2026" - deliberately strict so junk text like "-" or "Closed"
# never gets fuzzy-matched into a nonsense date.
_DATE_PATTERN = re.compile(r"\d{1,2}[-\s][A-Za-z]{3,9}(?:[-\s]\d{2,4})?")

# Broad aliases since not all pages' headers are confirmed yet. "name" is
# intentionally NOT matched by generic words like "issue" alone to avoid
# grabbing the wrong column.
DEFAULT_COLUMN_ALIASES = {
    "name": ["company", "name"],
    "open_date": ["open"],
    "close_date": ["close"],
    "price": ["price"],
    # Fallback for pages with ONE combined date column instead of separate
    # open/close columns (e.g. OFS's "Offer Date"). Only used if neither
    # open_date nor close_date matched anything above.
    "date_range": ["date"],
}


def _parse_number(text):
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


def _parse_date(text):
    """Parse a date like '12-Aug-25' out of text. Only matches text that
    actually looks like a day-month(-year) pattern - never fuzzy-guesses
    a date out of unrelated text like '-' or 'Closed'."""
    if not text:
        return None
    match = _DATE_PATTERN.search(text)
    if not match:
        return None
    try:
        return dateparser.parse(match.group(0), dayfirst=True, fuzzy=False).date()
    except (ValueError, OverflowError, TypeError):
        return None


def _days_from_today(d):
    if d is None:
        return None
    return (d - datetime.date.today()).days


def _map_headers(header_cells, aliases):
    mapping = {}
    for idx, header_text in enumerate(header_cells):
        h = header_text.strip().lower()
        for field, field_aliases in aliases.items():
            if field in mapping:
                continue
            if any(a in h for a in field_aliases):
                mapping[field] = idx
    return mapping


def fetch_table(url, category, debug=False, column_aliases=None):
    """Scrape one chittorgarh.com report table. Returns list of item dicts."""
    aliases = column_aliases or DEFAULT_COLUMN_ALIASES
    items = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ))
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)

        table = page.query_selector("table")
        if table is None:
            if debug:
                print(f"[debug] no <table> found on {url}")
            browser.close()
            return []

        header_cells = [th.inner_text() for th in table.query_selector_all("thead th")]
        if debug:
            print(f"[debug] headers on {url}: {header_cells}")

        col_map = _map_headers(header_cells, aliases)
        if debug:
            print(f"[debug] column map: {col_map}")

        has_separate_dates = "open_date" in col_map or "close_date" in col_map

        rows = table.query_selector_all("tbody tr")
        for row in rows:
            cells = row.query_selector_all("td")
            if not cells:
                continue
            texts = [c.inner_text().strip() for c in cells]
            if len(texts) < 2:
                continue
            if len(texts) == 1 and "no data" in texts[0].lower():
                continue
            if any("total records: 0" in t.lower() for t in texts):
                continue

            def get(field, texts=texts):
                idx = col_map.get(field)
                if idx is None or idx >= len(texts):
                    return None
                return texts[idx]

            name = get("name")
            if not name:
                continue

            if has_separate_dates:
                open_date_text = get("open_date")
                close_date_text = get("close_date")
            else:
                # Single combined date column (e.g. OFS's "Offer Date",
                # which spans a 2-day T/T+1 window). Pull out every
                # date-like substring found in that cell; use the first as
                # open, the last as close (same value if only one found).
                range_text = get("date_range")
                found = _DATE_PATTERN.findall(range_text) if range_text else []
                open_date_text = found[0] if found else None
                close_date_text = found[-1] if found else None

            open_dt = _parse_date(open_date_text)
            close_dt = _parse_date(close_date_text)

            item = {
                "name": name.strip(),
                "category": category,
                "price": _parse_number(get("price")),
                "open_date": open_date_text,
                "close_date": close_date_text,
                "days_until_open": _days_from_today(open_dt),
                "days_until_close": _days_from_today(close_dt),
                "raw": dict(zip(header_cells, texts)) if header_cells else texts,
            }
            items.append(item)

            if debug:
                print(f"[debug] row: name={item['name']!r} "
                      f"open_date={open_date_text!r} close_date={close_date_text!r} "
                      f"days_until_open={item['days_until_open']} "
                      f"days_until_close={item['days_until_close']}")

        browser.close()

    return items
