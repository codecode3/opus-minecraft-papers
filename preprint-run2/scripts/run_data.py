#!/usr/bin/env python3
"""Pull the numbers the run 2 preprint needs out of both runs' records.

    python3 preprint-run2/scripts/run_data.py   -> preprint-run2/data/run2.json

Reads only. Run 2 is runs/2026-11-04-1901, the baseline is runs/2026-11-01-1211. The same
functions measure both, so a difference between the two is not a difference in method.
Statistics that resample use a fixed seed, so a rerun gives the same numbers.
Times are hours since each run's first program unless named *_utc. Everything is cut at the
win; what the agent did after it is kept apart under "after_win".
"""
import json
import math
import random
import re
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PRE = Path(__file__).resolve().parent.parent
PROJECT = PRE.parent
RUN2 = PROJECT / "runs" / "2026-11-04-1901"
RUN1 = PROJECT / "runs" / "2026-11-01-1211"
INH = "inherited/2026-11-01-1211"


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


def cause(text):
    """The first preprint's rule list, in its order, so run 1's counts stay as published. The last two rows are new: run 1 never died that way."""
    t = text.lower()
    rules = [
        ("Dragon breath", "ender dragon using magic"), ("Dragon (fall, contact)", "by ender dragon"),
        ("Void", "out of the world"), ("Void", "same world as"), ("Drowning", "drown"),
        ("Lava and fire", "lava"), ("Lava and fire", "burn"), ("Lava and fire", "crisp"), ("Lava and fire", "flames"),
        ("Skeletons", "skeleton"), ("Zombies", "zombie"), ("Creepers", "creeper"), ("Spiders", "spider"),
        ("Silverfish", "silverfish"), ("Piglins", "piglin"), ("Endermen", "enderman"), ("Blazes", "blaze"),
        ("Pillagers", "pillager"), ("Hoglins", "hoglin"), ("Falls", "fell"), ("Falls", "hit the ground"),
        ("Falls", "doomed to fall"), ("Suffocation", "suffocat"), ("Withering", "withered"), ("Stalactite", "stalactite"),
    ]
    for label, key in rules:
        if key in t:
            return label
    return "Other"


def transcript(run):
    sid = json.loads((run / "run.json").read_text())["sessionId"]
    return next(Path.home().glob(f".claude/projects/*/{sid}.jsonl"), run / "records" / "transcripts" / f"{sid}.jsonl")


def measure(run):
    """The measures compared between the runs. Same definitions for both."""
    rec = run / "records"
    events = jl(rec / "events.jsonl")
    programs = jl(rec / "programs.jsonl")
    t0 = ts(programs[0]["startedAt"])
    win = next(ts(e["t"]) for e in events if e["type"] == "win")
    H = lambda t: (t - t0).total_seconds() / 3600
    before = [p for p in programs if ts(p["startedAt"]) <= win]
    is_check = lambda p: "L.bot===bot" in p["code"] and len(p["code"]) < 120
    real = [p for p in before if not is_check(p)]
    spans = sorted((ts(p["startedAt"]), ts(p["endedAt"]) if p.get("endedAt") else ts(p["startedAt"])) for p in before)
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    running = sum((b - a).total_seconds() for a, b in merged)
    total = (win - t0).total_seconds()
    pauses = [(merged[i + 1][0] - merged[i][1]).total_seconds() for i in range(len(merged) - 1)]
    deaths = []
    for e in events:
        if e["type"] != "death" or ts(e["t"]) > win:
            continue
        t = ts(e["t"])
        if t < t0:  # run 1's first death came before its first program: counts in the total, not in the pause analysis
            deaths.append({"h": H(t), "text": e["text"], "cause": cause(e["text"]), "in_program": False, "since_program_end_s": None, "before_first_program": True})
            continue
        running_now = any(a <= t <= b for a, b in merged)
        ended = [b for a, b in merged if b <= t]
        since = (t - ended[-1]).total_seconds() if ended and not running_now else None
        deaths.append({"h": H(t), "text": e["text"], "cause": cause(e["text"]), "in_program": running_now, "since_program_end_s": since})
    durs = [p["durationMs"] / 1000 for p in real if p.get("durationMs") is not None]
    lines = {l.strip() for p in before for l in p["code"].splitlines() if l.strip()}
    miles = {e["key"]: H(ts(e["t"])) for e in events if e["type"] == "milestone"}
    in_pause = [d for d in deaths if not d["in_program"] and not d.get("before_first_program")]
    return {
        "t0_utc": t0.isoformat(), "win_utc": win.isoformat(), "win_h": H(win), "milestones": miles,
        "advancements": [{"h": H(ts(e["t"])), "name": e["text"]} for e in events if e["type"] == "advancement" and ts(e["t"]) <= win],
        "deaths": deaths, "deaths_after_first_program": sum(1 for d in deaths if not d.get("before_first_program")), "death_causes": Counter(d["cause"] for d in deaths).most_common(),
        "programs": {"before_win": len(before), "library_checks": len(before) - len(real), "real": len(real),
                     "errors": sum(1 for p in before if p.get("error")), "timed_out": sum(1 for p in before if p.get("timedOut")),
                     "median_s_real": statistics.median(durs), "distinct_lines": len(lines), "after_win": len(programs) - len(before),
                     "per_half_hour": sorted(Counter(int(H(ts(p["startedAt"])) * 2) for p in real).items())},
        "running_share": running / total, "running_h": running / 3600,
        "pauses": {"n": len(pauses), "median_s": statistics.median(pauses), "mean_s": statistics.mean(pauses),
                   "p90_s": sorted(pauses)[int(len(pauses) * .9)], "longest_s": max(pauses), "total_h": sum(pauses) / 3600},
        "deaths_in_pause": {"n": len(in_pause), "within_10s": sum(1 for d in in_pause if d["since_program_end_s"] is not None and d["since_program_end_s"] <= 10)},
    }


