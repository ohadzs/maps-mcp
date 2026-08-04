"""Google Maps Platform MCP server (Directions + Places) — thin adapter.

Local stdio MCP server giving Claude live, traffic-aware routing and place
search via a Google Maps Platform API key. All logic lives in
``maps_mcp.core``; this module only registers the MCP tools and formats the
core results into human-readable strings. The key is read from ~/.gmaps_key
(or $GMAPS_KEY) — it never appears in tool arguments or output.

NOT a connection to a personal Google Maps account (saved places / lists /
Timeline have no public API — reach those via the browser, signed in).

Cost safety: a per-day call cap (MAPS_DAILY_CAP, default 200) lives in core and
makes runaway spend impossible; usage stays far under the free 10k/month tier.
"""
from mcp.server.fastmcp import FastMCP

from . import core

mcp = FastMCP("maps")


def _fmt_directions(r: dict) -> str:
    if not r.get("ok"):
        return f"Error: {r.get('error')}"
    delay = r["delay_min"]
    note = "clear" if delay <= 2 else f"+{delay} min vs typical ({r['typical_min']})"
    return (f"{r['origin']} → {r['destination']} ({r['mode']})\n"
            f"Now: {r['eta_min']} min, {r['km']} km, via {r['via']} — {note}.")


@mcp.tool()
def maps_commute() -> str:
    """Live traffic-aware drive time for the configured commute ($MAPS_HOME →
    $MAPS_WORK). Use for 'how long to work
    right now?' / 'should I leave?'."""
    return _fmt_directions(core.commute())


@mcp.tool()
def maps_directions(origin: str, destination: str, mode: str = "driving") -> str:
    """Live traffic-aware route between any two places. origin/destination are
    free-text addresses or place names (Hebrew or English). mode is one of
    driving, walking, bicycling, transit. Returns ETA (with current traffic),
    distance, and the main road used."""
    return _fmt_directions(core.directions(origin, destination, mode))


@mcp.tool()
def maps_search_places(query: str, open_now: bool = False, max_results: int = 8) -> str:
    """Search Google Places for businesses / points of interest by free-text
    query (e.g. 'pharmacy near Times Square', 'ramen Tel Aviv'). Set
    open_now=true to keep only currently-open results. Returns name, address,
    rating, and open/closed status."""
    places = core.search_places(query, open_now=open_now, max_results=max_results)
    if not places:
        return f"No places found for: {query}"
    lines = []
    for p in places:
        tail = (f" ★{p['rating']}" if p["rating"] else "")
        openn = p["open_now"]
        tail += " · open now" if openn else (" · closed" if openn is False else "")
        lines.append(f"• {p['name']} — {p['address']}{tail}")
    return "\n".join(lines)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
