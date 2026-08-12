"""
Loads rules.json, runs the fetcher for each rule, checks conditions against
every item returned, and fires the notifier for anything that matches.

To add a new kind of alert:
    1. Add a fetcher module in fetchers/ if the data source is new
       (must expose a fetch() -> list[dict]).
    2. Add a notifier module in notifiers/ if the output channel is new
       (must expose notify(item, rule)).
    3. Add a block to rules.json. No changes needed here.
"""

import importlib
import json
import sys

from conditions import matches_all, closing_soon
from state import load_state, save_state, already_notified, mark_notified

_fetch_cache = {}


def load_rules(path="rules.json"):
    with open(path) as f:
        return json.load(f)


def get_fetcher(name):
    return importlib.import_module(f"fetchers.{name}")


def get_notifier(name):
    return importlib.import_module(f"notifiers.{name}")


def run(debug=False):
    rules = load_rules()
    state = load_state()
    any_match = False

    for rule in rules:
        fetcher_name = rule["fetcher"]

        if fetcher_name not in _fetch_cache:
            fetcher = get_fetcher(fetcher_name)
            fetch_kwargs = {"debug": debug} if debug else {}
            try:
                _fetch_cache[fetcher_name] = fetcher.fetch(**fetch_kwargs)
            except TypeError:
                # fetcher doesn't accept a debug kwarg
                _fetch_cache[fetcher_name] = fetcher.fetch()

        items = _fetch_cache[fetcher_name]
        print(f"Rule '{rule['name']}': fetched {len(items)} items from {fetcher_name}")

        matched_items = [i for i in items if matches_all(i, rule["conditions"])]

        date_window = rule.get("date_window_days")
        if date_window is not None:
            before = len(matched_items)
            matched_items = [i for i in matched_items if closing_soon(i, date_window)]
            print(f"Rule '{rule['name']}': {before} matched conditions, "
                  f"{len(matched_items)} closing within {date_window} day(s)")

        notifier = get_notifier(rule["notifier"])
        notified_count = 0
        skipped_count = 0
        for item in matched_items:
            # Check-and-mark right here (not precomputed) so two items with
            # the same name in a single fetch don't both slip through.
            if already_notified(state, rule["name"], item):
                skipped_count += 1
                continue
            notifier.notify(item, rule)
            mark_notified(state, rule["name"], item)
            notified_count += 1
            any_match = True

        if skipped_count:
            print(f"Rule '{rule['name']}': skipping {skipped_count} already-notified item(s)")
        print(f"Rule '{rule['name']}': {notified_count} new item(s) notified")

    save_state(state)

    if not any_match:
        print("No new alerts today.")


if __name__ == "__main__":
    run(debug="--debug" in sys.argv)
