#!/usr/bin/env python3
"""Read the planning session's log into preprint-meta/data/session.json.

    python3 preprint-meta/scripts/session_data.py [path to the session's .jsonl]

The default path is the private copy kept for the run 5 paper (preprint-run5/private/, not in git).
Only times and sizes are written: the tokens in the model's context at each request, the compactions,
and when each human prompt arrived with its length and how it arrived. No prompt text, path or link
is copied. Times are Central (UTC-6), as hours of 11 November 2026.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PRE = Path(__file__).resolve().parent.parent
LOG = Path(sys.argv[1]) if len(sys.argv) > 1 else PRE.parent / "preprint-run5" / "private" / "planning-session.jsonl"
CT = timezone(timedelta(hours=-6))
DAY0 = datetime(2026, 11, 11, 0, 0, tzinfo=CT)
LO, HI = 6.0, 21.2  # the planning day, hours Central


def hour(ts):
    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (t - DAY0).total_seconds() / 3600


ctx, compactions, prompts, rows = [], [], [], 0
for line in LOG.open():
    try:
        r = json.loads(line)
    except ValueError:
        continue
    rows += 1
    ts = r.get("timestamp")
    if not ts:
        continue
    h = hour(ts)
    if not LO <= h <= HI:
        continue
    if r.get("type") == "system" and r.get("subtype") == "compact_boundary":
        m = r.get("compactMetadata") or {}
        compactions.append({"h": round(h, 4), "trigger": m.get("trigger"), "pre": m.get("preTokens"), "post": m.get("postTokens"),
                            "seconds": round((m.get("durationMs") or 0) / 1000)})
    elif r.get("type") == "assistant" and not r.get("isSidechain"):
        msg = r.get("message") or {}
        u = msg.get("usage")
        if u and msg.get("model") != "<synthetic>":
            n = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            ctx.append([round(h, 4), n])
    elif r.get("type") == "user" and not r.get("isMeta") and not r.get("isCompactSummary") and r.get("promptSource"):
        c = (r.get("message") or {}).get("content")
        if isinstance(c, list):
            c = "\n".join(x.get("text", "") for x in c if x.get("type") == "text")
        if c and c.strip():
            prompts.append({"h": round(h, 4), "chars": len(c), "source": r["promptSource"]})

out = {
    "_note": "From the planning session's log (Claude Code, session ddd0eb9a). Hours are Central time on 11 November 2026. "
             "ctx is [hour, tokens in the context at that request]. Written by scripts/session_data.py.",
    "window_hours": [LO, HI],
    "log_rows_read": rows,
    "requests": len(ctx),
    "peak_tokens": max(n for _, n in ctx),
    "ctx": ctx,
    "compactions": compactions,
    "prompts": prompts,
}
(PRE / "data" / "session.json").write_text(json.dumps(out, indent=1))
print(f"{rows} rows read; {len(ctx)} requests, {len(compactions)} compactions, {len(prompts)} prompts in the window; peak {out['peak_tokens']}")
for c in compactions:
    print(c)
print([(round(p['h'], 2), p['chars'], p['source']) for p in prompts])
