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

from conditions import matches_all

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
        print(f"Rule '{rule['name']}': {len(matched_items)} item(s) matched")

        if matched_items:
            any_match = True
            notifier = get_notifier(rule["notifier"])
            for item in matched_items:
                notifier.notify(item, rule)

    if not any_match:
        print("No rules matched today.")


if __name__ == "__main__":
    run(debug="--debug" in sys.argv)
