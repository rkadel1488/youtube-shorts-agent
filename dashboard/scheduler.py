"""
Background scheduler that replaces GitHub Actions entirely: runs inside the
same process as the dashboard, checks hourly whether now is a good time to
post (reusing the Instagram-online-followers-or-research-fallback logic),
and if so, runs one trend job against every enabled account.

Jobs run strictly sequentially (one at a time) — video rendering is
CPU/memory heavy, and a modest VPS should not run multiple renders in
parallel.
"""
import threading
import time
import traceback
from datetime import datetime, timezone

import db
from utils.logger import get_logger

log = get_logger(__name__)

_lock = threading.Lock()
_running = False


def is_optimal_hour_now() -> tuple[bool, dict]:
    """Reuses the same real-signal-with-fallback logic as the old GH Actions
    check, but reads the Instagram token from whichever 'meta' account(s)
    are configured instead of a single global env var."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    import should_post_now as spn

    meta_accounts = [a for a in db.list_accounts(enabled_only=True) if a["platform"] == "meta"]
    best = None
    if meta_accounts:
        creds = db.get_account_credentials(meta_accounts[0]["id"])
        spn.IG_ACCESS_TOKEN = creds.get("access_token", "")
        best = spn.real_best_hours_utc()

    source = "instagram_insights" if best else "research_fallback"
    best = best or spn.fallback_hours_utc()
    now_hour = datetime.now(timezone.utc).hour
    info = {"source": source, "best_hours_utc": best, "current_hour_utc": now_hour}
    return now_hour in best, info


def run_due_job_if_any() -> dict | None:
    """Check the time, and if optimal + not already running, kick off one
    trend job across all enabled accounts. Returns the job result or None
    if skipped (not optimal time, or a job is already in progress)."""
    global _running
    with _lock:
        if _running:
            log.info("Scheduler: a job is already running, skipping this tick")
            return None
        should_run, info = is_optimal_hour_now()
        log.info("Scheduler check: %s", info)
        if not should_run:
            return None
        _running = True

    try:
        from pipeline_runner import run_trend_job
        account_ids = [a["id"] for a in db.list_accounts(enabled_only=True)]
        if not account_ids:
            log.info("Scheduler: optimal hour, but no enabled accounts configured")
            return None
        log.info("Scheduler: optimal hour — running trend job for %d account(s)", len(account_ids))
        return run_trend_job(account_ids)
    except Exception:
        log.error("Scheduler job failed:\n%s", traceback.format_exc())
        return None
    finally:
        with _lock:
            _running = False


def _loop(poll_seconds: int):
    log.info("Scheduler thread started (checking every %ds)", poll_seconds)
    while True:
        try:
            run_due_job_if_any()
        except Exception:
            log.error("Scheduler tick crashed:\n%s", traceback.format_exc())
        time.sleep(poll_seconds)


def start_background_scheduler(poll_seconds: int = 3600) -> threading.Thread:
    """Start the scheduler as a daemon thread. Call once at app startup."""
    t = threading.Thread(target=_loop, args=(poll_seconds,), daemon=True)
    t.start()
    return t
