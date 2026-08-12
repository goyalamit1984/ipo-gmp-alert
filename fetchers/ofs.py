"""Fetches the live Offer For Sale (OFS) list from chittorgarh.com."""

from fetchers._chittorgarh_common import fetch_table

URL = "https://www.chittorgarh.com/report/offer-for-sale-in-india/157/"


def fetch(debug=False):
    return fetch_table(URL, "ofs", debug=debug)


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(fetch(debug="--debug" in sys.argv), indent=2))
