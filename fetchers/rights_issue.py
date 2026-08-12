"""Fetches the live Rights Issue list from chittorgarh.com."""

from fetchers._chittorgarh_common import fetch_table

URL = "https://www.chittorgarh.com/report/latest-rights-issue-in-india/75/"


def fetch(debug=False):
    return fetch_table(URL, "rights_issue", debug=debug)


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(fetch(debug="--debug" in sys.argv), indent=2))
