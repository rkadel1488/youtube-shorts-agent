"""
Fetches recent cricket match data from ESPN's public cricket API (no API key needed).
Returns a list of recent match summaries to feed into the script agent.
"""
import time

import requests

from utils.logger import get_logger

log = get_logger(__name__)

# ESPN public cricket API — returns recent international cricket scores
ESPN_CRICKET_API = "https://site.api.espn.com/apis/site/v2/sports/cricket/28/scoreboard"
BBC_CRICKET_RSS  = "https://feeds.bbci.co.uk/sport/cricket/rss.xml"


def _parse_espn(data: dict) -> list[dict]:
    """Extract match summaries from ESPN scoreboard JSON."""
    matches = []
    for event in data.get("events", []):
        try:
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            team1 = competitors[0].get("team", {}).get("displayName", "Team A") if len(competitors) > 0 else "Team A"
            team2 = competitors[1].get("team", {}).get("displayName", "Team B") if len(competitors) > 1 else "Team B"
            score1 = competitors[0].get("score", "") if len(competitors) > 0 else ""
            score2 = competitors[1].get("score", "") if len(competitors) > 1 else ""
            status = comp.get("status", {}).get("type", {}).get("description", "")
            name   = event.get("name", f"{team1} vs {team2}")
            note   = comp.get("note", "")
            matches.append({
                "name": name,
                "team1": team1, "score1": score1,
                "team2": team2, "score2": score2,
                "status": status,
                "note": note,
            })
        except Exception:
            continue
    return matches


def _parse_bbc_rss(xml_text: str) -> list[dict]:
    """Parse BBC Sport cricket RSS as a simple fallback."""
    import xml.etree.ElementTree as ET
    matches = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.findall(".//item")[:6]:
            title = item.findtext("title", "")
            desc  = item.findtext("description", "")
            if title:
                matches.append({"name": title, "note": desc,
                                 "team1": "", "score1": "", "team2": "", "score2": "", "status": ""})
    except Exception:
        pass
    return matches


def get_recent_matches(retries: int = 3) -> list[dict]:
    """
    Return a list of recent cricket match dicts.
    Falls back to BBC RSS if ESPN API fails.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(ESPN_CRICKET_API, timeout=15,
                                headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            matches = _parse_espn(resp.json())
            if matches:
                log.info("Fetched %d recent cricket matches from ESPN", len(matches))
                return matches
        except Exception as exc:
            log.warning("ESPN cricket API attempt %d failed: %s", attempt, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)

    # Fallback: BBC Sport cricket RSS
    log.info("Falling back to BBC Sport cricket RSS...")
    try:
        resp = requests.get(BBC_CRICKET_RSS, timeout=15)
        resp.raise_for_status()
        matches = _parse_bbc_rss(resp.text)
        if matches:
            log.info("Fetched %d cricket stories from BBC RSS", len(matches))
            return matches
    except Exception as exc:
        log.warning("BBC RSS fallback failed: %s", exc)

    log.warning("No live match data available — will generate generic highlight")
    return []
