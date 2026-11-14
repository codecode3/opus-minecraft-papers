"""Write the public excerpt of each winning solo run's server log into records/.

Kept from the vanilla server log: every advancement line and every death line
of the player, with the official clock (time since the player's first spawn)
added in front. Left out: everything else, including chat, connection lines
(which hold addresses and coordinates), world generation and the seed. The
full records are private, so this needs the private run folders:

    python3 tools/make_records.py /path/to/minecraft-dragon/runs
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("America/Chicago")  # the server's clock
RUNS = {"run-1": "2026-11-01-1211", "run-2": "2026-11-04-1901", "run-4": "2026-11-06-2240", "run-5": "2026-11-11-2058"}
LINE = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] \[Server thread/INFO\]: (.*)$")
SKIP = ("joined the game", "left the game", "lost connection", "moved wrongly", "moved too quickly", "logged in with")


def clock(delta):
    s = int(delta.total_seconds())
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def excerpt(run_dir):
    events = [json.loads(l) for l in (run_dir / "records" / "events.jsonl").open()]
    first = next(e for e in events if e["type"] == "bot_connected")
    player = first["player"]
    spawn = datetime.fromisoformat(first["t"].replace("Z", "+00:00"))
    day, last, rows = spawn.astimezone(TZ).date(), None, []
    started = False
    for raw in (run_dir / "records" / "server.log").read_text().splitlines():
        m = LINE.match(raw)
        if not m:
            continue
        tod = timedelta(hours=int(m[1]), minutes=int(m[2]), seconds=int(m[3]))
        if last is not None and tod < last:
            day += timedelta(days=1)
        last = tod
        text = m[4]
        if not text.startswith(player + " ") or any(k in text for k in SKIP):
            continue
        at = datetime.combine(day, datetime.min.time(), TZ) + tod
        rows.append((at - spawn, text))
    return player, spawn, rows


if __name__ == "__main__":
    runs = Path(sys.argv[1])
    out = ROOT / "records"
    out.mkdir(exist_ok=True)
    for name, folder in RUNS.items():
        player, spawn, rows = excerpt(runs / folder)
        lines = [f"# {name}: advancement and death lines of player `{player}` from the server log",
                 f"# first spawn {spawn.strftime('%Y-%m-%dT%H:%M:%SZ')}; the clock in front is time since then (the log has whole seconds)", ""]
        lines += [f"{clock(d):>9}  {t}" for d, t in rows]
        (out / f"{name}-server-log.txt").write_text("\n".join(lines) + "\n")
        print(name, len(rows), "lines; last:", lines[-1])
