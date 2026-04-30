"""
One-time setup: authenticates with YouTube and saves the OAuth token.

Run ONCE before starting the agent:
    python setup_youtube_auth.py

Prerequisites:
  1. Go to https://console.cloud.google.com
  2. Create a project -> Enable "YouTube Data API v3"
  3. Create OAuth 2.0 credentials (Desktop app)
  4. Download the JSON and save as client_secrets.json in this folder
"""
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from config import YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES, YOUTUBE_TOKEN_FILE


def main():
    secrets_path = Path(YOUTUBE_CLIENT_SECRETS_FILE)
    if not secrets_path.exists():
        print(f"\n[ERROR] '{YOUTUBE_CLIENT_SECRETS_FILE}' not found.")
        print("Steps:")
        print("  1. Visit https://console.cloud.google.com")
        print("  2. Create a project and enable 'YouTube Data API v3'")
        print("  3. Create OAuth 2.0 credentials (Desktop app)")
        print("  4. Download the JSON and save it as:", secrets_path.absolute())
        sys.exit(1)

    print("Opening browser for YouTube authentication…")
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), YOUTUBE_SCOPES)
    creds = flow.run_local_server(port=0)

    token_path = Path(YOUTUBE_TOKEN_FILE)
    with open(token_path, "w") as f:
        f.write(creds.to_json())

    print(f"\n[OK] Token saved -> {token_path.absolute()}")
    print("You can now run: python main.py")


if __name__ == "__main__":
    main()
