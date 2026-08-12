"""
Reusable condition evaluation.

A condition looks like:
    {"field": "gmp_percent", "op": ">", "value": 15}

A rule can have a list of conditions under "conditions" - ALL must pass
(AND logic) for the rule to fire on a given item.
"""

import re

_OPS = {
    ">": lambda a, b: a is not None and a > b,
    ">=": lambda a, b: a is not None and a >= b,
    "<": lambda a, b: a is not None and a < b,
    "<=": lambda a, b: a is not None and a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "contains": lambda a, b: a is not None and str(b).lower() in str(a).lower(),
    "not_contains": lambda a, b: a is None or str(b).lower() not in str(a).lower(),
    "regex": lambda a, b: a is not None and re.search(b, str(a)) is not None,
}


def evaluate(item: dict, condition: dict) -> bool:
    field = condition["field"]
    op = condition["op"]
    value = condition["value"]

    if op not in _OPS:
        raise ValueError(f"Unknown operator: {op}")

    actual = item.get(field)
    return _OPS[op](actual, value)


def matches_all(item: dict, conditions: list) -> bool:
    return all(evaluate(item, cond) for cond in conditions)


def closing_soon(item: dict, window_days: int) -> bool:
    """True if the item's close_date is today or within the next
    window_days days. Only looks at close_date (not open_date) -
    this is specifically for "closing today/tomorrow" alerts."""
    days = item.get("days_until_close")
    return days is not None and 0 <= days <= window_days
