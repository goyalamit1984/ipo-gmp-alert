"""
Run this ONCE, locally (not in GitHub Actions), to get a refresh token for
the Google account whose calendar you want events created on.

Before running:
1. In Google Cloud Console, create an OAuth client ID of type "Desktop app".
2. Set the two env vars below (or paste values directly).

    export GOOGLE_CLIENT_ID="..."
    export GOOGLE_CLIENT_SECRET="..."
    python get_refresh_token.py

A browser window opens - log in and approve. The refresh token is printed
at the end; save it as the GOOGLE_REFRESH_TOKEN GitHub secret.
"""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def main():
    client_config = {
        "installed": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)
    print("\nSave this as the GOOGLE_REFRESH_TOKEN secret:\n")
    print(creds.refresh_token)


if __name__ == "__main__":
    main()
