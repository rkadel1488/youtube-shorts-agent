"""
FastAPI dashboard: single-admin-password login, account management (add a
YouTube/Meta account by pasting its credentials — no code changes needed),
manual "run now" triggers, job history, and the YouTube-clip-to-Shorts tool.
"""
import os
import sys
import threading
from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer, BadSignature

sys.path.insert(0, str(Path(__file__).parent.parent))  # sibling agents/ package

import db
from scheduler import start_background_scheduler

APP_DIR = Path(__file__).parent
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SESSION_SECRET = os.getenv("DASHBOARD_SECRET_KEY", "insecure-dev-key")
serializer = URLSafeTimedSerializer(SESSION_SECRET)

app = FastAPI(title="Shorts Automation Dashboard")


# ── auth ──────────────────────────────────────────────────────────────────────

def _make_session_token() -> str:
    return serializer.dumps({"authed": True})


def require_auth(request: Request):
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    try:
        data = serializer.loads(token, max_age=60 * 60 * 24 * 30)  # 30 days
    except BadSignature:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if not data.get("authed"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


@app.exception_handler(HTTPException)
async def redirect_on_auth_failure(request: Request, exc: HTTPException):
    if exc.status_code == 303:
        return RedirectResponse(url="/login")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return (APP_DIR / "static" / "login.html").read_text()


@app.post("/login")
def login(password: str = Form(...)):
    if not ADMIN_PASSWORD:
        raise HTTPException(500, "ADMIN_PASSWORD is not configured on the server")
    if password != ADMIN_PASSWORD:
        return RedirectResponse(url="/login?error=1", status_code=303)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie("session", _make_session_token(), httponly=True, max_age=60 * 60 * 24 * 30)
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("session")
    return resp


# ── dashboard page ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def index():
    return (APP_DIR / "static" / "index.html").read_text()


# ── accounts API ──────────────────────────────────────────────────────────────

@app.get("/api/accounts", dependencies=[Depends(require_auth)])
def api_list_accounts():
    accounts = db.list_accounts()
    for a in accounts:
        a.pop("credentials_enc", None)  # never send encrypted blob to the browser
    return accounts


@app.post("/api/accounts", dependencies=[Depends(require_auth)])
def api_add_account(
    platform: str = Form(...),
    label: str = Form(...),
    # YouTube fields
    youtube_token_json: str = Form(""),
    # Meta fields
    meta_access_token: str = Form(""),
    post_to_instagram: bool = Form(True),
    post_to_facebook: bool = Form(True),
):
    import json as _json
    if platform == "youtube":
        if not youtube_token_json.strip():
            raise HTTPException(400, "Paste the YouTube OAuth token JSON")
        try:
            creds = _json.loads(youtube_token_json)
        except _json.JSONDecodeError:
            raise HTTPException(400, "That doesn't look like valid JSON")
        if "refresh_token" not in creds:
            raise HTTPException(400, "Token JSON must include a refresh_token")
        account_id = db.add_account("youtube", label, creds)
    elif platform == "meta":
        if not meta_access_token.strip():
            raise HTTPException(400, "Paste the Meta system-user access token")
        account_id = db.add_account("meta", label, {"access_token": meta_access_token.strip()},
                                     post_to_instagram=post_to_instagram,
                                     post_to_facebook=post_to_facebook)
    else:
        raise HTTPException(400, f"Unknown platform: {platform}")
    return {"id": account_id, "status": "added"}


@app.post("/api/accounts/{account_id}/toggle", dependencies=[Depends(require_auth)])
def api_toggle_account(account_id: int):
    acc = db.get_account(account_id)
    if not acc:
        raise HTTPException(404, "Account not found")
    db.set_account_enabled(account_id, not acc["enabled"])
    return {"id": account_id, "enabled": not acc["enabled"]}


@app.delete("/api/accounts/{account_id}", dependencies=[Depends(require_auth)])
def api_delete_account(account_id: int):
    db.delete_account(account_id)
    return {"id": account_id, "status": "deleted"}


@app.post("/api/accounts/{account_id}/test", dependencies=[Depends(require_auth)])
def api_test_account(account_id: int):
    """Verify credentials actually work before relying on them in a scheduled run."""
    acc = db.get_account(account_id)
    if not acc:
        raise HTTPException(404, "Account not found")
    creds = db.get_account_credentials(account_id)
    try:
        if acc["platform"] == "meta":
            from agents.instagram_agent import resolve_meta_account
            result = resolve_meta_account(creds["access_token"])
            return {"ok": True, "detail": f"Page {result['page_id']}, "
                                          f"IG {'linked: ' + result['ig_user_id'] if result['ig_user_id'] else 'NOT linked'}"}
        elif acc["platform"] == "youtube":
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as GRequest
            from config import YOUTUBE_SCOPES
            c = Credentials.from_authorized_user_info(creds, YOUTUBE_SCOPES)
            if not c.valid and c.refresh_token:
                c.refresh(GRequest())
            return {"ok": c.valid, "detail": "Token is valid" if c.valid else "Token could not be validated"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


# ── jobs API ──────────────────────────────────────────────────────────────────

@app.get("/api/jobs", dependencies=[Depends(require_auth)])
def api_list_jobs(limit: int = 50):
    return db.list_jobs(limit=limit)


@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_auth)])
def api_get_job(job_id: int):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/api/jobs/run-now", dependencies=[Depends(require_auth)])
def api_run_now(account_ids: str = Form(...)):
    """account_ids: comma-separated list, e.g. '1,3,4'."""
    import json as _json
    from pipeline_runner import run_trend_job
    ids = [int(x) for x in account_ids.split(",") if x.strip()]

    def _run():
        try:
            run_trend_job(ids)
        except Exception:
            pass  # error already logged + persisted to the job row

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started"}


@app.post("/api/jobs/clip", dependencies=[Depends(require_auth)])
def api_run_clip(youtube_url: str = Form(...), account_ids: str = Form(...)):
    from pipeline_runner import run_clip_job
    ids = [int(x) for x in account_ids.split(",") if x.strip()]

    def _run():
        try:
            run_clip_job(youtube_url, ids)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started"}


# ── startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    if not ADMIN_PASSWORD:
        print("WARNING: ADMIN_PASSWORD is not set — the dashboard login will reject everyone "
              "until you set it.", file=sys.stderr)
    start_background_scheduler(poll_seconds=int(os.getenv("SCHEDULER_POLL_SECONDS", "3600")))


app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
