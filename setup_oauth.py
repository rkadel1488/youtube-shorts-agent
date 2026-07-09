#!/usr/bin/env python3
"""
One-time OAuth setup for adding a YouTube account to the dashboard.

Run this LOCALLY (not on the VPS) — it opens a browser window for you to
log in and approve access. Afterward it prints the token JSON to paste
into the dashboard's "YouTube OAuth token JSON" field when adding an
account.

Prereqs:
1. Google Cloud Console -> enable "YouTube Data API v3" for your project
2. OAuth consent screen -> add your Google account as a test user
   (or publish the app if you want long-lived tokens without re-consent)
3. Credentials -> Create OAuth client ID -> Desktop app -> Download JSON
   -> save it in this same folder as `client_secrets.json`

Usage:
    pip3 install google-auth-oauthlib
    python3 setup_oauth.py
"""
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = "client_secrets.json"


def main():
    if not Path(CLIENT_SECRETS_FILE).exists():
        print(f"ERROR: {CLIENT_SECRETS_FILE} not found in this folder.")
        print("Download it from Google Cloud Console -> Credentials -> "
              "your OAuth client -> Download JSON, and save it here as "
              f"'{CLIENT_SECRETS_FILE}'.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    token_info = json.loads(creds.to_json())

    out_path = Path("token.json")
    out_path.write_text(json.dumps(token_info, indent=2))

    print("\n" + "=" * 60)
    print(f"Success! Token saved to {out_path.resolve()}")
    print("=" * 60)
    print("\nCopy everything below and paste it into the dashboard's")
    print("'YouTube OAuth token JSON' field when adding this account:\n")
    print(json.dumps(token_info))
    print()


if __name__ == "__main__":
    main()
