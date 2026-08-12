"""
Creates a Google Calendar event. Auth is via a stored OAuth refresh token
(see get_refresh_token.py) so this can run unattended in GitHub Actions.

Required environment variables:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REFRESH_TOKEN
    GOOGLE_CALENDAR_ID   (optional, defaults to "primary")
"""

import datetime
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
    return build("calendar", "v3", credentials=creds)


def notify(item: dict, rule: dict):
    """Create a calendar event for a matched item.

    `rule` may contain a "notify_config" dict with:
        - title_template: str, formatted with item's fields via .format(**item)
        - description_template: str, same
        - all_day: bool (default True)
    """
    config = rule.get("notify_config", {})
    title_template = config.get("title_template", "IPO Alert: {name}")
    desc_template = config.get(
        "description_template",
        "GMP: {gmp_rupees} ({gmp_percent}%)\nCategory: {category}\nPrice: {price}",
    )

    safe_item = {k: (v if v is not None else "N/A") for k, v in item.items() if k != "raw"}
    title = title_template.format(**safe_item)
    description = desc_template.format(**safe_item)

    today = datetime.date.today().isoformat()

    service = _get_service()
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    event = {
        "summary": title,
        "description": description,
        "start": {"date": today},
        "end": {"date": today},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 0}],
        },
    }

    created = service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"Created calendar event: {created.get('htmlLink')}")
    return created
