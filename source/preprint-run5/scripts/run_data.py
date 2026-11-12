#!/usr/bin/env python3
"""Read run 5's records into preprint-run5/data/run5.json (system python3).

    python3 preprint-run5/scripts/run_data.py

Clock values are seconds on the official clock, from the player's first spawn, and everything is cut
at the win unless a name says otherwise. The stage marks in STAGES are set by hand from the player's
own messages and its memory/01-targets.md, good to about a minute; the recovery spans start at the
death event and end where the player reported its kit back in hand.
"""
import datetime as dt
import json
import re
import statistics
from pathlib import Path

PRE = Path(__file__).resolve().parent.parent
PROJECT = PRE.parent
RUN = PROJECT / "runs" / "2026-11-11-2058"
T = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
hms = lambda s: f"{int(s) // 3600}:{int(s) % 3600 // 60:02d}:{int(s) % 60:02d}"
M = lambda h, m, s=0: h * 3600 + m * 60 + s

cfg = json.loads((RUN / "run.json").read_text())
ev = [json.loads(l) for l in open(RUN / "records" / "events.jsonl")]
t0 = T(next(e["t"] for e in ev if e["type"] == "bot_connected"))
ck = lambda s: (T(s) - t0).total_seconds()
win_e = next(e for e in ev if e["type"] == "win")
WIN = ck(win_e["t"])

milestones = [{"key": e["key"], "label": e["label"], "clock": round(ck(e["t"]))} for e in ev if e["type"] == "milestone"]
frames = [json.loads(l) for l in open(RUN / "server" / "camera" / "frames.jsonl")]
fr = [(ck(f["t"]), f["dim"]) for f in frames if f.get("dim")]
dims, last = [], None
for c, d in fr:
    if c > WIN:
        break
    if d != last:
        dims.append([round(c), d])
        last = d
dim_at = lambda c: [d for cc, d in fr if cc <= c][-1]
bot_deaths = [e for e in ev if e["type"] == "bot_death"]
deaths = []
for e in ev:
    if e["type"] == "death" and ck(e["t"]) <= WIN:
        c = ck(e["t"])
        deaths.append({"clock": round(c), "text": e["text"], "dim": dim_at(c - 2)})

pr_all = [json.loads(l) for l in open(RUN / "records" / "programs.jsonl")]
pr = [p for p in pr_all if ck(p["startedAt"]) <= WIN]
spans = sorted((ck(p["startedAt"]), min(ck(p["endedAt"]) if p.get("endedAt") else ck(p["startedAt"]), WIN)) for p in pr)
merged = []
for a, b in spans:
    if merged and a <= merged[-1][1]:
        merged[-1][1] = max(merged[-1][1], b)
    else:
        merged.append([a, b])
running = sum(b - a for a, b in merged)
durs = [p["durationMs"] / 1000 for p in pr if p.get("durationMs") is not None]
lines = set()
for p in pr:
    for ln in p["code"].splitlines():
        if ln.strip():
            lines.add(ln.strip())
programs = {
    "to_win": len(pr), "after_win": len(pr_all) - len(pr), "errors": sum(1 for p in pr if p.get("error")),
    "timeouts": sum(1 for p in pr if p.get("timedOut")), "median_s": round(statistics.median(durs), 1),
    "running_s": round(running), "running_share": round(running / WIN, 3), "idle_min": round((WIN - running) / 60, 1),
    "first_program_s": round(spans[0][0], 1), "distinct_lines": len(lines),
    "over_60s": sum(1 for d in durs if d >= 60), "under_5s": sum(1 for d in durs if d < 5),
    "spans": [[round(a), round(b)] for a, b in merged],
}

