"""
Shared scraper for chittorgarh.com's report pages (OFS, Rights Issue,
Buyback). These use the same JS-rendered DataTables pattern as
investorgain.com's IPO GMP page, so this reuses that approach: Playwright
to render, header-keyword matching to find columns, since exact column
names aren't confirmed until a live --debug run against the real page.

NOTE: column headers for these pages haven't been verified against a live
render yet (unlike ipo_gmp.py, which was calibrated against real debug
output). Run `python run.py --debug` after first deploying and check the
[debug] headers / column map lines - the aliases below may need tweaking,
exactly like ipo_gmp.py's COLUMN_ALIASES did on first real run.
"""

import datetime
import re

from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright

# Broad aliases since we haven't confirmed exact header text yet. "name" is
# intentionally NOT matched by generic words like "issue" or "company" alone
# to avoid grabbing the wrong column - refine after seeing real headers.
DEFAULT_COLUMN_ALIASES = {
    "name": ["company", "name"],
    "open_date": ["open"],
    "close_date": ["close"],
    "price": ["price"],
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

            open_date_text = get("open_date")
            close_date_text = get("close_date")
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
