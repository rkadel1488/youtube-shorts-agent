#!/usr/bin/env python3
"""
Decide whether THIS hour is a good time to post, across YouTube/Instagram/
Facebook. Prints "true" or "false" to stdout (for a GitHub Actions step to
capture). Deliberately stdlib-only (urllib, no `requests`) so this can run
as a cheap check BEFORE the dependency-install step — the workflow runs
hourly, but the actual (expensive) render+upload pipeline only fires on the
hours this script approves.

Real signal used: Instagram's /{ig-user-id}/insights?metric=online_followers
— the one platform that exposes an "audience online right now" style metric
reachable at small account sizes. Facebook's equivalent Page Insights
require 100+ Page likes before Meta returns anything, and YouTube has no
simple "audience online" endpoint for a new channel — so neither has a
usable real signal yet for this channel.

Fallback: well-established general engagement windows for short-form video
(morning scroll / lunch break / evening leisure), in the target audience's
local time zone, converted to UTC with DST handled via zoneinfo — this
applies across all three platforms since it reflects audience daily rhythm,
not one platform's algorithm.

As the Instagram account accumulates enough follower activity, this
automatically switches over to real data — no manual re-tuning needed.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

GRAPH = "https://graph.facebook.com/v21.0"
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")

# General short-form-video engagement windows, in the audience's LOCAL time.
FALLBACK_LOCAL_HOURS = [8, 12, 19]  # morning scroll, lunch, evening leisure
AUDIENCE_TIMEZONE = os.getenv("AUDIENCE_TIMEZONE", "America/New_York")
MIN_SAMPLE_SIZE = 20  # don't trust IG data with fewer than this many followers online


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


def real_best_hours_utc(top_n: int = 3) -> list[int] | None:
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
        values = data["data"][0]["values"][-1]["value"]  # {"0": n, ..., "23": n}, UTC hour keys
        counts = {int(h): c for h, c in values.items()}
        if sum(counts.values()) < MIN_SAMPLE_SIZE:
            return None
        top = sorted(counts, key=counts.get, reverse=True)[:top_n]
        return sorted(top)
    except Exception as exc:
        print(f"[best_time] IG insights unavailable ({exc}); using fallback", file=sys.stderr)
        return None


def fallback_hours_utc() -> list[int]:
    if not ZoneInfo:
        return sorted(set(FALLBACK_LOCAL_HOURS))
    tz = ZoneInfo(AUDIENCE_TIMEZONE)
    today = datetime.now(tz).date()
    hours = set()
    for h in FALLBACK_LOCAL_HOURS:
        local_dt = datetime(today.year, today.month, today.day, h, tzinfo=tz)
        hours.add(local_dt.astimezone(timezone.utc).hour)
    return sorted(hours)


def main() -> None:
    best = real_best_hours_utc()
    source = "instagram_insights" if best else "research_fallback"
    best = best or fallback_hours_utc()

    now_hour = datetime.now(timezone.utc).hour
    should_run = now_hour in best

    print(f"[best_time] source={source} best_hours_utc={best} "
          f"current_hour_utc={now_hour} should_run={should_run}", file=sys.stderr)
    print("true" if should_run else "false")


if __name__ == "__main__":
    main()