# Context size through the run: input tokens of each model request, from the session transcript.
tr = RUN / "records" / "transcripts" / f"{cfg['sessionId']}.jsonl"
context, tools, seen, turns = [], {}, set(), 0
for l in open(tr):
    e = json.loads(l)
    if e.get("type") != "assistant" or not e.get("timestamp"):
        continue
    msg = e["message"]
    for c in msg["content"]:
        if c["type"] == "tool_use":
            tools[c["name"]] = tools.get(c["name"], 0) + 1
    if msg.get("id") in seen:
        continue
    seen.add(msg.get("id"))
    u = msg.get("usage") or {}
    tot = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
    c = ck(e["timestamp"])
    if tot and c <= WIN + 180:
        context.append([round(c), tot])
        turns += c <= WIN
compactions, stamp, usage, texts, limits = [], None, {}, [], []
for l in open(RUN / "records" / "agent-stream.jsonl"):
    e = json.loads(l)
    if e.get("timestamp"):
        stamp = e["timestamp"]
    if e.get("type") == "system" and e.get("subtype") == "compact_boundary":
        m = e.get("compact_metadata") or {}
        compactions.append({"clock": round(ck(stamp)), "pre": m.get("pre_tokens"), "post": m.get("post_tokens"),
                            "seconds": round((m.get("duration_ms") or 0) / 1000), "trigger": m.get("trigger")})
    if e.get("type") == "rate_limit_event" and stamp:
        i = e["rate_limit_info"]
        w = i.get("unifiedWindows") or {}
        limits.append({"clock": round(ck(stamp)), "status": i.get("status"),
                       "five_hour": (w.get("five_hour") or {}).get("utilization"), "five_hour_resets_s": round((w.get("five_hour") or {}).get("resetsAt", 0) - t0.timestamp()),
                       "seven_day": (w.get("seven_day") or {}).get("utilization")})
    if e.get("type") == "result":
        usage = {"cost_usd": e.get("total_cost_usd"), "duration_ms": e.get("duration_ms"), "api_ms": e.get("duration_api_ms"),
                 "turns": e.get("num_turns"), "model": e.get("modelUsage")}
    if e.get("type") == "system" and e.get("subtype") == "init":
        usage_init = {"model": e.get("model")}
reads = []
for l in open(tr):
    e = json.loads(l)
    if e.get("type") == "assistant" and e.get("timestamp"):
        for c in e["message"]["content"]:
            if c["type"] == "tool_use" and c["name"] == "Read":
                reads.append([round(ck(e["timestamp"])), c["input"].get("file_path", "").split("workspace/")[-1]])

# Stage marks, by hand (see the docstring). recover = [death, kit back]; food = the unforeseen food work.
STAGES = [
    {"key": "to_nether", "label": "To Nether entry", "a": 0, "b": M(0, 35, 19), "target_end": M(0, 44)},
    {"key": "fort_rods", "label": "Fortress and 7 rods", "a": M(0, 35, 19), "b": M(0, 55), "target_end": M(1, 14)},
    {"key": "pearls", "label": "13 pearls", "a": M(0, 55), "b": M(1, 34, 30), "target_end": M(1, 44), "recover": [[M(0, 58, 28), M(1, 6, 30)]]},
    {"key": "home_eyes", "label": "Home: eyes, two throws", "a": M(1, 34, 30), "b": M(1, 45), "target_end": M(1, 51)},
    {"key": "crossing", "label": "Crossing, base, End entry", "a": M(1, 45), "b": M(3, 32, 41), "target_end": M(2, 26),
     "recover": [[M(2, 11, 13), M(3, 5)]], "food": [[M(2, 5), M(2, 11, 13)], [M(3, 5), M(3, 27)]]},
    {"key": "crystals", "label": "Ten crystals", "a": M(3, 32, 41), "b": M(3, 42), "target_end": M(2, 44)},
    {"key": "dragon", "label": "Dragon", "a": M(3, 42), "b": round(WIN), "target_end": M(2, 59), "recover": [[M(4, 16, 52), M(4, 23, 20)], [M(4, 25, 8), M(4, 31, 30)]]},
]
prior = json.loads((PROJECT / "bayes" / "prior.json").read_text())["no_preparation_player"]
for s in STAGES:
    rec = sum(b - a for a, b in s.get("recover", []))
    food = sum(b - a for a, b in s.get("food", []))
    s["clock_min"] = round((s["b"] - s["a"]) / 60, 1)
    s["recover_min"] = round(rec / 60, 1)
    s["food_min"] = round(food / 60, 1)
    s["work_min"] = round((s["b"] - s["a"] - rec) / 60, 1)
    s["work_less_food_min"] = round((s["b"] - s["a"] - rec - food) / 60, 1)
    s["prior"] = prior["predictive"]["stage_minutes"][s["key"]]

