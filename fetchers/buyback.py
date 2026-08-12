"""Fetches the live Buyback list from chittorgarh.com."""

from fetchers._chittorgarh_common import fetch_table

URL = "https://www.chittorgarh.com/report/latest-buyback-issues-in-india/80/tender-offer-buyback/"

# Confirmed via --debug run against the live page.
COLUMN_ALIASES = {
    "name": ["company name", "company"],
    "open_date": ["issue open"],
    "close_date": ["issue close"],
    "price": ["buyback price"],
}


def fetch(debug=False):
    return fetch_table(URL, "buyback", debug=debug, column_aliases=COLUMN_ALIASES)


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(fetch(debug="--debug" in sys.argv), indent=2))
