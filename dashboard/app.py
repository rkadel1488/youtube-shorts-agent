"""
AI Shorts Maker — a simple on-demand tool: paste a YouTube link or upload
your own video, get back a rendered vertical Short to download. Nothing
auto-posts anywhere; no accounts or credentials are stored.
"""
import os
import sys
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer, BadSignature

sys.path.insert(0, str(Path(__file__).parent.parent))  # sibling agents/ package

import db

APP_DIR = Path(__file__).parent
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SESSION_SECRET = os.getenv("DASHBOARD_SECRET_KEY", "insecure-dev-key")
serializer = URLSafeTimedSerializer(SESSION_SECRET)

app = FastAPI(title="AI Shorts Maker")


# ── auth (kept — this triggers real API calls with a cost, shouldn't be public) ──

def _make_session_token() -> str:
    return serializer.dumps({"authed": True})


def require_auth(request: Request):
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    try:
        data = serializer.loads(token, max_age=60 * 60 * 24 * 30)
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


# ── main page ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def index():
    return (APP_DIR / "static" / "index.html").read_text()


# ── render API ────────────────────────────────────────────────────────────────

@app.post("/api/render/youtube", dependencies=[Depends(require_auth)])
def api_render_youtube(youtube_url: str = Form(...)):
    from render_runner import render_from_youtube

    def _run():
        render_from_youtube(youtube_url)

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started"}


@app.post("/api/render/upload", dependencies=[Depends(require_auth)])
def api_render_upload(
    file: UploadFile = File(...),
    start_seconds: float = Form(...),
    end_seconds: float = Form(...),
    mode: str = Form("blur"),
):
    from render_runner import render_from_upload

    if end_seconds <= start_seconds:
        raise HTTPException(400, "end_seconds must be greater than start_seconds")
    if end_seconds - start_seconds > 120:
        raise HTTPException(400, "Keep clips under 2 minutes")
    if mode not in ("blur", "crop"):
        raise HTTPException(400, "mode must be 'blur' or 'crop'")

    suffix = Path(file.filename).suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(Path(__file__).parent))
    tmp.write(file.file.read())
    tmp.close()
    tmp_path = Path(tmp.name)

    def _run():
        render_from_upload(tmp_path, file.filename, start_seconds, end_seconds, mode=mode)

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started"}


@app.get("/api/renders", dependencies=[Depends(require_auth)])
def api_list_renders(limit: int = 50):
    return db.list_renders(limit=limit)


@app.get("/api/renders/{render_id}", dependencies=[Depends(require_auth)])
def api_get_render(render_id: int):
    r = db.get_render(render_id)
    if not r:
        raise HTTPException(404, "Render not found")
    return r


@app.get("/api/renders/{render_id}/download", dependencies=[Depends(require_auth)])
def api_download_render(render_id: int):
    r = db.get_render(render_id)
    if not r or r["status"] != "success" or not r["output_path"]:
        raise HTTPException(404, "No finished video for this render")
    path = Path(r["output_path"])
    if not path.exists():
        raise HTTPException(404, "Output file is missing on disk")
    filename = f"short_{render_id}.mp4"
    return FileResponse(path, media_type="video/mp4", filename=filename)


app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
