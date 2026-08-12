"""
Fetches recent news headlines for your stock holdings via Google News RSS.
No API key needed - it's a public RSS feed, just an XML parse over HTTP.

NOTE: this only sends the company NAME to Google in the search query -
never share counts or values. holdings.json should only ever contain names.
"""

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def fetch_news_for_holding(name, max_items=5, days=3):
    query = urllib.parse.quote(f"{name} stock")
    url = (
        f"https://news.google.com/rss/search?q={query}+when:{days}d"
        f"&hl=en-IN&gl=IN&ceid=IN:en"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)
    except Exception as e:
        print(f"[news] failed to fetch news for {name!r}: {e}")
        return []

    items = []
    for item in root.findall(".//item")[:max_items]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub_date = item.findtext("pubDate") or ""
        source_el = item.find("source")
        source = source_el.text if source_el is not None else None
        items.append({
            "title": title,
            "link": link,
            "pub_date": pub_date,
            "source": source,
        })
    return items


def fetch_all_holdings_news(holdings, max_items_per_holding=5):
    """holdings: list of company name strings. Returns {name: [news items]}."""
    result = {}
    for name in holdings:
        result[name] = fetch_news_for_holding(name, max_items=max_items_per_holding)
    return result
