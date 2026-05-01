"""
One-time setup: authenticates with TikTok and saves OAuth tokens.

Run ONCE before starting the agent:
    python setup_tiktok_auth.py

Prerequisites:
  1. Go to https://developers.tiktok.com and create an app
  2. Enable the "Content Posting API" product
  3. Add redirect URI: http://localhost:8080/callback
  4. Copy client_key and client_secret to .env as TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET
"""
import http.server
import json
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

from config import TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_TOKEN_FILE

REDIRECT_URI = "http://localhost:8080/callback"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.publish,video.upload"

_auth_code: str | None = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]

        if code:
            _auth_code = code
            body = b"<h2>TikTok auth complete — you can close this tab.</h2>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        else:
            error = params.get("error_description", ["unknown error"])[0]
            body = f"<h2>Auth failed: {error}</h2>".encode()
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *args):
        pass  # suppress default request logging


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

    print("Opening browser for TikTok authentication…")
    print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("localhost", 8080), _CallbackHandler)
    server.timeout = 120
    print("Waiting for callback on http://localhost:8080/callback …")
    server.handle_request()

    if not _auth_code:
        print("\n[ERROR] No auth code received.")
        sys.exit(1)

    # Exchange code for tokens
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "code": _auth_code,
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