def tokens(run, win):
    per = {}
    for d in jl(transcript(run)):
        if d.get("type") != "assistant" or (d.get("timestamp") and ts(d["timestamp"]) > win):
            continue
        u = d["message"].get("usage") or {}
        best = per.setdefault(d["message"].get("id"), Counter())
        for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"):
            best[k] = max(best[k], u.get(k, 0) or 0)
        best["thinking_tokens"] = max(best["thinking_tokens"], (u.get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0)
        cc = u.get("cache_creation") or {}
        best["cache_1h"] = max(best["cache_1h"], cc.get("ephemeral_1h_input_tokens", 0) or 0)
        best["cache_5m"] = max(best["cache_5m"], cc.get("ephemeral_5m_input_tokens", 0) or 0)
    tok = Counter()
    for b in per.values():
        tok.update(b)
    tok["api_responses"] = len(per)
    return dict(tok)


run2 = measure(RUN2)
run1 = measure(RUN1)
T0, WIN = ts(run2["t0_utc"]), ts(run2["win_utc"])
H2 = lambda t: (t - T0).total_seconds() / 3600
programs2 = jl(RUN2 / "records" / "programs.jsonl")
before2 = [p for p in programs2 if ts(p["startedAt"]) <= WIN]
events2 = jl(RUN2 / "records" / "events.jsonl")
frames2 = jl(RUN2 / "server" / "camera" / "frames.jsonl")

# --- Where each death happened: the last camera frame at or before it.
fr_t = [(ts(f["t"]), f) for f in frames2]
for d in run2["deaths"]:
    t = T0.timestamp() + d["h"] * 3600
    last = [f for tt, f in fr_t if tt.timestamp() <= t]
    d["dim"] = last[-1]["dim"] if last else None
    d["pos"] = last[-1]["pos"] if last else None
run2["deaths_by_dim"] = Counter(d["dim"] for d in run2["deaths"]).most_common()
gaps = [(fr_t[i + 1][0] - fr_t[i][0]).total_seconds() for i in range(len(fr_t) - 1) if fr_t[i + 1][0] <= WIN]
run2["frames"] = {"to_win": sum(1 for t, _ in fr_t if t <= WIN), "total": len(frames2), "max_gap_s": max(gaps), "median_gap_s": statistics.median(gaps),
                  "share_by_dim": Counter(f["dim"] for t, f in fr_t if T0 <= t <= WIN).most_common()}

# --- Tool calls and what they touched.
tr2 = jl(transcript(RUN2))
calls = []
first_event = None
for d in tr2:
    if d.get("timestamp") and first_event is None:
        first_event = ts(d["timestamp"])
    if d.get("type") == "assistant" and isinstance(d["message"].get("content"), list):
        for b in d["message"]["content"]:
            if b.get("type") == "tool_use" and ts(d["timestamp"]) <= WIN:
                calls.append({"t": ts(d["timestamp"]), "name": b["name"], "input": b["input"]})
run2["tool_calls"] = Counter(c["name"] for c in calls).most_common()
run2["prep_s"] = (T0 - first_event).total_seconds()


def area(s):
    """Which part of the inherited folder a read or a command names; a command can name several."""
    found = set()
    for key, pat in [("memory", r"workspace/memory|\bmemory/(lessons|progress)|lessons\.md|progress\.md"), ("lib", r"workspace/lib|\$INH|lib/"),
                     ("programs/events/server log", r"programs\.jsonl|events\.jsonl|server\.log|records/report|report\.md"),
                     ("conversation", r"transcripts|readable|agent-stream"), ("preprint", r"preprint"),
                     ("git history", r"git -C|git log|\.git\b"), ("camera", r"camera"), ("index", r"INDEX\.md")]:
        if re.search(pat, s):
            found.add(key)
    return found or {"other"}


def reads_inherited(c):
    """The lines of a tool call that read the inherited folder. The plan quotes the folder's path in its "Find it:" routing line;
    writing that line down is not a read. Checked by hand: every other matching line during the run is a real read."""
    if c["name"] in ("Read", "Grep", "Glob"):
        return [str(c["input"].get("file_path") or c["input"].get("path") or "")] if "inherited" in str(c["input"]) else []
    return [l for l in str(c["input"].get("command") or "").splitlines() if re.search(r"inherited|\$INH\b|\bINH=", l) and "Find it:" not in l]


inh_calls = []
for c in calls:
    lines = reads_inherited(c)
    if lines:
        s_ = "\n".join(lines)
        inh_calls.append({"h": H2(c["t"]), "tool": c["name"], "areas": sorted(area(s_)), "before_first_program": c["t"] < T0, "text": s_[:400]})
in_run = [x for x in inh_calls if not x["before_first_program"]]
run2["inherited_use"] = {"calls": len(inh_calls), "before_first_program": len(inh_calls) - len(in_run), "during_run": len(in_run),
                         "areas_before": Counter(a for x in inh_calls if x["before_first_program"] for a in x["areas"]).most_common(),
                         "areas_during": Counter(a for x in in_run for a in x["areas"]).most_common(),
                         "during_hours": [round(x["h"], 3) for x in in_run],
                         "during_text": [{"h": round(x["h"], 2), "text": x["text"].replace(str(PROJECT) + "/", "")[:220]} for x in in_run],
                         "read_camera_frames": any("camera-frames" in x["text"] or "camera/frames" in x["text"] for x in inh_calls),
                         "read_readme_prediction": any(re.search(r"minecraft-dragon/README|\.\./README|15.{1,3}25", (c["input"].get("file_path") or c["input"].get("command") or "")) for c in calls)}

# --- The library: what it took from run 1's, and how much it wrote.
def lib_lines(folder):
    out = {}
    for f in sorted(Path(folder).glob("*")):
        if f.is_file() and f.suffix in (".js", ".sh") and not f.name.startswith("."):
            out[f.name] = [l.strip() for l in f.read_text(errors="replace").splitlines() if l.strip() and not l.strip().startswith("//")]
    return out


lib1 = lib_lines(RUN1 / "workspace" / "lib")
lib2 = lib_lines(RUN2 / "workspace" / "lib")
set1 = {l for ls in lib1.values() for l in ls}
lines2 = sum(len(v) for v in lib2.values())
kept2 = sum(1 for v in lib2.values() for l in v if l in set1)
per_file = []
for name, ls in sorted(lib2.items(), key=lambda kv: -len(kv[1])):
    same = set(lib1.get(name, []))
    per_file.append({"file": name, "lines": len(ls), "in_run1_file": name in lib1, "identical_lines": sum(1 for l in ls if l in set1),
                     "from_same_file": sum(1 for l in ls if l in same), "unchanged": name in lib1 and lib1[name] == ls})
ws = RUN2 / "workspace"
git = lambda *a: subprocess.run(["git", "-C", str(ws), *a], capture_output=True, text=True).stdout
log = [l.split("|", 2) for l in git("log", "--reverse", "--format=%h|%cI|%s").splitlines()]
series = []
for h, when, subj in log:
    n, fs, kept_c = 0, 0, 0
    for path in git("ls-tree", "-r", "--name-only", h, "lib").splitlines():
        if path.endswith((".js", ".sh")) and not Path(path).name.startswith("."):
            fs += 1
            ls_c = [l.strip() for l in git("show", f"{h}:{path}").splitlines() if l.strip() and not l.strip().startswith("//")]
            n += len(ls_c)
            kept_c += sum(1 for l in ls_c if l in set1)
    plan = git("show", f"{h}:memory/00-plan.md")
    lessons = git("show", f"{h}:memory/02-lessons.md")
    targets = git("show", f"{h}:memory/01-targets.md")
    series.append({"hash": h, "h": H2(ts(when)), "subject": subj, "lib_lines": n, "lib_files": fs, "lib_identical": kept_c, "plan_chars": len(plan), "lessons_lines": len(lessons.splitlines()), "targets_chars": len(targets)})
start = next(s for s in series if s["lib_lines"] > 0)
first_hash = start["hash"]
first_lib = {Path(p).name for p in git("ls-tree", "-r", "--name-only", first_hash, "lib").splitlines()}
# Calls into the library from programs, by whether run 1's library defines that name.
defined1 = set(re.findall(r"\bL\.(\w+)\s*=", "\n".join(f.read_text(errors="replace") for f in (RUN1 / "workspace" / "lib").glob("*.js"))))
defined2 = set(re.findall(r"\bL\.(\w+)\s*=", "\n".join(f.read_text(errors="replace") for f in (RUN2 / "workspace" / "lib").glob("*.js") if not f.name.startswith("."))))
called = Counter()
for p in before2:
    if "Core helpers. Install" in p["code"][:200] or len(p["code"]) > 20000:  # library installs, not calls
        continue
    for n in set(re.findall(r"\bL\.(\w+)", p["code"])):
        called[n] += 1
NOT_FUNCTIONS = {"bot", "Vec3", "goals", "gen", "mcData", "Movements", "HOSTILE"}
called = {k: v for k, v in called.items() if k in defined2 and k not in NOT_FUNCTIONS}
run2["library"] = {"run1_files": len(lib1), "run1_lines": sum(len(v) for v in lib1.values()), "run2_files": len(lib2), "run2_lines": lines2,
                   "run2_lines_identical_to_run1": kept2, "share_identical": kept2 / lines2,
                   "share_identical_lines_of_20_chars_or_more": sum(1 for v in lib2.values() for l in v if len(l) >= 20 and l in set1) / sum(1 for v in lib2.values() for l in v if len(l) >= 20),
                   "files_named_as_in_run1": sum(1 for n in lib2 if n in lib1),
                   "files_new": sorted(n for n in lib2 if n not in lib1), "files_unchanged": sorted(n for n in lib2 if n in lib1 and lib1[n] == lib2[n]),
                   "files_dropped": sorted(n for n in lib1 if n not in lib2), "first_commit": first_hash, "first_commit_files": len(first_lib), "first_commit_lines": start["lib_lines"],
                   "per_file": per_file, "functions_called": len(called), "functions_called_from_run1": sum(1 for k in called if k in defined1),
                   "calls": sum(called.values()), "calls_to_run1_functions": sum(v for k, v in called.items() if k in defined1),
                   "top_new_functions": sorted(((k, v) for k, v in called.items() if k not in defined1), key=lambda kv: -kv[1])[:15],
                   "top_old_functions": sorted(((k, v) for k, v in called.items() if k in defined1), key=lambda kv: -kv[1])[:15]}
run2["commits"] = series

# --- Plan and lessons: how the loop was kept.
plan_edits = [c for c in calls if "00-plan" in str(c["input"]) and (c["name"] in ("Write", "Edit") or re.search(r"open\(|>>?\s*\S*00-plan|cat\s*>|write", str(c["input"].get("command", ""))))]
targets_edits = [c for c in calls if "01-targets" in str(c["input"]) and (c["name"] in ("Write", "Edit") or re.search(r"open\(|>>?\s*\S*01-targets|cat\s*>|write", str(c["input"].get("command", ""))))]
lessons_edits = [c for c in calls if "02-lessons" in str(c["input"]) and (c["name"] in ("Write", "Edit") or re.search(r"open\(|>>\s*\S*02-lessons|cat\s*>>?|write", str(c["input"].get("command", ""))))]
lessons_text = (ws / "memory" / "02-lessons.md").read_text()
run2["memory"] = {"plan_edits": len(plan_edits), "plan_edit_hours": [round(H2(c["t"]), 3) for c in plan_edits], "targets_edits": len(targets_edits), "targets_edit_hours": [round(H2(c["t"]), 3) for c in targets_edits],
                  "lessons_edits": len(lessons_edits), "lessons_lines": len(lessons_text.splitlines()), "lessons_chars": len(lessons_text),
                  "plan_max_chars": max(s["plan_chars"] for s in series), "plan_chars_final": series[-1]["plan_chars"],
                  "commits_changing_plan": len(git("log", "--format=%h", "--", "memory/00-plan.md").split()),
                  "commits_changing_targets": len(git("log", "--format=%h", "--", "memory/01-targets.md").split())}

# --- The time from each death to the next program, and to the next commit.
commit_h = [s["h"] for s in series]
prog_starts = [ts(p["startedAt"]) for p in before2]
for d in run2["deaths"]:
    t = T0.timestamp() + d["h"] * 3600
    nxt = next((x for x in prog_starts if x.timestamp() > t), None)
    d["next_program_s"] = (nxt.timestamp() - t) if nxt else None
    c = next((h for h in commit_h if h > d["h"]), None)
    d["next_commit_min"] = (c - d["h"]) * 60 if c is not None else None

# --- Compactions, and whether both manifests were read again before the next program.
stream = jl(RUN2 / "records" / "agent-stream.jsonl")
comp = []
for d in stream:
    if d.get("type") == "system" and d.get("subtype") == "compact_boundary":
        md = d.get("compact_metadata") or {}
        comp.append({"pre": md.get("pre_tokens"), "post": md.get("post_tokens"), "trigger": md.get("trigger")})
boundaries = []
for i, d in enumerate(tr2):
    if d.get("type") == "system" and d.get("subtype") == "compact_boundary" and d.get("timestamp") and ts(d["timestamp"]) <= WIN:
        boundaries.append(ts(d["timestamp"]))
from datetime import timedelta
compact_rows = []
for i, b in enumerate(boundaries):
    nxt_prog = next((x for x in prog_starts if x > b), None)
    window = [c for c in calls if b <= c["t"] <= b + timedelta(seconds=15)]
    txt = " ".join(str(c["input"]) for c in window)
    compact_rows.append({"h": H2(b), "read_infra": "infrastructure-manifest" in txt, "read_planning": "planning-manifest" in txt,
                         "first_read_s": min(((c["t"] - b).total_seconds() for c in window if "manifest" in str(c["input"])), default=None),
                         "to_next_program_s": (nxt_prog - b).total_seconds() if nxt_prog else None,
                         "pre": comp[i]["pre"] if i < len(comp) else None, "post": comp[i]["post"] if i < len(comp) else None})
run2["compactions"] = compact_rows

# --- The status line its own run.sh prints: state at the end of each program.
STATUS = re.compile(r"\[pos\(([-\d.]+),([-\d.]+),([-\d.]+)\) hp([\d.]+) food(\d+) t\d+ (\w+)\] deaths(\d+) sealed:(YES|NO[^ ]*(?: [^ ]+)*?) food-items:(\d+) free:(\d+)")
rows = []
for p in before2:
    txt = (p.get("output") or "") + "\n" + str(p.get("returned") or "")
    m = None
    for m in STATUS.finditer(txt):
        pass
    if not m:
        continue
    tail = txt[m.end():]
    rows.append({"t": ts(p.get("endedAt") or p["startedAt"]), "dim": m.group(6), "hp": float(m.group(4)), "sealed": m.group(8).startswith("YES"), "deaths": int(m.group(7)),
                 "obsidian": int((re.search(r"\bobsidian:(\d+)", tail) or [0, 0])[1]), "fns": int((re.search(r"flint_and_steel:(\d+)", tail) or [0, 0])[1])})
run2["status_lines"] = {"programs_with_status": len(rows), "sealed_share": sum(r["sealed"] for r in rows) / len(rows),
                        "by_dim": {dim: {"n": sum(1 for r in rows if r["dim"] == dim), "sealed": sum(1 for r in rows if r["dim"] == dim and r["sealed"])} for dim in {r["dim"] for r in rows}}}

# --- Nether entries: the last status line in the Overworld, and the first inside the Nether.
entries = []
prev_dim = None
for tt, f in fr_t:
    if tt > WIN:
        break
    if f["dim"] == "the_nether" and prev_dim == "overworld":
        lo = [r for r in rows if r["t"] <= tt and r["dim"] == "overworld"]
        last = lo[-1] if lo else None
        hi = next((r for r in rows if r["t"] >= tt - timedelta(seconds=15) and r["dim"] == "the_nether"), None)
        before_ok = bool(last and last["obsidian"] >= 10 and last["fns"] >= 1)
        after_ok = bool(hi and hi["obsidian"] >= 10 and hi["fns"] >= 1)
        entries.append({"h": H2(tt), "obsidian": last["obsidian"] if last else None, "fns": last["fns"] if last else None, "status_age_s": (tt - last["t"]).total_seconds() if last else None,
                        "first_inside_obsidian": hi["obsidian"] if hi else None, "first_inside_fns": hi["fns"] if hi else None, "ok_before": before_ok, "ok_either": before_ok or after_ok})
    prev_dim = f["dim"]
run2["nether_entries"] = entries
run2["nether_compliance"] = {"entries": len(entries), "ok_last_overworld_status": sum(e["ok_before"] for e in entries), "ok_either": sum(e["ok_either"] for e in entries)}


# --- Recovery and time by place, by one method for both runs.
def places(run):
    rec = run / "records"
    ev = jl(rec / "events.jsonl")
    fr = [(ts(f["t"]), f) for f in jl(run / "server" / "camera" / "frames.jsonl")]
    win = next(ts(e["t"]) for e in ev if e["type"] == "win")
    t0 = ts(jl(rec / "programs.jsonl")[0]["startedAt"])
    spawn = next(e for e in ev if e["type"] == "bot_connected")["pos"]
    resp = [e for e in ev if e["type"] == "bot_respawn"]
    out = []
    for e in ev:
        if e["type"] != "bot_death" or not t0 < ts(e["t"]) <= win or not e.get("pos"):
            continue
        t, p = ts(e["t"]), e["pos"]
        prior = [f for tt, f in fr if tt <= t]
        dim = prior[-1]["dim"] if prior else None
        r = next((x for x in resp if ts(x["t"]) >= t), None)
        rp = r.get("pos") if r else None
        back = None
        if dim:
            for tt, f in fr:
                if tt > t + timedelta(seconds=5) and tt <= win and f["dim"] == dim and math.dist(f["pos"], [p["x"], p["y"], p["z"]]) <= 16:
                    back = (tt - t).total_seconds()
                    break
        at_spawn = bool(rp and math.hypot(rp["x"] - spawn["x"], rp["z"] - spawn["z"]) <= 30)
        out.append({"h": (t - t0).total_seconds() / 3600, "dim": dim, "back_s": back, "censor_s": (win - t).total_seconds(), "respawn_at_world_spawn": at_spawn})
    wf = [x for x in out if x["dim"]]
    got = [x["back_s"] for x in wf if x["back_s"] is not None]
    hours = Counter()
    prev = None
    for tt, f in fr:
        if t0 <= tt <= win:
            if prev is not None and (tt - prev[0]).total_seconds() < 60:
                hours[prev[1]] += (tt - prev[0]).total_seconds() / 3600
            prev = (tt, f["dim"])
    return {"deaths_with_frame": len(wf), "returned": len(got), "never": len(wf) - len(got), "median_back_s": statistics.median(got), "within_300s": sum(1 for v in got if v <= 300),
            "back_s": sorted(got), "per_death": wf, "hours_by_dim": dict(hours), "deaths_by_dim": Counter(x["dim"] for x in out).most_common(), "respawns_at_world_spawn": sum(x["respawn_at_world_spawn"] for x in out),
            "first_frame_h": (fr[0][0] - t0).total_seconds() / 3600, "spawn_dist_note": "respawn within 30 blocks of the first connect position"}


run2["places"] = places(RUN2)
run1["places"] = places(RUN1)

# --- Death rates, with the interval on their ratio.
h1, h2 = run1["win_h"], run2["win_h"]
n1, n2 = len(run1["deaths"]), len(run2["deaths"])
SLEEP = (9.41, 15.82)  # run 1: Mac asleep, from the first preprint
in_sleep = sum(1 for d in run1["deaths"] if SLEEP[0] <= d["h"] <= SLEEP[1])
ratio = (n2 / h2) / (n1 / h1)
se = math.sqrt(1 / n1 + 1 / n2)
pub = {"overworld": 69, "the_nether": 17, "the_end": 29}  # run 1, the first preprint's Figure 5 (frames, plus void and pre-camera deaths placed by rule)
hrs1 = dict(run1["places"]["hours_by_dim"])
hrs1["overworld"] += run1["places"]["first_frame_h"]  # before its camera started run 1 was in the Overworld
d2 = dict(run2["places"]["deaths_by_dim"])
hrs2 = run2["places"]["hours_by_dim"]
rates1 = {k: pub[k] / hrs1[k] for k in pub}
rates2 = {k: d2[k] / hrs2[k] for k in pub}
expected = sum(rates1[k] * hrs2[k] for k in pub)
pois = sum(math.exp(-expected) * expected ** i / math.factorial(i) for i in range(n2 + 1))
run_h2 = run2["running_h"]
pause2 = run2["pauses"]["total_h"]
run_h1 = run1["running_h"]
pause1 = run1["pauses"]["total_h"]
run2["death_stats"] = {"per_h_run1": n1 / h1, "per_h_run2": n2 / h2, "per_h_run1_excl_sleep": (n1 - in_sleep) / (h1 - (SLEEP[1] - SLEEP[0])), "deaths_in_sleep_band": in_sleep,
                       "rate_ratio": ratio, "ratio_ci95": [ratio * math.exp(-1.96 * se), ratio * math.exp(1.96 * se)],
                       "per_program_run1": n1 / run1["programs"]["before_win"], "per_program_run2": n2 / run2["programs"]["before_win"], "per_real_program_run1": n1 / run1["programs"]["real"],
                       "rates_by_dim_run1": rates1, "rates_by_dim_run2": rates2, "hours_by_dim_run1_with_precamera": hrs1, "expected_at_run1_rates": expected, "poisson_p_le_observed": pois,
                       "in_pause_per_h_run1": run1["deaths_in_pause"]["n"] / pause1, "in_pause_per_h_run2": run2["deaths_in_pause"]["n"] / pause2,
                       "running_per_h_run1": (run1["deaths_after_first_program"] - run1["deaths_in_pause"]["n"]) / run_h1, "running_per_h_run2": (run2["deaths_after_first_program"] - run2["deaths_in_pause"]["n"]) / run_h2}

# --- Recovery as time to an event: a death the player never returned to is unfinished at the win, not absent.
def tte(rows):
    return [(x["back_s"], 1) if x["back_s"] is not None else (x["censor_s"], 0) for x in rows]


def logrank(a, b):
    O = E = V = 0.0
    for t in sorted({x for x, e in a + b if e}):
        na, nb = sum(1 for x, _ in a if x >= t), sum(1 for x, _ in b if x >= t)
        da, db = sum(1 for x, e in a if x == t and e), sum(1 for x, e in b if x == t and e)
        n, d = na + nb, da + db
        O += da
        E += d * na / n
        if n > 1:
            V += d * (na / n) * (nb / n) * (n - d) / (n - 1)
    return O, E, V


def chi_p(O, E, V):
    x = (O - E) ** 2 / V
    return {"chi2": x, "p": math.erfc(math.sqrt(x / 2))}


def km_median(rows):
    s, pts = 1.0, sorted(tte(rows))
    for i, (t, e) in enumerate(pts):
        if e:
            s *= 1 - 1 / (len(pts) - i)
        if s <= 0.5:
            return t
    return None


def fisher(a, b, c, d):
    n, r, k = a + b + c + d, a + b, a + c
    pf = lambda x: math.comb(k, x) * math.comb(n - k, r - x) / math.comb(n, r)
    p0 = pf(a)
    return sum(pf(x) for x in range(max(0, r - (n - k)), min(r, k) + 1) if pf(x) <= p0 * (1 + 1e-9))


A, B = run2["places"]["per_death"], run1["places"]["per_death"]
B_awake = [x for x in B if not SLEEP[0] <= x["h"] <= SLEEP[1]]
rng = random.Random(1)


def boot(rows, n=4000):
    vals = sorted(km_median([rng.choice(rows) for _ in rows]) or 1e9 for _ in range(n))
    return [vals[int(0.025 * n)], vals[int(0.975 * n)]]


by_place, OO, EE, VV = {}, 0.0, 0.0, 0.0
for dim in ("overworld", "the_nether", "the_end"):
    a_, b_ = [x for x in A if x["dim"] == dim], [x for x in B if x["dim"] == dim]
    O_, E_, V_ = logrank(tte(a_), tte(b_))
    OO, EE, VV = OO + O_, EE + E_, VV + V_
    ga, gb = [x["back_s"] for x in a_ if x["back_s"] is not None], [x["back_s"] for x in b_ if x["back_s"] is not None]
    by_place[dim] = {"run2_n": len(a_), "run2_back": len(ga), "run2_median_s": statistics.median(ga), "run1_n": len(b_), "run1_back": len(gb), "run1_median_s": statistics.median(gb), **chi_p(O_, E_, V_)}
run2["recovery"] = {"logrank": chi_p(*logrank(tte(A), tte(B))), "stratified_by_place": chi_p(OO, EE, VV), "by_place": by_place,
                    "km_median_s": {"run2": km_median(A), "run1": km_median(B), "run1_awake": km_median(B_awake)},
                    "km_median_ci95_s": {"run2": boot(A), "run1": boot(B)},
                    "fisher_returned_p": fisher(run2["places"]["returned"], run2["places"]["never"], run1["places"]["returned"], run1["places"]["never"]),
                    "run1_awake": {"n": len(B_awake), "returned": sum(x["back_s"] is not None for x in B_awake), "median_s": statistics.median(x["back_s"] for x in B_awake if x["back_s"] is not None), "logrank": chi_p(*logrank(tte(A), tte(B_awake)))}}


# --- The two worlds, and how far each player moved. One method for both: horizontal distance between camera frames.
def world(run):
    ev, pr = jl(run / "records" / "events.jsonl"), jl(run / "records" / "programs.jsonl")
    t0 = ts(pr[0]["startedAt"])
    win = next(ts(e["t"]) for e in ev if e["type"] == "win")
    fr = [(ts(f["t"]), f) for f in jl(run / "server" / "camera" / "frames.jsonl")]
    fr = [x for x in fr if x[0] <= win]
    spawn = next(e for e in ev if e["type"] == "bot_connected")["pos"]
    ms = {e["key"]: ts(e["t"]) for e in ev if e["type"] == "milestone"}
    at = lambda t: next(f for tt, f in fr if tt >= t)
    hd = lambda a, b: math.hypot(a[0] - b[0], a[2] - b[2])
    t_n, f_n = next((tt, f) for tt, f in fr if f["dim"] == "the_nether")
    over = [f for tt, f in fr if tt < t_n and f["dim"] == "overworld"][-1]
    s = at(ms["stronghold"])
    path, hrs, prev = Counter(), Counter(), None
    for tt, f in fr:
        if tt < t0:
            continue
        if prev and prev[1]["dim"] == f["dim"] and (tt - prev[0]).total_seconds() < 60:
            d = math.dist(prev[1]["pos"], f["pos"])
            if d < 120:  # larger jumps in one frame gap are deaths or teleports, not walking
                path[f["dim"]] += d
            hrs[f["dim"]] += (tt - prev[0]).total_seconds() / 3600
        prev = (tt, f)
    return {"portal_to_fortress": hd(at(ms["fortress"])["pos"], f_n["pos"]), "portal_to_first_rod": hd(at(ms["blaze_rods"])["pos"], f_n["pos"]), "portal_to_first_pearl": hd(at(ms["ender_pearls"])["pos"], f_n["pos"]),
            "first_portal_to_stronghold": hd(s["pos"], over["pos"]), "spawn_to_stronghold": math.hypot(s["pos"][0] - spawn["x"], s["pos"][2] - spawn["z"]), "origin_to_stronghold": math.hypot(s["pos"][0], s["pos"][2]),
            "portal_to_fortress_min": (ms["fortress"] - ms["nether_portal"]).total_seconds() / 60,
            "diamonds_h": next((ts(e["t"]) - t0).total_seconds() / 3600 for e in ev if e["type"] == "advancement" and "Diamonds" in e["text"]),
            "path_blocks": dict(path), "path_total": sum(path.values()), "path_hours": dict(hrs), "blocks_per_h": {k: path[k] / hrs[k] for k in path}, "camera_start_h": (fr[0][0] - t0).total_seconds() / 3600}


w2, w1 = world(RUN2), world(RUN1)
one_trip_h = ((w1["portal_to_fortress"] - w2["portal_to_fortress"]) + (w1["portal_to_first_pearl"] - w2["portal_to_first_pearl"])) / w1["blocks_per_h"]["the_nether"] + (w1["first_portal_to_stronghold"] - w2["first_portal_to_stronghold"]) / w1["blocks_per_h"]["overworld"]
run2["worlds"] = {"run2": w2, "run1": w1, "one_trip_over_the_differences_h": one_trip_h, "gap_h": h1 - h2, "trips_to_fill_the_gap": (h1 - h2) / one_trip_h}


# --- Pauses without the first player's one-line library checks, which fire just before each real program and make its median pause meaningless.
def pause_stats(run, a=None, b=None, skip_sleep=False):
    ev, pr = jl(run / "records" / "events.jsonl"), jl(run / "records" / "programs.jsonl")
    t0 = ts(pr[0]["startedAt"])
    win = next(ts(e["t"]) for e in ev if e["type"] == "win")
    H_ = lambda t: (t - t0).total_seconds() / 3600
    a = 0 if a is None else a
    b = H_(win) if b is None else b
    inside = [p for p in pr if ts(p["startedAt"]) <= win and a <= H_(ts(p["startedAt"])) <= b]
    real_ = [p for p in inside if not ("L.bot===bot" in p["code"] and len(p["code"]) < 120)]
    m = []
    for x, y in sorted((ts(p["startedAt"]), ts(p["endedAt"] or p["startedAt"])) for p in real_):
        if m and x <= m[-1][1]:
            m[-1][1] = max(m[-1][1], y)
        else:
            m.append([x, y])
    g = [(m[i + 1][0] - m[i][1]).total_seconds() for i in range(len(m) - 1) if not (skip_sleep and SLEEP[0] <= H_(m[i][1]) <= SLEEP[1])]
    return {"hours": b - a, "programs": len(inside), "real": len(real_), "running_share": sum((y - x).total_seconds() for x, y in m) / ((b - a) * 3600),
            "median_s": statistics.median(g), "mean_s": statistics.mean(g), "p90_s": sorted(g)[int(0.9 * len(g))], "longest_s": max(g), "total_h": sum(g) / 3600, "over_15_min": sum(x >= 900 for x in g)}


SWITCH = 58.97  # run 1: medium until here, then xhigh (the first preprint)
END2 = run2["milestones"]["the_end"]
run2["pauses_real"] = {"run2": pause_stats(RUN2), "run2_end": pause_stats(RUN2, END2), "run1": pause_stats(RUN1), "run1_awake": pause_stats(RUN1, skip_sleep=True),
                       "run1_medium_awake": pause_stats(RUN1, 0, SWITCH, skip_sleep=True), "run1_xhigh": pause_stats(RUN1, SWITCH)}

# --- Run 1's xhigh tail against this run's End: the same effort, with the same tools in hand.
ev1 = jl(RUN1 / "records" / "events.jsonl")
T1 = ts(run1["t0_utc"])
H1 = lambda t: (t - T1).total_seconds() / 3600
fr1 = [(ts(f["t"]), f) for f in jl(RUN1 / "server" / "camera" / "frames.jsonl")]
tail_h, prev = Counter(), None
for tt, f in fr1:
    if SWITCH <= H1(tt) and tt <= ts(run1["win_utc"]):
        if prev and (tt - prev[0]).total_seconds() < 60:
            tail_h[prev[1]] += (tt - prev[0]).total_seconds() / 3600
        prev = (tt, f["dim"])
tail_deaths = Counter([f for tt, f in fr1 if tt <= ts(e["t"])][-1]["dim"] for e in ev1 if e["type"] == "death" and SWITCH <= H1(ts(e["t"])) and ts(e["t"]) <= ts(run1["win_utc"]))
run2["same_effort"] = {"switch_h": SWITCH, "tail_hours_by_dim": dict(tail_h), "tail_deaths_by_dim": dict(tail_deaths), "tail_end_rate": tail_deaths["the_end"] / tail_h["the_end"],
                       "medium_end_deaths": pub["the_end"] - tail_deaths["the_end"], "medium_end_hours": hrs1["the_end"] - tail_h["the_end"], "medium_end_rate": (pub["the_end"] - tail_deaths["the_end"]) / (hrs1["the_end"] - tail_h["the_end"]), "this_end_rate": rates2["the_end"]}

# --- Which tools the programs called: dated by the first commit that defines each name.
DEF = re.compile(r"\bL\.(\w+)\s*=(?!=)")
born = {}
for h_, when, _ in log:
    txt = "".join(git("show", f"{h_}:{path}") + "\n" for path in git("ls-tree", "-r", "--name-only", h_, "lib").splitlines() if path.endswith(".js"))
    for n in set(DEF.findall(txt)):
        born.setdefault(n, H2(ts(when)))
d1 = set(DEF.findall("\n".join(f.read_text(errors="replace") for f in (RUN1 / "workspace" / "lib").glob("*.js"))))
origin = lambda n: "first_player" if n in d1 else ("before_first_program" if born[n] <= 0.01 else "during_run")
per_hour, total_calls, lines_by_h = defaultdict(Counter), Counter(), defaultdict(list)
INSTALL = lambda c: "Core helpers. Install" in c[:200] or len(c) > 20000
for p in before2:
    if INSTALL(p["code"]):
        continue
    hh = min(8, int(H2(ts(p["startedAt"]))))  # the last 8 minutes after hour 9 join hour 8
    lines_by_h[hh].append(sum(1 for l in p["code"].splitlines() if l.strip()))
    for n in set(re.findall(r"\bL\.(\w+)", p["code"])):
        if n in NOT_FUNCTIONS or n not in born:
            continue
        per_hour[hh][origin(n)] += 1
        total_calls[n] += 1
FIXES = ("dig", "runTo", "peek", "fastBridge", "fightStep", "dive", "wrapRun", "fleeWait", "melee", "obsGen", "safeGravel", "pickup")
all_lib_2 = "\n".join(f.read_text(errors="replace") for f in (RUN2 / "workspace" / "lib").glob("*.js"))
run2["tool_origin"] = {"names": {k: sum(1 for n in born if origin(n) == k) for k in ("first_player", "before_first_program", "during_run")}, "run1_names": len(d1),
                       "per_hour": {str(h_): dict(c) for h_, c in sorted(per_hour.items())}, "totals": {k: sum(c[k] for c in per_hour.values()) for k in ("first_player", "before_first_program", "during_run")},
                       "called_names": {k: sum(1 for n in total_calls if origin(n) == k) for k in ("first_player", "before_first_program", "during_run")},
                       "top_during_run": Counter({n: v for n, v in total_calls.items() if origin(n) == "during_run"}).most_common(10), "median_lines_by_hour": {str(h_): statistics.median(v) for h_, v in sorted(lines_by_h.items())},
                       "programs_calling_fix_tools": {n: sum(1 for p in before2 if not INSTALL(p["code"]) and re.search(r"\bL\." + n + r"\b", p["code"])) for n in FIXES},
                       "fix_tools_born_h": {n: born.get(n) for n in FIXES}, "safeGravel_defined_in_final_library": "safeGravel" in all_lib_2,
                       "safeGravel_in_any_program": any("safeGravel" in p["code"] for p in programs2), "pickup_programs_after_death_11": sum(1 for p in before2 if not INSTALL(p["code"]) and H2(ts(p["startedAt"])) > 6.1 and re.search(r"\bL\.pickup\b", p["code"]))}

# --- Bartering, the usual human route to pearls: did either player try it?
def barter(run):
    pr = jl(run / "records" / "programs.jsonl")
    lib = "".join(f.read_text(errors="replace") for f in (run / "workspace" / "lib").glob("*.js"))
    notes = [l for f in (run / "workspace" / "memory").glob("*") if f.is_file() for l in f.read_text(errors="replace").splitlines() if re.search("barter", l, re.I)]
    return {"programs_naming_barter": sum(bool(re.search("barter", p["code"], re.I)) for p in pr), "programs_naming_piglin_and_gold_ingot": sum(bool(re.search("piglin", p["code"], re.I) and "gold_ingot" in p["code"]) and not INSTALL(p["code"]) for p in pr),
            "library_naming_barter": len(re.findall("barter", lib, re.I)), "note_lines_naming_barter": len(notes)}


run2["barter"] = {"run2": barter(RUN2), "run1": barter(RUN1)}

# --- The prediction we wrote down before the run.
root_git = lambda *a: subprocess.run(["git", "-C", str(PROJECT), *a], capture_output=True, text=True).stdout.strip()
pred_when = ts(root_git("log", "-1", "--format=%cI", "345ec9a"))
run2["prediction"] = {"low_h": 15, "high_h": 25, "commit": "345ec9a", "minutes_before_session": (first_event - pred_when).total_seconds() / 60, "beat_low_end_by_h": 15 - h2, "own_target_h": 9.5, "own_target_off_min": (9.5 - h2) * 60}

# --- The plan's finish forecast and the dragon's health.
forecast, last_f = [], None
for c in calls:
    for m in re.finditer(r"finish target (\d{1,2}):(\d{2})", json.dumps(c["input"])):
        v = int(m.group(1)) + int(m.group(2)) / 60
        if v != last_f:
            forecast.append({"h": max(0.0, H2(c["t"])), "finish_h": v})
            last_f = v
run2["forecast"] = forecast
dragon = []
for p in before2:
    out_ = (p.get("output") or "") + "\n" + str(p.get("returned") or "")
    vals = [float(v) for v in re.findall(r'"phase":-?\d+,"hp":([\d.]+)\}', out_)] + [float(v) for v in re.findall(r"\bD([\d.]+)/ph-?\d", out_)]
    if vals:
        dragon.append({"h": H2(ts(p.get("endedAt") or p["startedAt"])), "hp": vals[-1], "min": min(vals)})
run2["dragon"] = dragon
ctx, seen = [], set()
for d in tr2:
    if d.get("type") == "assistant" and d["message"].get("id") not in seen and d.get("timestamp") and ts(d["timestamp"]) <= WIN:
        seen.add(d["message"].get("id"))
        u = d["message"].get("usage") or {}
        ctx.append([round(H2(ts(d["timestamp"])), 4), (u.get("input_tokens", 0) or 0) + (u.get("cache_read_input_tokens", 0) or 0) + (u.get("cache_creation_input_tokens", 0) or 0)])
run2["ctx"] = [c for c in ctx if c[0] >= 0][::max(1, len(ctx) // 1500)]

# --- Tokens, cost and model time.
results = [d for d in stream if d.get("type") == "result"]
run2["tokens"] = tokens(RUN2, WIN)
run1["tokens"] = tokens(RUN1, ts(run1["win_utc"]))
run2["model_usage_session_end"] = results[0].get("modelUsage") if results else None
run2["turns_session_end"] = results[0].get("num_turns") if results else None
run2["cost_usd_session_end"] = results[0].get("total_cost_usd") if results else None
run2["cost_usd_after_portal"] = results[-1].get("total_cost_usd") if results else None
run2["api_ms_session_end"] = results[0].get("duration_api_ms") if results else None
run2["session_results"] = len(results)
efforts = Counter()
for d in tr2:
    if d.get("type") == "api-request" and d.get("timestamp") and ts(d["timestamp"]) <= WIN:
        efforts[str((d.get("params") or {}).get("output_config", {}).get("effort"))] += 1
run2["effort_requests"] = efforts.most_common()

# --- After the win.
after = [p for p in programs2 if ts(p["startedAt"]) > WIN]
run2["after_win"] = {"programs": len(after), "times": [p["startedAt"] for p in after]}
run2["server_restarts"] = sum(1 for e in events2 if e["type"] == "server_ready") - 1
run2["bot_reconnects"] = sum(1 for e in events2 if e["type"] == "bot_connected") - 1
run2["event_types"] = Counter(e["type"] for e in events2).most_common()

(PRE / "data").mkdir(exist_ok=True)
out = {"run2": run2, "run1": run1, "team": {"win_h": 1634 / 60, "programs": 2783, "distinct_lines": 63313, "deaths": 605,
       "milestones_min": {"stone_tools": 6, "iron_tools": 14, "bucket": 14, "flint_and_steel": 64, "nether_portal": 102, "fortress": 177, "ender_pearls": 186, "blaze_rods": 257,
                          "eyes_of_ender": 643, "stronghold": 797, "the_end": 813, "ten_crystals": 1594, "dragon": 1634}}}
(PRE / "data" / "run2.json").write_text(json.dumps(out, indent=1, default=str))

show = {k: run2[k] for k in ("win_h", "prep_s", "death_causes", "programs", "running_share", "pauses", "deaths_in_pause", "frames", "tool_calls", "memory", "compactions", "status_lines", "nether_compliance", "forecast", "tokens", "model_usage_session_end", "cost_usd_session_end", "cost_usd_after_portal", "api_ms_session_end", "session_results", "effort_requests", "after_win", "server_restarts", "bot_reconnects")}
print(json.dumps(show, default=str))
print("inherited:", json.dumps({k: v for k, v in run2["inherited_use"].items() if k != "during_text"}, default=str))
for x in run2["inherited_use"]["during_text"]:
    print("  ", x["h"], x["text"][:120].replace("\n", " / "))
print("stats:", json.dumps(run2["death_stats"], default=str))
print("places2:", json.dumps({k: v for k, v in run2["places"].items() if k != "back_s"}, default=str))
print("places1:", json.dumps({k: v for k, v in run1["places"].items() if k != "back_s"}, default=str))
lb = {k: v for k, v in run2["library"].items() if k != "per_file"}
print(json.dumps(lb, default=str))
print("run1:", json.dumps({k: run1[k] for k in ("running_share", "pauses", "deaths_in_pause", "tokens", "death_causes", "deaths_after_first_program", "programs")}, default=str))
print("run1 total deaths", len(run1["deaths"]), "run2 total", len(run2["deaths"]))
print("NEW:", json.dumps({k: run2[k] for k in ("recovery", "worlds", "pauses_real", "same_effort", "tool_origin", "barter", "prediction")}, default=str, indent=0).replace("\n", " "))
print("deaths2:", *[(round(d["h"], 2), d["cause"], d["dim"], d["in_program"], d["since_program_end_s"] and round(d["since_program_end_s"], 1)) for d in run2["deaths"]], sep="\n ")
