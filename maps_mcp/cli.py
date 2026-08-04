"""CLI adapter for the Google Maps core — for cron / scripts / piping.

Same engine as the MCP server (``maps_mcp.core``); this just exposes it on the
command line.

Usage:
  maps-cli eta                                  # shortcut: $MAPS_HOME -> $MAPS_WORK
  maps-cli commute                              # alias of eta
  maps-cli route "<origin>" "<destination>" [--mode driving]
  maps-cli directions "<origin>" "<destination>" [--mode walking]   # alias of route
  maps-cli places "<text query>" [--open-now] [--max 8]
  maps-cli search "<text query>"                # alias of places

Add --json to any command to print the raw core dict/list instead of text.
"""
import sys
import json
import argparse

from . import core


def _print_directions(r: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r.get("ok") else 1
    if not r.get("ok"):
        print("error:", r.get("error"))
        return 1
    print(f"{r['origin']} -> {r['destination']} ({r['mode']})")
    print(f"  now: {r['eta_min']} min  (typical {r['typical_min']}, "
          f"+{r['delay_min']})  via {r['via']}  [{r['km']} km]")
    return 0


def _print_places(places: list, query: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps(places, ensure_ascii=False))
        return 0
    if not places:
        print("no results")
        return 0
    for p in places:
        flags = (f" ★{p['rating']}" if p["rating"] else "")
        openn = p["open_now"]
        flags += " • open now" if openn else (" • closed" if openn is False else "")
        print(f"• {p['name']} — {p['address']}{flags}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="maps-cli", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    for name in ("eta", "commute"):
        c = sub.add_parser(name, help="live drive time home -> work")
        c.add_argument("--json", action="store_true")

    for name in ("route", "directions"):
        c = sub.add_parser(name, help="traffic-aware route between two places")
        c.add_argument("origin")
        c.add_argument("destination")
        c.add_argument("--mode", default="driving",
                       choices=core.MODES)
        c.add_argument("--json", action="store_true")

    for name in ("places", "search"):
        c = sub.add_parser(name, help="search businesses / points of interest")
        c.add_argument("query")
        c.add_argument("--open-now", action="store_true")
        c.add_argument("--max", type=int, default=8, dest="max_results")
        c.add_argument("--json", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.cmd or "eta"
    try:
        if cmd in ("eta", "commute"):
            return _print_directions(core.commute(), args.json)
        if cmd in ("route", "directions"):
            return _print_directions(
                core.directions(args.origin, args.destination, args.mode), args.json)
        if cmd in ("places", "search"):
            places = core.search_places(args.query, open_now=args.open_now,
                                        max_results=args.max_results)
            return _print_places(places, args.query, args.json)
        parser.print_help()
        return 1
    except core.MapsError as e:
        print("error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
