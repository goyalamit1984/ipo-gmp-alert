"""Fetches the live Offer For Sale (OFS) list from chittorgarh.com."""

from fetchers._chittorgarh_common import fetch_table

URL = "https://www.chittorgarh.com/report/offer-for-sale-in-india/157/"

# Confirmed via --debug run: OFS has no separate open/close columns, just
# one combined "Offer Date" column (the OFS bidding window is only 2 days,
# T and T+1). "date_range" triggers the common fetcher's date-range parsing.
COLUMN_ALIASES = {
    "name": ["company name", "company"],
    "price": ["floor price"],
    "date_range": ["offer date"],
}


def fetch(debug=False):
    return fetch_table(URL, "ofs", debug=debug, column_aliases=COLUMN_ALIASES)


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(fetch(debug="--debug" in sys.argv), indent=2))