r4 = json.loads((PROJECT / "preprint-run4" / "data" / "run4.json").read_text())["runs"]
bench = json.loads((PROJECT / "preprint-bench" / "data" / "bench.json").read_text())["arms"]
earlier = {k: {"won": r4[k]["won"], "official_s": round(r4[k]["official_h"] * 3600),
               "milestones": {m: round(h * 3600) for m, h in r4[k]["milestones"].items() if h is not None}} for k in ("run2", "run4")}
for a in bench:
    earlier["bench_" + a["name"]] = {"won": False, "official_s": None, "deaths": len([d for d in a["deaths"] if d["clock"] <= a["last_model_message"]]),
                                     "stopped_s": a["last_model_message"], "milestones": {m["key"]: m["clock"] for m in a["milestones"]}}

ws = RUN / "workspace"
count = lambda d: sum(len(f.read_text(errors="replace").splitlines()) for f in d.glob("*") if f.is_file() and not f.name.startswith("."))
out = {
    "run": cfg["runId"], "model": cfg["model"], "effort": cfg["effort"], "t0_utc": t0.isoformat(), "win_s": round(WIN, 1),
    "win_clock": hms(WIN), "from_first_program_s": round(win_e["elapsedFromFirstProgramMs"] / 1000, 1),
    "milestones": milestones, "deaths": deaths, "dims": dims, "programs": programs, "context": context,
    "context_max": max(c[1] for c in context), "turns_to_win": turns, "compactions": compactions, "usage": usage, "tools": tools,
    "reads": reads, "limits": limits, "stages": STAGES, "prior": prior, "earlier": earlier, "inherit": cfg["inheritFrom"],
    "workspace": {"lib_files": len(list((ws / "lib").glob("*"))), "lib_lines": count(ws / "lib"), "prog_files": len(list((ws / "prog").glob("*"))),
                  "prog_lines": count(ws / "prog"), "lessons_lines": len((ws / "memory" / "02-lessons.md").read_text().splitlines())},
}
(PRE / "data").mkdir(exist_ok=True)
(PRE / "data" / "run5.json").write_text(json.dumps(out, indent=1))
print("win", out["win_clock"], "programs", programs["to_win"], "errors", programs["errors"], "timeouts", programs["timeouts"],
      "median", programs["median_s"], "running", programs["running_share"], "idle min", programs["idle_min"], "lines", programs["distinct_lines"])
print("first program s", programs["first_program_s"], "over60", programs["over_60s"], "under5", programs["under_5s"], "turns", turns, "ctx max", out["context_max"])
print("deaths", deaths)
print("dims", [(hms(c), d) for c, d in dims])
print("compactions", compactions)
print("usage", {k: v for k, v in usage.items() if k != "model"}, usage["model"])
print("limits", len(limits), "refused", sum(1 for x in limits if x["status"] != "allowed"), "peak", max(x["five_hour"] for x in limits), [x for x in limits if x["five_hour"] == max(y["five_hour"] for y in limits)][0], limits[0], limits[-1])
print("tools", tools, "reads", reads)
for s in STAGES:
    print(f"{s['key']:<10} clock {s['clock_min']:6} recover {s['recover_min']:5} food {s['food_min']:5} work {s['work_min']:6} less food {s['work_less_food_min']:6} prior {s['prior']}")
print("earlier", {k: (v["official_s"], v["milestones"]) for k, v in earlier.items()})
print(out["workspace"])
