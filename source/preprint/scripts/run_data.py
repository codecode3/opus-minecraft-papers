#!/usr/bin/env python3
"""Pull the numbers the preprint needs out of a finished run's records.

    python3 preprint/scripts/run_data.py [RUN_DIR]   -> preprint/data/run.json

Reads only: records/{events,programs,agent-stream}.jsonl, server/camera/frames.jsonl,
the workspace's git log. Times are hours since the first program unless named *_utc.
"""
import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PRE = Path(__file__).resolve().parent.parent
RUN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (PRE.parent / "runs" / "2026-11-01-1211").resolve()
REC = RUN / "records"


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def jl(p):
    out = []
    for line in Path(p).read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


events = jl(REC / "events.jsonl")
programs = jl(REC / "programs.jsonl")
t0 = ts(programs[0]["startedAt"])
win = next(ts(e["t"]) for e in events if e["type"] == "win")
H = lambda t: (t - t0).total_seconds() / 3600


def cause(text):
    t = text.lower()
    rules = [
        ("Dragon breath", "ender dragon using magic"), ("Dragon (fall, contact)", "by ender dragon"),
        ("Void", "out of the world"), ("Void", "same world as"), ("Drowning", "drown"),
        ("Lava and fire", "lava"), ("Lava and fire", "burn"), ("Lava and fire", "crisp"), ("Lava and fire", "flames"),
        ("Skeletons", "skeleton"), ("Zombies", "zombie"), ("Creepers", "creeper"), ("Spiders", "spider"),
        ("Silverfish", "silverfish"), ("Piglins", "piglin"), ("Endermen", "enderman"), ("Blazes", "blaze"),
        ("Pillagers", "pillager"), ("Hoglins", "hoglin"), ("Falls", "fell"), ("Falls", "hit the ground"),
        ("Falls", "doomed to fall"), ("Suffocation", "suffocat"),
    ]
    for label, key in rules:
        if key in t:
            return label
    return "Other"


deaths = [{"h": H(ts(e["t"])), "text": e["text"], "cause": cause(e["text"])}
          for e in events if e["type"] == "death" and ts(e["t"]) <= win]
milestones = {e["key"]: H(ts(e["t"])) for e in events if e["type"] == "milestone"}
advancements = [{"h": H(ts(e["t"])), "name": e["text"]} for e in events
                if e["type"] == "advancement" and ts(e["t"]) <= win]

before = [p for p in programs if ts(p["startedAt"]) <= win]
is_check = lambda p: "L.bot===bot" in p["code"] and len(p["code"]) < 120
real = [p for p in before if not is_check(p)]
per_half_hour = Counter(int(H(ts(p["startedAt"])) * 2) for p in real)
dur = [p["durationMs"] / 1000 for p in real if p.get("durationMs") is not None]
lines = {l.strip() for p in before for l in p["code"].splitlines() if l.strip()}

# Dragon health as the agent's programs read it: dInfo JSON ("hp":N) and the fight log (D<n>/ph).
dragon = []
for p in before:
    if ts(p["startedAt"]) < ts("2026-11-03T10:40:00Z"):
        continue
    out = (p.get("output") or "") + "\n" + str(p.get("returned") or "")
    vals = [float(v) for v in re.findall(r'"phase":-?\d+,"hp":([\d.]+)\}', out)]
    vals += [float(v) for v in re.findall(r"\bD([\d.]+)/ph-?\d", out)]
    if vals:
        dragon.append({"h": H(ts(p["endedAt"] or p["startedAt"])), "hp": vals[-1], "min": min(vals)})

# Context size, tokens and compactions from the agent's stream.
seen, ctx, compactions = set(), [], []
last_t = None
for d in jl(REC / "agent-stream.jsonl"):
    if d.get("type") == "assistant":
        m = d["message"]
        if d.get("timestamp"):
            last_t = ts(d["timestamp"])
        u = m.get("usage") or {}
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        c = (u.get("input_tokens", 0) or 0) + (u.get("cache_read_input_tokens", 0) or 0) + (u.get("cache_creation_input_tokens", 0) or 0)
        if last_t and last_t <= win:
            ctx.append([round(H(last_t), 4), c])
    elif d.get("type") == "system" and d.get("subtype") == "compact_boundary":
        md = d.get("compact_metadata") or {}
        compactions.append({"h": H(last_t) if last_t else None, "pre": md.get("pre_tokens"), "post": md.get("post_tokens"),
                            "trigger": md.get("trigger")})
ctx = ctx[::max(1, len(ctx) // 2500)]
# Stream lines carry partial output counts, so token totals come from the session transcript.
sid = json.loads((RUN / "run.json").read_text())["sessionId"]
tr = next(Path.home().glob(f".claude/projects/*/{sid}.jsonl"), REC / "transcripts" / f"{sid}.jsonl")
per_msg = {}
for d in jl(tr):
    if d.get("type") != "assistant" or (d.get("timestamp") and ts(d["timestamp"]) > win):
        continue
    u = d["message"].get("usage") or {}
    best = per_msg.setdefault(d["message"].get("id"), Counter())
    for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"):
        best[k] = max(best[k], u.get(k, 0) or 0)
    best["thinking_tokens"] = max(best["thinking_tokens"], (u.get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0)
tok = Counter()
for best in per_msg.values():
    tok.update(best)
tok["api_responses"] = len(per_msg)

frames = jl(RUN / "server" / "camera" / "frames.jsonl")
commits = subprocess.run(["git", "-C", str(RUN / "workspace"), "log", "--reverse", "--format=%cI|%s"],
                         capture_output=True, text=True).stdout.splitlines()

out = {
    "t0_utc": t0.isoformat(), "win_utc": win.isoformat(), "win_h": H(win),
    "milestones": milestones, "advancements": advancements, "deaths": deaths,
    "death_causes": Counter(d["cause"] for d in deaths).most_common(),
    "programs": {"before_win": len(before), "library_checks": len(before) - len(real), "real": len(real),
                 "errors_real": sum(1 for p in real if p.get("error")), "median_s_real": statistics.median(dur),
                 "distinct_lines": len(lines), "after_win": len(programs) - len(before),
                 "per_half_hour": sorted(per_half_hour.items())},
    "dragon": dragon, "ctx": ctx, "compactions": compactions, "tokens": dict(tok),
    "frames": {"count": len(frames), "first_utc": frames[0]["t"], "last_utc": frames[-1]["t"]},
    "commits": len(commits),
}
(PRE / "data").mkdir(exist_ok=True)
(PRE / "data" / "run.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("win_h", "milestones", "death_causes", "programs", "compactions", "tokens", "frames", "commits")},
                 indent=1, default=str)[:4000])
print("deaths", len(deaths), "dragon readings", len(dragon), "ctx points", len(ctx))
