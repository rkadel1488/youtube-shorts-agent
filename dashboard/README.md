# AI Shorts Maker

A simple, self-hosted tool: paste a YouTube link or upload your own video,
get back a rendered vertical (9:16) Short to download. That's it —
**nothing auto-posts anywhere, no accounts, no scheduler, no credentials
stored.** The main channel automation (trend-based posting to YouTube/IG/FB)
lives separately in GitHub Actions, unaffected by this tool.

## What it does

- **From a YouTube link**: fetches the video's captions, has Claude pick the
  single best 30–60s moment, then cuts and reframes it to vertical.
- **From your own upload**: you pick the start/end seconds yourself (no
  captions available for an arbitrary file), same cut + reframe.
- Every render shows up in a simple history list with a **Download** button.

## Deploying on your Contabo VPS via Coolify

1. Coolify → **New Resource → Dockerfile** (not Docker Compose / not
   Nixpacks — pick **Dockerfile** as the build pack directly)
2. Base Directory: `/` (repo root) · Dockerfile Location: `dashboard/Dockerfile`
3. Environment variables:

   | Variable | Value |
   |---|---|
   | `ADMIN_PASSWORD` | any password — gates the whole tool |
   | `DASHBOARD_SECRET_KEY` | generate: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
   | `ANTHROPIC_API_KEY` | your existing key (used to pick the best moment from a transcript) |
   | `YTDLP_COOKIES` | optional, see below — needed if YouTube blocks downloads |

4. **Add persistent storage** (Resource → Storages): mount path
   `/srv/dashboard/data` — this is where the database *and* all rendered
   videos live. Skip this and every redeploy wipes your render history.
5. **Ports Exposes**: `8000`. Set up a domain for HTTPS.
6. Deploy, visit your domain, log in.

## The YouTube-link mode may hit YouTube blocking your VPS's IP

This happens in **two separate places**, with two different fixes — if
you hit one, you may still hit the other:

**1. Transcript fetching blocked** (`RequestBlocked`/`IpBlocked` from
`youtube-transcript-api`) — the library's own error message explicitly
recommends **against** a cookie-based workaround here, since it risks
getting the authenticating Google account permanently banned. Its
recommended fix is a proxy, and it has built-in support for
[Webshare](https://www.webshare.io/) specifically:

1. Sign up for Webshare (has a free tier; paid "Residential" proxies
   work more reliably against YouTube's blocking than the free
   datacenter ones)
2. Get your **Proxy Username** and **Proxy Password** from their dashboard
3. Set `WEBSHARE_PROXY_USERNAME` and `WEBSHARE_PROXY_PASSWORD` as env
   vars in Coolify
4. Redeploy — no code changes needed, this activates automatically

Without these set, transcript fetching just goes out directly, same as
before.

**2. Video download blocked** ("Sign in to confirm you're not a bot"
from `yt-dlp`) — this is the *download* step, separate from the
transcript step above. Its accepted fix genuinely is cookies (unlike
the transcript step):

1. Install a browser extension like **"Get cookies.txt LOCALLY"**
2. While logged into YouTube, export cookies for `youtube.com`
3. Set the file's contents as `YTDLP_COOKIES` in Coolify
4. Redeploy

Using a secondary/throwaway Google account's cookies (rather than your
main one) is the safer option for this step specifically. Cookies expire
periodically — re-export if it starts failing again after previously
working.

**The upload mode is unaffected by either of these** — it's just your
own file, no YouTube request involved at all. If the YouTube-link mode's
setup feels like too much, the upload mode alone is a fully reliable
fallback with zero extra accounts or services.

## Known limitations

- The YouTube-link mode needs existing captions (manual or auto-generated)
  on the source video — it doesn't run its own transcription.
- Uploads capped at 2 minutes per clip.
- One render at a time isn't enforced — for a personal-use tool this is
  fine, but heavy concurrent use could strain a modest VPS.
