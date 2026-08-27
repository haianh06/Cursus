"""Ping the Render free-tier services on a loop so they don't spin down from
15 minutes of inactivity -- run this only while you actually want the app
warm (before/during a demo, testing session, etc.), not as a permanent
background process. Render's free plan grants 750 compute-hours/month
*shared across every free service in the workspace* -- keeping 2 services
alive 24/7 would burn through that in about 12-13 days and risk Render
suspending them for the rest of the month, which is worse than a cold start.
There is deliberately no scheduler/cron built into this script for that
reason: you start it, it runs, you stop it (Ctrl+C) when you're done.

Usage:
    python scripts/keep_alive.py             # loop forever, ping every 10 min
    python scripts/keep_alive.py --once      # ping once and exit (sanity check)
    python scripts/keep_alive.py --interval 300   # custom interval (seconds)
"""

from __future__ import annotations

import argparse
import time
import urllib.error
import urllib.request

TARGETS = {
    "cursus-backend": "https://cursus-backend-53yc.onrender.com/health",
    "cursus-ai-service": "https://cursus-ai-service.onrender.com/health",
}

# Must stay under Render's 15-minute inactivity spin-down window, with
# margin for a slow ping or a missed cycle.
DEFAULT_INTERVAL_SECONDS = 600


def ping(name: str, url: str, log) -> None:
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            elapsed = time.monotonic() - started
            log(f"  {name}: HTTP {response.status} ({elapsed:.1f}s)")
    except urllib.error.HTTPError as exc:
        elapsed = time.monotonic() - started
        log(f"  {name}: HTTP {exc.code} ({elapsed:.1f}s) -- reachable, not necessarily healthy")
    except Exception as exc:  # noqa: BLE001 -- network hiccups must not kill the loop
        elapsed = time.monotonic() - started
        log(f"  {name}: [x] {type(exc).__name__}: {exc} ({elapsed:.1f}s)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="ping once and exit")
    parser.add_argument(
        "--interval", type=int, default=DEFAULT_INTERVAL_SECONDS,
        help=f"seconds between pings (default {DEFAULT_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    def log(msg: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    if args.interval >= 900:
        log(f"  [!] interval={args.interval}s is >= Render's 15-min spin-down window -- services will still cold-start.")

    if args.once:
        log("Ping mot lan:")
        for name, url in TARGETS.items():
            ping(name, url, log)
        return

    log(f"Giu am {len(TARGETS)} service moi {args.interval}s -- Ctrl+C de dung.")
    log("Nho: chi nen chay khi thuc su can (demo/test) -- xem docstring ve gioi han 750h/thang cua Render free tier.")
    try:
        while True:
            for name, url in TARGETS.items():
                ping(name, url, log)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log("Da dung.")


if __name__ == "__main__":
    main()
