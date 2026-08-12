"""
Tracks which (rule, item) pairs we've already fired a notification for, so
re-running the check on subsequent days doesn't create duplicate calendar
events for an IPO that's still open with GMP still above the threshold.

Stored as a flat JSON file, committed back to the repo by the GitHub Actions
workflow after each run (see .github/workflows/ipo-gmp-alert.yml).
"""

import json
import os

STATE_PATH = "state/notified.json"


def _key(rule_name: str, item: dict) -> str:
    # Name alone is enough - the same company won't have two IPOs with the
    # identical name active at once.
    return f"{rule_name}::{item['name']}"


def load_state(path=STATE_PATH) -> dict:
    if not os.path.exists(path):
        return {"notified": []}
    with open(path) as f:
        return json.load(f)


def save_state(state: dict, path=STATE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def already_notified(state: dict, rule_name: str, item: dict) -> bool:
    return _key(rule_name, item) in state.get("notified", [])


def mark_notified(state: dict, rule_name: str, item: dict):
    key = _key(rule_name, item)
    if key not in state["notified"]:
        state["notified"].append(key)
