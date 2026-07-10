#!/usr/bin/env python3
"""
Decide whether it's time to post, across YouTube/Instagram/Facebook.
Prints "true" or "false" to stdout (for a GitHub Actions step to capture).
Deliberately stdlib-only (urllib, no `requests`) so this can run as a cheap
check BEFORE the dependency-install step — the workflow runs hourly, but
the actual (expensive) render+upload pipeline only fires when this script
approves.

IMPORTANT: this does NOT require landing in one exact target hour anymore.
GitHub Actions' schedule trigger is documented to drift/delay significantly
on repos without heavy activity — observed in practice as ~5 firings across
14 hours instead of ~14 hourly firings. Combined with the old design's 3
single-hour exact-match windows, this meant it was entirely possible to
miss every target hour on a given day through GitHub's timing drift alone,
not any actual bug in the logic. Instead: track hours since the last
successful post (from state/last_result.json, already committed to the
repo) and approve whenever enough time has passed AND it's a reasonable
hour of day — robust to irregular/delayed cron firing by design.

Real signal used: Instagram's /{ig-user-id}/insights?metric=online_followers
for a rough "audience active now" check where meaningful data exists;
otherwise a plain daytime-hours check.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

GRAPH = "https://graph.facebook.com/v21.0"
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
AUDIENCE_TIMEZONE = os.getenv("AUDIENCE_TIMEZONE", "America/New_York")
MIN_SAMPLE_SIZE = 20  # don't trust IG data with fewer than this many followers online

MIN_HOURS_BETWEEN_POSTS = float(os.getenv("MIN_HOURS_BETWEEN_POSTS", "7"))
DAYTIME_LOCAL_HOURS = range(7, 23)  # 7am-11pm local audience time; avoid posting overnight

STATE_PATH = Path(__file__).parent.parent / "state" / "last_result.json"


def _get(url: str, params: dict) -> dict:
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{q}", timeout=15) as r:
        return json.loads(r.read())


def _resolve_ig_user_id() -> str | None:
    data = _get(f"{GRAPH}/me/accounts",
                {"fields": "instagram_business_account", "access_token": IG_ACCESS_TOKEN})
    for page in data.get("data", []):
        iba = page.get("instagram_business_account")
        if iba:
            return iba["id"]
    return None


def _is_audience_active_now() -> bool | None:
    """Best-effort real signal from Instagram. None if unavailable/too sparse."""
    if not IG_ACCESS_TOKEN:
        return None
    try:
        ig_id = _resolve_ig_user_id()
        if not ig_id:
            return None
        data = _get(f"{GRAPH}/{ig_id}/insights",
                    {"metric": "online_followers", "period": "lifetime",
                     "access_token": IG_ACCESS_TOKEN})
        values = data["data"][0]["values"][-1]["value"]
        counts = {int(h): c for h, c in values.items()}
        if sum(counts.values()) < MIN_SAMPLE_SIZE:
            return None
        now_hour = datetime.now(timezone.utc).hour
        # "active now" if this hour is above-average for the audience
        avg = sum(counts.values()) / len(counts)
        return counts.get(now_hour, 0) >= avg
    except Exception as exc:
        print(f"[best_time] IG insights unavailable ({exc}); using daytime-hours check", file=sys.stderr)
        return None


def _hours_since_last_post() -> float:
    if not STATE_PATH.exists():
        return float("inf")  # never posted (or state missing) -> always eligible
    try:
        data = json.loads(STATE_PATH.read_text())
        job_id = data.get("job_id", "")
        # job_id format: YYYYMMDD_HHMMSS[_slotN]
        ts_part = "_".join(job_id.split("_")[:2])
        last = datetime.strptime(ts_part, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last).total_seconds() / 3600
    except Exception as exc:
        print(f"[best_time] Could not parse last post time ({exc}); treating as eligible", file=sys.stderr)
        return float("inf")


def _is_daytime_local() -> bool:
    if not ZoneInfo:
        return True
    tz = ZoneInfo(AUDIENCE_TIMEZONE)
    return datetime.now(tz).hour in DAYTIME_LOCAL_HOURS


def main() -> None:
    hours_since = _hours_since_last_post()
    enough_time_passed = hours_since >= MIN_HOURS_BETWEEN_POSTS
    daytime = _is_daytime_local()
    audience_active = _is_audience_active_now()

    # Real audience data can OVERRIDE the daytime gate (e.g. approve a
    # slightly-off-peak-local hour if IG shows followers genuinely active),
    # but never overrides the minimum-interval throttle — that's a hard
    # floor to avoid ever double-posting in a short window.
    should_run = enough_time_passed and (daytime or audience_active is True)

    print(f"[best_time] hours_since_last_post={hours_since:.1f} "
          f"min_required={MIN_HOURS_BETWEEN_POSTS} daytime_local={daytime} "
          f"audience_active={audience_active} should_run={should_run}", file=sys.stderr)
    print("true" if should_run else "false")


if __name__ == "__main__":
    main()
