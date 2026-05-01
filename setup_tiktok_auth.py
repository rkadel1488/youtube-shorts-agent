"""
One-time setup: authenticates with TikTok and saves OAuth tokens.

Run ONCE before starting the agent:
    python setup_tiktok_auth.py

Prerequisites:
  1. Go to https://developers.tiktok.com and create an app
  2. Enable the "Content Posting API" product
  3. Add redirect URI: https://localhost (TikTok requires HTTPS, not http://localhost)
  4. Copy client_key and client_secret to .env as TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET

How the auth flow works:
  - Your browser opens TikTok's auth page
  - After approving, TikTok redirects to https://localhost?code=...  (page won't load — that's fine)
  - Copy the full URL from your browser's address bar and paste it here
"""
import json
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

from config import TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_TOKEN_FILE

# Must exactly match what you registered in the TikTok developer portal
REDIRECT_URI = "https://localhost"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.publish,video.upload"


def _extract_code(raw: str) -> str:
    """
    Accept either a full redirect URL or a bare code string.
    e.g. "https://localhost?code=abc123&state=..." → "abc123"
         "abc123" → "abc123"
    """
    raw = raw.strip()
    if raw.startswith("http"):
        parsed = urllib.parse.urlparse(raw)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if not code:
            raise ValueError(f"No 'code' parameter found in URL: {raw}")
        return code
    return raw  # bare code pasted directly


def main():
    if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET:
        print("\n[ERROR] TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET must be set in .env")
        sys.exit(1)

    params = urllib.parse.urlencode({
        "client_key": TIKTOK_CLIENT_KEY,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": "tiktok_auth",
    })
    auth_url = f"{AUTH_URL}?{params}"

    print("\n" + "=" * 60)
    print("  TikTok OAuth Setup")
    print("=" * 60)
    print("\nStep 1: Opening TikTok authorization page in your browser…")
    print(f"        (If it doesn't open, visit the URL below manually)\n")
    print(f"  {auth_url}\n")
    webbrowser.open(auth_url)

    print("Step 2: Approve the permissions in your browser.")
    print("        TikTok will redirect to https://localhost — the page")
    print("        will show a connection error. That is expected.\n")
    print("Step 3: Copy the FULL URL from your browser's address bar")
    print("        (it will look like: https://localhost?code=...&state=...)\n")

    raw = input("Paste the redirect URL (or just the code) here: ").strip()
    if not raw:
        print("\n[ERROR] Nothing entered.")
        sys.exit(1)

    try:
        auth_code = _extract_code(raw)
    except ValueError as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)

    print("\nExchanging code for access token…")
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    resp.raise_for_status()
    token_data = resp.json()

    if "access_token" not in token_data:
        print(f"\n[ERROR] Token exchange failed: {token_data}")
        sys.exit(1)

    token_data["expires_at"] = time.time() + token_data.get("expires_in", 86400)

    token_path = Path(TIKTOK_TOKEN_FILE)
    with open(token_path, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\n[OK] Token saved -> {token_path.absolute()}")
    print("You can now run: python main.py")


if __name__ == "__main__":
    main()
