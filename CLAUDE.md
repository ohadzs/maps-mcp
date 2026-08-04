# maps-mcp — developer context

MCP server + CLI for Google Maps Platform, built to one rule: **a single I/O-free core, two thin
adapters.** No credentials or addresses belong in this repo — all of it is environment config.

## What this is
`maps_commute`, `maps_directions(origin, destination, mode)`,
`maps_search_places(query, open_now, max_results)`. One I/O-free `core.py`, plus an MCP adapter
(`server.py`) and a CLI adapter (`cli.py` → `maps-cli`). Live traffic-aware routing and place
search over Google's world data.

## Dev facts
- Run/serve (MCP): `uv run --directory /path/to/maps-mcp maps-mcp`. Entry `maps_mcp.server:main`.
- CLI: `uv run maps-cli <eta|route|places> …` (entry `maps_mcp.cli:main`); add `--json` for raw dicts.
- Config is entirely environment: `GMAPS_KEY` (or `~/.gmaps_key`), `MAPS_HOME` / `MAPS_WORK`,
  `MAPS_DAILY_CAP`.

## Gotchas
- **World data only — not a personal Google Maps account.** Saved places, lists, Home/Work labels
  and Timeline have no public API; reach those through a signed-in browser.
- The per-day call cap (`MAPS_DAILY_CAP`, default 200) is the spend guard. Keep it.
- Restrict the API key to **Directions API + Places API (New)** in Google Cloud.
- The key never enters tool arguments, return values or logs, so it is never exposed to the model.
  Don't add a tool that would echo it.
