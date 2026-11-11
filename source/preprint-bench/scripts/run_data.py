#!/usr/bin/env python3
"""Read the benchmark pair's records into preprint-bench/data/bench.json (system python3).

    python3 preprint-bench/scripts/run_data.py

All clock values are seconds on the official clock, from each player's first spawn.
"""
import datetime as dt
import json
import re
from pathlib import Path

PRE = Path(__file__).resolve().parent.parent
PAIR = "2026-11-10-1904-bench"
T = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def arm(name):
    d = PRE.parent / "runs" / f"{PAIR}-{name}"
    cfg = json.loads((d / "run.json").read_text())
    ev = [json.loads(l) for l in open(d / "records" / "events.jsonl")]
    t0 = T(next(e["t"] for e in ev if e["type"] == "bot_connected"))
    ck = lambda s: round((T(s) - t0).total_seconds())
    progs = [json.loads(l) for l in open(d / "records" / "programs.jsonl")]
    dims, last = [], None
    for p in progs:
        s = json.dumps(p.get("returned")) + (p.get("output") or "")
        m = re.findall(r"(overworld|the_nether|the_end)", s)
        if m and m[-1] != last:
            last = m[-1]
            dims.append([ck(p["startedAt"]), last])
    limits, stamp, last_real, usage, reqs = [], None, None, {}, 0
    for l in open(d / "records" / "agent-stream.jsonl"):
        e = json.loads(l)
        if e.get("timestamp"):
            stamp = e["timestamp"]
        msg = e.get("message") or {}
        if e.get("type") == "assistant" and msg.get("model") != "<synthetic>":
            last_real = stamp
        if e.get("type") == "rate_limit_event" and stamp:
            i = e["rate_limit_info"]
            w = (i.get("unifiedWindows") or {}).get("five_hour", {})
            limits.append({"clock": ck(stamp), "status": i.get("status"), "utilization": w.get("utilization"),
                           "resetsAt": w.get("resetsAt") or i.get("resetsAt")})
        if e.get("type") == "result":
            usage = {"cost": e.get("total_cost_usd"), "modelUsage": e.get("modelUsage"), "api_ms": e.get("duration_api_ms")}
    return {
        "name": name, "model": cfg["model"], "effort": cfg.get("effort"), "t0": t0.isoformat(),
        "milestones": [{"key": e["key"], "label": e["label"], "clock": ck(e["t"])} for e in ev if e["type"] == "milestone"],
        "deaths": [{"clock": ck(e["t"]), "text": e["text"]} for e in ev if e["type"] == "death"],
        "advancements": [{"clock": ck(e["t"]), "text": e.get("text", "")} for e in ev if e["type"] == "advancement"],
        "programs": len(progs), "program_errors": sum(1 for p in progs if p.get("error")),
        "program_timeouts": sum(1 for p in progs if p.get("timedOut")),
        "program_seconds": round(sum((p.get("durationMs") or 0) for p in progs) / 1000),
        "last_program": ck(progs[-1]["startedAt"]), "last_model_message": ck(last_real),
        "dims": dims, "limits": limits, "usage": usage,
    }


out = {"pair": PAIR, "arms": [arm("opus"), arm("fable")]}
(PRE / "data").mkdir(exist_ok=True)
(PRE / "data" / "bench.json").write_text(json.dumps(out, indent=1))
for a in out["arms"]:
    print(a["name"], "stopped", a["last_model_message"], "programs", a["programs"], "deaths", len(a["deaths"]),
          "cost", a["usage"].get("cost"), "prog s", a["program_seconds"])
    print("  ", {k: {x: v[x] for x in v if "okens" in x or x == "costUSD"} for k, v in (a["usage"].get("modelUsage") or {}).items()})
    seen = {}
    for x in a["limits"]:
        seen.setdefault(x["resetsAt"], []).append((x["clock"], x["utilization"]))
    for k, v in seen.items():
        print("   window reset", k, "first", v[0], "last", v[-1], "0.9 at", next((c for c, u in v if u and u >= 0.9), None))
