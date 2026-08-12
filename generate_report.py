"""
Generates docs/index.html - the public dashboard showing IPO, OFS, Rights
Issue, Buyback (each with "today/tomorrow" highlighted, "upcoming" below)
and recent news for your stock holdings.

Run this after run.py (or standalone) - it re-fetches fresh data itself
rather than reusing run.py's alert-filtered results, since the dashboard
shows a broader view (everything upcoming, not just items that crossed an
alert threshold).

GitHub Pages should be configured to serve from the /docs folder on main.
"""

import datetime
import html
import json
import os

from fetchers import ipo_gmp, ofs, rights_issue, buyback
from news import fetch_all_holdings_news

OUTPUT_PATH = "docs/index.html"
HOLDINGS_PATH = "holdings.json"


def load_holdings():
    if not os.path.exists(HOLDINGS_PATH):
        return []
    with open(HOLDINGS_PATH) as f:
        return json.load(f)


def sort_key(item):
    """Days until the relevant date - close if known, else open. Items
    with neither sort last."""
    days = item.get("days_until_close")
    if days is None:
        days = item.get("days_until_open")
    return days if days is not None else 999999


def bucket(item):
    """'today_tomorrow', 'upcoming', or None (already closed / no date)."""
    days = item.get("days_until_close")
    if days is None:
        days = item.get("days_until_open")
    if days is None or days < 0:
        return None
    return "today_tomorrow" if days <= 1 else "upcoming"


def split_buckets(items):
    today_tomorrow, upcoming = [], []
    for item in items:
        b = bucket(item)
        if b == "today_tomorrow":
            today_tomorrow.append(item)
        elif b == "upcoming":
            upcoming.append(item)
    today_tomorrow.sort(key=sort_key)
    upcoming.sort(key=sort_key)
    return today_tomorrow, upcoming


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def render_item_row(item, extra_fields=()):
    close = esc(item.get("close_date") or item.get("open_date") or "TBA")
    price = item.get("price")
    price_str = f"₹{price:g}" if price is not None else ""
    extras = " · ".join(esc(item.get(f)) for f in extra_fields if item.get(f) is not None)
    return f"""
    <div class="item-row">
      <div class="item-name">{esc(item['name'])}</div>
      <div class="item-meta">{close}{' · ' + price_str if price_str else ''}{' · ' + extras if extras else ''}</div>
    </div>"""


def render_section(title, items, extra_fields=()):
    today_tomorrow, upcoming = split_buckets(items)

    if not today_tomorrow and not upcoming:
        body = '<p class="empty">Nothing upcoming right now.</p>'
    else:
        body = ""
        if today_tomorrow:
            body += '<h3 class="subheading">🔥 Today / Tomorrow</h3>'
            body += "".join(render_item_row(i, extra_fields) for i in today_tomorrow)
        if upcoming:
            body += '<h3 class="subheading">Upcoming</h3>'
            body += "".join(render_item_row(i, extra_fields) for i in upcoming)

    return f"""
    <section class="card">
      <h2>{esc(title)}</h2>
      {body}
    </section>"""


def render_news_section(holdings_news):
    if not holdings_news:
        return """
    <section class="card">
      <h2>📰 Holdings News</h2>
      <p class="empty">Add company names to holdings.json to see news here.</p>
    </section>"""

    body = ""
    for name, items in holdings_news.items():
        body += f'<h3 class="subheading">{esc(name)}</h3>'
        if not items:
            body += '<p class="empty">No recent news found.</p>'
        else:
            for n in items:
                body += f"""
      <div class="news-row">
        <a href="{esc(n['link'])}" target="_blank" rel="noopener">{esc(n['title'])}</a>
        <div class="item-meta">{esc(n.get('source') or '')}</div>
      </div>"""

    return f"""
    <section class="card">
      <h2>📰 Holdings News</h2>
      {body}
    </section>"""


CSS = """
:root { color-scheme: light dark; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px 60px;
  background: #fafafa;
  color: #1a1a1a;
}
@media (prefers-color-scheme: dark) {
  body { background: #16181c; color: #e6e6e6; }
  .card { background: #1f2227 !important; border-color: #2c2f36 !important; }
  .item-meta { color: #999 !important; }
  a { color: #7cb3ff !important; }
}
h1 { font-size: 1.5rem; margin-bottom: 4px; }
.updated { color: #777; font-size: 0.85rem; margin-bottom: 24px; }
.card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
}
.card h2 { margin: 0 0 8px; font-size: 1.15rem; }
.subheading { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em;
  color: #888; margin: 14px 0 6px; }
.item-row, .news-row { padding: 8px 0; border-top: 1px solid #eee; }
.item-row:first-of-type, .news-row:first-of-type { border-top: none; }
.item-name { font-weight: 600; font-size: 0.95rem; }
.item-meta { font-size: 0.82rem; color: #777; margin-top: 2px; }
.news-row a { font-size: 0.92rem; text-decoration: none; color: #0645ad; }
.news-row a:hover { text-decoration: underline; }
.empty { color: #999; font-size: 0.88rem; font-style: italic; }
"""


def build_html(sections_html, generated_at):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Market Alerts Dashboard</title>
<style>{CSS}</style>
</head>
<body>
  <h1>Market Alerts Dashboard</h1>
  <div class="updated">Last updated: {esc(generated_at)}</div>
  {sections_html}
</body>
</html>"""


def generate(debug=False):
    all_ipo = ipo_gmp.fetch(debug=debug)
    mainboard = [i for i in all_ipo if i["category"] == "mainboard"]
    sme = [i for i in all_ipo if i["category"] == "sme"]

    ofs_items = ofs.fetch(debug=debug)
    rights_items = rights_issue.fetch(debug=debug)
    buyback_items = buyback.fetch(debug=debug)

    holdings = load_holdings()
    holdings_news = fetch_all_holdings_news(holdings) if holdings else {}

    sections = ""
    sections += render_section("📊 Mainboard IPO", mainboard, extra_fields=("gmp_percent",))
    sections += render_section("🏷️ SME IPO", sme, extra_fields=("gmp_percent",))
    sections += render_section("📄 Offer for Sale (OFS)", ofs_items)
    sections += render_section("📄 Rights Issue", rights_items)
    sections += render_section("📄 Buyback", buyback_items)
    sections += render_news_section(holdings_news)

    generated_at = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p IST")
    output = build_html(sections, generated_at)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output)

    # Tells GitHub Pages to skip its default Jekyll processing - we're
    # serving plain static HTML, and Jekyll's default theme errors out
    # trying to process assets that don't exist in this setup.
    nojekyll_path = os.path.join(os.path.dirname(OUTPUT_PATH), ".nojekyll")
    open(nojekyll_path, "a").close()

    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    import sys
    generate(debug="--debug" in sys.argv)
