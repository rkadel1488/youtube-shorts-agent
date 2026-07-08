# Shorts Automation Dashboard

Self-hosted control panel that fully replaces the GitHub Actions automation:
same trend-picking/script/voice/render pipeline, but now (1) supports any
number of YouTube and Meta (Instagram+Facebook) accounts side by side, (2)
runs its own scheduler on your VPS instead of GitHub's cron, and (3) can turn
any existing YouTube video into a Short via the clipper tool.

## What it does

- **Add an account by pasting its token** — no code changes, no redeploy.
  Enable/disable/delete any account anytime from the UI.
- **Automatic scheduling** — a background thread checks hourly whether now
  is a good time to post (same logic as before: real Instagram audience
  data once available, researched engagement-window fallback otherwise),
  and posts one trend-based Short to every enabled account when it is.
- **Manual "Run now"** — post on demand, choosing exactly which accounts.
- **YouTube → Shorts clipper** — paste any YouTube URL, Claude reads its
  transcript and picks the single best 30-60s moment, cuts + reframes it
  to vertical, and posts it to the accounts you pick.
- **Job history** — every run's status and per-platform result, kept in
  the dashboard's database.

## Deploying on your Contabo VPS via Coolify

1. Push this repo (already done if you're reading this from the repo).
2. In Coolify: **New Resource → Docker Compose**, point it at this repo,
   set the compose file path to `dashboard/docker-compose.yml`.
3. Set these environment variables in Coolify (Resource → Environment):

   | Variable | Value |
   |---|---|
   | `ADMIN_PASSWORD` | any password you choose — this gates the whole dashboard |
   | `DASHBOARD_SECRET_KEY` | generate with the command below |
   | `ANTHROPIC_API_KEY` | your existing key |
   | `GOOGLE_AI_STUDIO_API_KEY` | your existing key |
   | `PEXELS_API_KEY` | your existing key |
   | `GH_TOKEN` | a GitHub token with `repo` scope on **this** repo (used only to temporarily host videos for Instagram's fetch-by-URL requirement) |
   | `GITHUB_REPOSITORY` | `rkadel1488/youtube-shorts-agent` |
   | `AUDIENCE_TIMEZONE` | e.g. `America/New_York` (optional, defaults to that) |

   Generate `DASHBOARD_SECRET_KEY` once:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. Deploy. Coolify will build the Dockerfile and expose port 8000 — set up
   a domain/subdomain for it in Coolify same as your other apps (e.g.
   `shorts.yourdomain.com`), so it's reachable over HTTPS rather than a raw
   IP:port (this dashboard holds live API tokens — always put it behind
   HTTPS with the password set).
5. Visit the URL, log in with `ADMIN_PASSWORD`, add your accounts.

## Adding an account

**YouTube**: needs an OAuth token with a `refresh_token`. Run
`python setup_oauth.py` once per YouTube account (locally, it opens a
browser) — this is unchanged from before. Paste the resulting `token.json`
contents into the "YouTube OAuth token JSON" field.

**Meta (Instagram + Facebook)**: paste a system-user access token from
Meta Business Manager → Users → System users → Generate token (permissions:
`pages_show_list`, `pages_read_engagement`, `instagram_basic`,
`instagram_content_publish`, `pages_manage_posts`, `publish_video`,
`business_management`; expiration: **Never**). The dashboard resolves the
linked Page and Instagram account automatically — use the "Test" button
after adding to confirm it resolved correctly.

## Old GitHub Actions workflow

`.github/workflows/post_shorts.yml` has been disabled (schedule trigger
removed, manual `workflow_dispatch` kept as a fallback) now that the VPS
dashboard owns scheduling. If you ever want to go back to it, the schedule
trigger can be restored from git history.

## Known limitations (honest, not hidden)

- **TikTok isn't included yet** — its Content Posting API requires a
  separate app-review process with Meta-style approval delays. The account
  model is already generic (`platform` column), so adding it later is a
  contained change, not a redesign.
- **The clipper needs existing captions** on the source YouTube video
  (manual or auto-generated — true for the large majority of videos). It
  does not run its own speech recognition, so a video with captions
  disabled will fail with a clear error rather than silently guessing.
- **One job at a time** — the scheduler and manual triggers share a lock;
  a second trigger while one is rendering will be skipped/queued rather
  than run in parallel, to avoid overloading a modest VPS.
