# maps-mcp

Google Maps Platform tooling — live traffic-aware routing and place search —
exposed to an LLM as an **MCP server** and to scripts as a **CLI**, off one
shared engine.

Built to a simple rule: **one I/O-free core, two thin adapters.** The core holds
all the logic and touches nothing; the adapters only translate.

## Architecture
```
  model ──▶  maps_mcp/server.py  (MCP adapter) ─┐
                                                ├─▶  maps_mcp/core.py  (I/O-free engine)
  cron  ──▶  maps_mcp/cli.py     (CLI adapter) ─┘
```
- **`maps_mcp/core.py`** — all the logic, I/O-free: reads the key, enforces the
  per-day cost cap, calls the Google APIs, returns plain dicts/lists. No
  printing, no argparse, no MCP. Functions: `directions(origin, destination, mode)`,
  `commute()`, `search_places(query, open_now, max_results)`. Raises `MapsError`.
- **`maps_mcp/server.py`** — thin MCP adapter; each tool calls `core.*` and
  formats the result.
- **`maps_mcp/cli.py`** — thin CLI adapter (`maps-cli`); same engine, for cron,
  scripts and piping.

## MCP tools
- `maps_commute` — live drive time between two configured endpoints.
- `maps_directions(origin, destination, mode)` — traffic-aware route between any
  two places (driving / walking / bicycling / transit).
- `maps_search_places(query, open_now, max_results)` — find businesses and POIs;
  returns name, address, rating, open-now.

## CLI
```bash
uv run maps-cli eta                                                  # alias: commute
uv run maps-cli route "<origin>" "<destination>" [--mode driving]    # alias: directions
uv run maps-cli places "<text query>" [--open-now] [--max 8]         # alias: search
```
Add `--json` to any command to print the raw core dict/list instead of text.

## Configuration
| Variable | Purpose |
|---|---|
| `GMAPS_KEY` or `~/.gmaps_key` (chmod 600) | Google Maps Platform API key |
| `MAPS_HOME` / `MAPS_WORK` | Endpoints for the `commute` shortcut |
| `MAPS_DAILY_CAP` | Per-day call cap, default `200` |

No addresses or keys are stored in this repo.

## Key & cost safety
- The key is read from disk or the environment. It never appears in tool
  arguments, return values or logs — so it is never exposed to the model.
- Restrict the key to **Directions API + Places API (New)** in Google Cloud.
- The per-day call cap makes runaway spend impossible; normal use stays well
  inside the free tier.

## What it is NOT
Not a connection to a **personal** Google Maps account. Saved places, lists,
Home/Work labels and Timeline have no public API — reach those through a
signed-in browser instead.

## Install + register
```bash
uv sync
uv run maps-mcp     # stdio server; Ctrl-C to stop
```
Register with an MCP client:
```json
{
  "mcpServers": {
    "maps": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/maps-mcp", "maps-mcp"]
    }
  }
}
```
Most clients need a restart to pick up new tools.

## Possible extensions
Enable Geocoding / Distance Matrix / Static Maps in the same Google Cloud
project (and add them to the key's API restriction) to expose more tools.
