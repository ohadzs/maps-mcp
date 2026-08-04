"""I/O-free core for Google Maps Platform (Directions + Places).

All the actual logic lives here: read the key, enforce the per-day cost cap,
call the Google APIs, and return plain Python dicts/lists. No printing, no
argparse, no MCP — the MCP adapter (server.py) and the CLI adapter (cli.py)
both import from here so there is exactly one engine.

The API key is read from ~/.gmaps_key (chmod 600) or $GMAPS_KEY. It never
appears in arguments or return values. Cost safety: a per-day call cap
(MAPS_DAILY_CAP, default 200) makes runaway spend impossible.

NOT a connection to a personal Google Maps account (saved places / lists /
Timeline have no public API — reach those via the browser, signed in).
"""
import os
import json
import datetime
import urllib.parse
import urllib.request

# Endpoints for the commute() shortcut. Read from the environment on purpose —
# the repo carries no addresses.
HOME = os.environ.get("MAPS_HOME", "")
WORK = os.environ.get("MAPS_WORK", "")

MODES = ("driving", "walking", "bicycling", "transit")

KEY_FILE = os.path.expanduser("~/.gmaps_key")
COUNT_FILE = os.path.expanduser("~/.gmaps_mcp_count")
DAILY_CAP = int(os.environ.get("MAPS_DAILY_CAP", "200"))


class MapsError(RuntimeError):
    """Raised for key/cap/API problems. Adapters decide how to present it."""


def _key() -> str:
    k = os.environ.get("GMAPS_KEY", "").strip()
    if k:
        return k
    try:
        with open(KEY_FILE) as f:
            return f.read().strip()
    except OSError:
        raise MapsError(
            f"No Google Maps API key found. Put it in {KEY_FILE} (chmod 600) "
            "or set $GMAPS_KEY. The key stays on disk; it is never shown to the model."
        )


def _charge_one() -> None:
    """Increment the per-day call counter; raise once the cap is hit."""
    today = datetime.date.today().isoformat()
    n = 0
    try:
        with open(COUNT_FILE) as f:
            day, saved = f.read().split()
            if day == today:
                n = int(saved)
    except (OSError, ValueError):
        pass
    if n >= DAILY_CAP:
        raise MapsError(
            f"Daily Google Maps call cap reached ({DAILY_CAP}/day) — refusing to "
            "call to guarantee no billing. Resets at midnight, or raise MAPS_DAILY_CAP."
        )
    try:
        with open(COUNT_FILE, "w") as f:
            f.write(f"{today} {n + 1}")
    except OSError:
        pass


def _get(url: str) -> dict:
    _charge_one()
    req = urllib.request.Request(url, headers={"User-Agent": "maps-mcp"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def _post(url: str, body: dict, headers: dict) -> dict:
    _charge_one()
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def directions(origin: str, destination: str, mode: str = "driving") -> dict:
    """Live traffic-aware route between two places.

    Returns a plain dict:
      {
        "ok": bool,
        "origin", "destination", "mode": str,
        # when ok:
        "eta_min": int,        # live ETA with current traffic
        "typical_min": int,    # duration without traffic
        "delay_min": int,      # eta_min - typical_min
        "km": float,
        "via": str,            # main road / route summary
        # when not ok:
        "error": str,
      }
    """
    if mode not in MODES:
        return {"ok": False, "origin": origin, "destination": destination,
                "mode": mode, "error": f"mode must be one of {', '.join(MODES)}."}
    q = urllib.parse.urlencode({
        "origin": origin, "destination": destination,
        "departure_time": "now", "mode": mode,
        "region": "il", "language": "iw", "key": _key(),
    })
    d = _get("https://maps.googleapis.com/maps/api/directions/json?" + q)
    if d.get("status") != "OK":
        return {"ok": False, "origin": origin, "destination": destination,
                "mode": mode,
                "error": f"{d.get('status')} — {d.get('error_message', 'no route found')}"}
    leg = d["routes"][0]["legs"][0]
    base = leg["duration"]["value"] / 60
    live = leg.get("duration_in_traffic", leg["duration"])["value"] / 60
    return {
        "ok": True,
        "origin": origin, "destination": destination, "mode": mode,
        "eta_min": round(live),
        "typical_min": round(base),
        "delay_min": round(live - base),
        "km": round(leg["distance"]["value"] / 1000, 1),
        "via": d["routes"][0].get("summary", ""),
    }


def commute() -> dict:
    """Live drive time for the configured commute: HOME -> WORK. Returns the
    same dict shape as directions(). Both endpoints come from the environment
    ($MAPS_HOME / $MAPS_WORK)."""
    if not HOME or not WORK:
        raise MapsError(
            "commute() needs both $MAPS_HOME and $MAPS_WORK set. "
            "Use directions(origin, destination) to pass them explicitly."
        )
    return directions(HOME, WORK, "driving")


def search_places(query: str, open_now: bool = False, max_results: int = 8) -> list[dict]:
    """Search Google Places (New) by free-text query.

    Returns a list of plain dicts:
      {"name": str, "address": str, "rating": float|None, "open_now": bool|None}
    Empty list means no results.
    """
    body = {"textQuery": query, "languageCode": "he"}
    if open_now:
        body["openNow"] = True
    headers = {
        "X-Goog-Api-Key": _key(),
        "X-Goog-FieldMask": ("places.displayName,places.formattedAddress,"
                             "places.rating,places.currentOpeningHours.openNow"),
    }
    d = _post("https://places.googleapis.com/v1/places:searchText", body, headers)
    places = d.get("places", [])
    out: list[dict] = []
    for p in places[:max(1, min(max_results, 20))]:
        out.append({
            "name": p.get("displayName", {}).get("text", "?"),
            "address": p.get("formattedAddress", ""),
            "rating": p.get("rating"),
            "open_now": p.get("currentOpeningHours", {}).get("openNow"),
        })
    return out
