#!/usr/bin/env python3
"""Pull the numbers the run 4 preprint needs out of all four runs' records.

    python3 preprint-run4/scripts/run_data.py   -> preprint-run4/data/run4.json

Reads only. The same functions measure every run, so a difference between runs is not a difference
in method. Statistics that resample use a fixed seed, so a rerun gives the same numbers.

Times are hours on the OFFICIAL clock, from the player's first spawn (first bot_connected), unless a
name says otherwise. The earlier papers ran from the first program, so their figures differ slightly;
hours from the first program are kept beside the official ones. Everything is cut at the win. Run 3
never won: it is cut where the owner ended it, at the supervisor's exit event.
"""
import json
import math
import random
import re
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PRE = Path(__file__).resolve().parent.parent
PROJECT = PRE.parent
IDS = {"run1": "2026-11-01-1211", "run2": "2026-11-04-1901", "run3": "2026-11-06-0651", "run4": "2026-11-06-2240"}
RUN = {k: PROJECT / "runs" / v for k, v in IDS.items()}
THIS = RUN["run4"]


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def jl(p):
    out = []
    for line in Path(p).read_text(errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def clock(h):
    s = int(round(h * 3600))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def cause(text):
    """The earlier papers' rule list, in its order, so the counts stay as published."""
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
    local = run / "records" / "transcripts" / f"{sid}.jsonl"
    return local if local.exists() else next(Path.home().glob(f".claude/projects/*/{sid}.jsonl"))


def bounds(run):
    ev = jl(run / "records" / "events.jsonl")
    pr = jl(run / "records" / "programs.jsonl")
    spawn = ts(next(e for e in ev if e["type"] == "bot_connected")["t"])
    win = next((ts(e["t"]) for e in ev if e["type"] == "win"), None)
    end = win or ts([e for e in ev if e["type"] == "supervisor" and "exit" in e.get("text", "")][-1]["t"])
    t0 = min(ts(p["startedAt"]) for p in pr)
    return ev, pr, spawn, t0, win, end


INSTALL = lambda c: "Core helpers. Install" in c[:200] or len(c) > 20000
NOT_FUNCTIONS = {"bot", "Vec3", "goals", "gen", "mcData", "Movements", "HOSTILE", "als", "console", "isC", "deaths", "busy"}


def merge(spans):
    merged = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def measure(run):
    ev, pr, spawn, t0, win, end = bounds(run)
    H = lambda t: (t - spawn).total_seconds() / 3600
    before = [p for p in pr if ts(p["startedAt"]) <= end]
    is_check = lambda p: "L.bot===bot" in p["code"] and len(p["code"]) < 120
    real = [p for p in before if not is_check(p)]
    m_all = merge((ts(p["startedAt"]), ts(p["endedAt"]) if p.get("endedAt") else ts(p["startedAt"])) for p in before)
    m_real = merge((ts(p["startedAt"]), ts(p["endedAt"]) if p.get("endedAt") else ts(p["startedAt"])) for p in real)
    running = sum((b - a).total_seconds() for a, b in m_all)
    total = (end - t0).total_seconds()
    pauses = [(m_real[i + 1][0] - m_real[i][1]).total_seconds() for i in range(len(m_real) - 1)]
    deaths = []
    fr = sorted(((ts(f["t"]), f) for f in jl(run / "server" / "camera" / "frames.jsonl")), key=lambda x: x[0])
    bd = [e for e in ev if e["type"] == "bot_death"]
    for e in ev:
        if e["type"] != "death" or ts(e["t"]) > end:
            continue
        t = ts(e["t"])
        running_now = any(a <= t <= b for a, b in m_all)
        ended = [b for a, b in m_all if b <= t]
        since = (t - ended[-1]).total_seconds() if ended and not running_now else None
        last = [f for tt, f in fr if tt <= t]
        near = min(bd, key=lambda x: abs((ts(x["t"]) - t).total_seconds())) if bd else None
        deaths.append({"h": H(t), "clock": clock(H(t)), "text": e["text"], "cause": cause(e["text"]), "in_program": running_now, "since_program_end_s": since,
                       "dim": last[-1]["dim"] if last else None, "pos": near.get("pos") if near and abs((ts(near["t"]) - t).total_seconds()) < 30 else None, "before_first_program": t < t0})
    gaps = [(deaths[i + 1]["h"] - deaths[i]["h"]) * 60 for i in range(len(deaths) - 1)]
    durs = [p["durationMs"] / 1000 for p in real if p.get("durationMs") is not None]
    miles = {e["key"]: H(ts(e["t"])) for e in ev if e["type"] == "milestone" and ts(e["t"]) <= end}
    return {"spawn_utc": spawn.isoformat(), "t0_utc": t0.isoformat(), "end_utc": end.isoformat(), "won": win is not None, "official_h": H(end), "from_first_program_h": (end - t0).total_seconds() / 3600,
            "spawn_to_first_program_s": (t0 - spawn).total_seconds(), "milestones": miles,
            "advancements": [{"h": H(ts(e["t"])), "name": e["text"]} for e in ev if e["type"] == "advancement" and ts(e["t"]) <= end],
            "deaths": deaths, "death_gaps_min": gaps, "chain_5min": sum(1 for g in gaps if g <= 5), "chain_10min": sum(1 for g in gaps if g <= 10), "min_gap_min": min(gaps), "death_causes": Counter(d["cause"] for d in deaths).most_common(),
            "deaths_between_programs": sum(1 for d in deaths if not d["in_program"] and not d["before_first_program"]),
            "deaths_within_20s_of_program_end": sum(1 for d in deaths if d["since_program_end_s"] is not None and d["since_program_end_s"] <= 20),
            "programs": {"before_end": len(before), "library_checks": len(before) - len(real), "real": len(real), "errors": sum(1 for p in before if p.get("error")), "timed_out": sum(1 for p in before if p.get("timedOut")),
                         "median_s_real": statistics.median(durs), "distinct_lines": len({l.strip() for p in before for l in p["code"].splitlines() if l.strip()}), "after_end": len(pr) - len(before),
                         "per_half_hour": sorted(Counter(int(H(ts(p["startedAt"])) * 2) for p in real).items())},
            "running_share": running / total, "running_h": running / 3600,
            "pauses": {"n": len(pauses), "median_s": statistics.median(pauses), "mean_s": statistics.mean(pauses), "p90_s": sorted(pauses)[int(len(pauses) * .9)], "longest_s": max(pauses), "total_h": sum(pauses) / 3600, "over_15_min": sum(x >= 900 for x in pauses)},
            "server_restarts": sum(1 for e in ev if e["type"] == "server_ready") - 1, "bot_connects": sum(1 for e in ev if e["type"] == "bot_connected")}


def tokens(run, end):
    per = {}
    for d in jl(transcript(run)):
        if d.get("type") != "assistant" or (d.get("timestamp") and ts(d["timestamp"]) > end):
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


def places(run):
    """Recovery and time by place, by one method: the first camera frame more than 5 s after a death, in its dimension and within 16 blocks."""
    ev, pr, spawn_t, t0, win, end = bounds(run)
    fr = sorted(((ts(f["t"]), f) for f in jl(run / "server" / "camera" / "frames.jsonl")), key=lambda x: x[0])
    spawn = next(e for e in ev if e["type"] == "bot_connected")["pos"]
    resp = [e for e in ev if e["type"] == "bot_respawn"]
    out = []
    for e in ev:
        if e["type"] != "bot_death" or not t0 < ts(e["t"]) <= end or not e.get("pos"):
            continue
        t, p = ts(e["t"]), e["pos"]
        prior = [f for tt, f in fr if tt <= t]
        dim = prior[-1]["dim"] if prior else None
        r = next((x for x in resp if ts(x["t"]) >= t), None)
        rp = r.get("pos") if r else None
        back = None
        if dim:
            for tt, f in fr:
                if t + timedelta(seconds=5) < tt <= end and f["dim"] == dim and math.dist(f["pos"], [p["x"], p["y"], p["z"]]) <= 16:
                    back = (tt - t).total_seconds()
                    break
        out.append({"h": (t - spawn_t).total_seconds() / 3600, "dim": dim, "back_s": back, "censor_s": (end - t).total_seconds(), "respawn_at_world_spawn": bool(rp and math.hypot(rp["x"] - spawn["x"], rp["z"] - spawn["z"]) <= 30)})
    wf = [x for x in out if x["dim"]]
    got = [x["back_s"] for x in wf if x["back_s"] is not None]
    hours, prev = Counter(), None
    for tt, f in fr:
        if spawn_t <= tt <= end:
            if prev is not None and (tt - prev[0]).total_seconds() < 60:
                hours[prev[1]] += (tt - prev[0]).total_seconds() / 3600
            prev = (tt, f["dim"])
    return {"deaths_with_frame": len(wf), "returned": len(got), "never": len(wf) - len(got), "median_back_s": statistics.median(got) if got else None, "within_300s": sum(1 for v in got if v <= 300), "back_s": sorted(got), "per_death": wf,
            "hours_by_dim": dict(hours), "deaths_by_dim": Counter(x["dim"] for x in out).most_common(), "respawns_at_world_spawn": sum(x["respawn_at_world_spawn"] for x in out), "first_frame_h": (fr[0][0] - spawn_t).total_seconds() / 3600}


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


rng = random.Random(1)


def boot(rows, n=4000):
    vals = sorted(km_median([rng.choice(rows) for _ in rows]) or 1e9 for _ in range(n))
    return [vals[int(0.025 * n)], vals[int(0.975 * n)]]


def world(run):
    ev, pr, spawn_t, t0, win, end = bounds(run)
    fr = sorted(((ts(f["t"]), f) for f in jl(run / "server" / "camera" / "frames.jsonl")), key=lambda x: x[0])
    fr = [x for x in fr if x[0] <= end]
    spawn = next(e for e in ev if e["type"] == "bot_connected")["pos"]
    ms = {e["key"]: ts(e["t"]) for e in ev if e["type"] == "milestone" and ts(e["t"]) <= end}
    at = lambda t: next((f for tt, f in fr if tt >= t), fr[-1][1])
    hd = lambda a, b: math.hypot(a[0] - b[0], a[2] - b[2])
    t_n, f_n = next((tt, f) for tt, f in fr if f["dim"] == "the_nether")
    over = [f for tt, f in fr if tt < t_n and f["dim"] == "overworld"]
    over = over[-1] if over else None
    path, hrs, prev = Counter(), Counter(), None
    for tt, f in fr:
        if tt < spawn_t:
            continue
        if prev and prev[1]["dim"] == f["dim"] and (tt - prev[0]).total_seconds() < 60:
            d = math.dist(prev[1]["pos"], f["pos"])
            if d < 120:  # larger jumps in one frame gap are deaths or teleports, not walking
                path[f["dim"]] += d
            hrs[f["dim"]] += (tt - prev[0]).total_seconds() / 3600
        prev = (tt, f)
    w = {"portal_to_fortress": hd(at(ms["fortress"])["pos"], f_n["pos"]) if "fortress" in ms else None, "portal_to_first_rod": hd(at(ms["blaze_rods"])["pos"], f_n["pos"]) if "blaze_rods" in ms else None,
         "portal_to_first_pearl": hd(at(ms["ender_pearls"])["pos"], f_n["pos"]) if "ender_pearls" in ms else None, "portal_to_fortress_min": (ms["fortress"] - ms["nether_portal"]).total_seconds() / 60 if "fortress" in ms else None,
         "diamonds_h": next(((ts(e["t"]) - spawn_t).total_seconds() / 3600 for e in ev if e["type"] == "advancement" and "Diamonds" in e["text"]), None),
         "path_blocks": dict(path), "path_total": sum(path.values()), "path_hours": dict(hrs), "blocks_per_h": {k: path[k] / hrs[k] for k in path}, "camera_start_h": (fr[0][0] - spawn_t).total_seconds() / 3600, "spawn_xz": [spawn["x"], spawn["z"]]}
    if "stronghold" in ms:
        s = [f for tt, f in fr if tt <= ms["stronghold"] and f["dim"] == "overworld"][-1]  # the event can fire as the player enters the End
        w.update({"first_portal_to_stronghold": hd(s["pos"], over["pos"]) if over else None, "spawn_to_stronghold": math.hypot(s["pos"][0] - spawn["x"], s["pos"][2] - spawn["z"]), "origin_to_stronghold": math.hypot(s["pos"][0], s["pos"][2])})
    return w


def lib_lines(folder):
    out = {}
    for f in sorted(Path(folder).glob("*")):
        if f.is_file() and f.suffix in (".js", ".sh") and not f.name.startswith("."):
            out[f.name] = [l.strip() for l in f.read_text(errors="replace").splitlines() if l.strip() and not l.strip().startswith("//")]
    return out


M = {k: measure(v) for k, v in RUN.items()}
D = M["run4"]
SPAWN, T0, WIN = ts(D["spawn_utc"]), ts(D["t0_utc"]), ts(D["end_utc"])
H4 = lambda t: (t - SPAWN).total_seconds() / 3600
programs = jl(THIS / "records" / "programs.jsonl")
before = sorted((p for p in programs if ts(p["startedAt"]) <= WIN), key=lambda p: p["startedAt"])
events = jl(THIS / "records" / "events.jsonl")
frames = jl(THIS / "server" / "camera" / "frames.jsonl")
fr_t = [(ts(f["t"]), f) for f in frames]
for k, r in RUN.items():
    M[k]["places"] = places(r)
    M[k]["world"] = world(r)
    M[k]["tokens"] = tokens(r, ts(M[k]["end_utc"]))

# --- Death rates, on the official clock, with intervals on the ratios to run 2 and run 3.
rates = {}
for k in M:
    n, h = len(M[k]["deaths"]), M[k]["official_h"]
    rates[k] = {"n": n, "h": h, "per_h": n / h}
for k in ("run1", "run2", "run3"):
    r = rates["run4"]["per_h"] / rates[k]["per_h"]
    se = math.sqrt(1 / rates["run4"]["n"] + 1 / rates[k]["n"])
    rates[f"ratio_to_{k}"] = {"ratio": r, "ci95": [r * math.exp(-1.96 * se), r * math.exp(1.96 * se)]}
RUN3_RESETS = 6  # deliberate resets at base, from the run 3 plan's reading of its log
rates["run3_without_resets"] = {"n": rates["run3"]["n"] - RUN3_RESETS, "per_h": (rates["run3"]["n"] - RUN3_RESETS) / rates["run3"]["h"]}
by_place = {}
for k in M:
    p = M[k]["places"]
    d = dict(p["deaths_by_dim"])
    by_place[k] = {dim: {"deaths": d.get(dim, 0), "hours": p["hours_by_dim"].get(dim, 0), "per_h": d.get(dim, 0) / p["hours_by_dim"][dim] if p["hours_by_dim"].get(dim) else None} for dim in ("overworld", "the_nether", "the_end")}
A = M["run4"]["places"]["per_death"]
recovery = {"km_median_s": {k: km_median(M[k]["places"]["per_death"]) for k in M}, "km_median_ci95_s": {k: boot(M[k]["places"]["per_death"]) for k in M}}
for k in ("run1", "run2", "run3"):
    recovery[f"logrank_vs_{k}"] = chi_p(*logrank(tte(A), tte(M[k]["places"]["per_death"])))
recovery["end_only"] = {k: {"n": sum(1 for x in M[k]["places"]["per_death"] if x["dim"] == "the_end"), "returned": sum(1 for x in M[k]["places"]["per_death"] if x["dim"] == "the_end" and x["back_s"] is not None),
                            "median_s": (lambda v: statistics.median(v) if v else None)([x["back_s"] for x in M[k]["places"]["per_death"] if x["dim"] == "the_end" and x["back_s"] is not None])} for k in M}
recovery["nether_only"] = {k: {"n": sum(1 for x in M[k]["places"]["per_death"] if x["dim"] == "the_nether"), "returned": sum(1 for x in M[k]["places"]["per_death"] if x["dim"] == "the_nether" and x["back_s"] is not None),
                               "median_s": (lambda v: statistics.median(v) if v else None)([x["back_s"] for x in M[k]["places"]["per_death"] if x["dim"] == "the_nether" and x["back_s"] is not None])} for k in M}

# --- Where the clock went: stretches labelled from the player's text and its programs, about 3 minutes either way.
# Boundaries come from dimension changes in the camera, deaths, and the program that starts or finishes the next task.
c = lambda s: sum(int(x) * 60 ** (2 - i) for i, x in enumerate(s.split(":"))) / 3600
STRETCHES = [
    ("0:00:00", "0:54:30", "gather", "Kit, base, 59 obsidian, spare chest", None),
    ("0:54:30", "1:02:30", "pearls", "Forest beside the portal, mouth, first pearls", None),
    ("1:02:30", "1:10:00", "recover", "Kit back through a tunnel", 1),
    ("1:10:00", "1:26:00", "pearls", "Farm at about 1.6 a minute", None),
    ("1:26:00", "1:42:10", "recover", "Meals, flint, kit, chest refilled", 2),
    ("1:42:10", "1:47:20", "fortress", "Probe east", None),
    ("1:47:20", "2:04:20", "recover", "Kit burned: rebuilt from ores near base", 3),
    ("2:04:20", "2:14:39", "fortress", "Probe west to the bricks, sealed cell", None),
    ("2:14:39", "2:17:50", "rods", "Closed room, shaft from below", None),
    ("2:17:50", "2:49:50", "recover", "Obsidian, iron, diamonds, meals; gate passed", 4),
    ("2:49:50", "2:56:10", "rods", "Back to the room", None),
    ("2:56:10", "3:25:41", "recover", "Pick, obsidian, kit from under the floor, chest", 5),
    ("3:25:41", "3:36:00", "rods", "The mole method", None),
    ("3:36:00", "3:39:11", "bank", "Home, rods banked", None),
    ("3:39:11", "3:42:11", "pearls", "Last pearls", None),
    ("3:42:11", "3:43:00", "bank", "Eyes crafted", None),
    ("3:43:00", "4:21:11", "eyes", "Throws, overland trek, base, portal", None),
    ("4:21:11", "4:21:28", "crystals", "Arrival platform", None),
    ("4:21:28", "4:45:41", "recover", "Kit lost in the void: rebuilt at the forward base", 6),
    ("4:45:41", "4:48:38", "crystals", "Firing spot, tunnel", None),
    ("4:48:38", "5:49:00", "recover", "Deaths 7 and 8: world spawn, overland to the base, rebuild, kit", 7),
    ("5:49:00", "5:54:31", "crystals", "Peek shots from a pillar: 2 crystals", None),
    ("5:54:31", "6:04:17", "recover", "Spares, arrows, kit", 9),
    ("6:04:17", "6:13:02", "crystals", "Mortar pit: 5 crystals; eggs", None),
    ("6:13:02", "6:22:07", "recover", "Kit, sorted", 10),
    ("6:22:07", "6:35:30", "crystals", "Sealed columns, last egg: 3 crystals", None),
    ("6:35:30", "6:50:52", "dragon", "Fight line, then the dragon", None),
]
stretch_rows = [{"a": c(a), "b": c(b), "kind": k, "what": w, "death": dth, "min": (c(b) - c(a)) * 60} for a, b, k, w, dth in STRETCHES]
assert abs(stretch_rows[-1]["b"] - D["official_h"]) < 0.001 and all(abs(stretch_rows[i]["b"] - stretch_rows[i + 1]["a"]) < 1e-9 for i in range(len(stretch_rows) - 1))
by_kind = Counter()
for s in stretch_rows:
    by_kind[s["kind"]] += s["min"]
# Each death's recovery is assigned to the stage the player was on when it died.
ASSIGN = {1: "pearls", 2: "pearls", 3: "fortress", 4: "rods", 5: "rods", 6: "crystals", 7: "crystals", 9: "crystals", 10: "crystals"}
stage_work, stage_rec = Counter(), Counter()
for s in stretch_rows:
    if s["kind"] == "recover":
        stage_rec[ASSIGN[s["death"]]] += s["min"]
    else:
        stage_work[s["kind"]] += s["min"]
BUDGET = {"entry": 67, "fortress": 20, "rods": 28, "home": 12, "pearls": 42, "eyes": 42, "crystals": 18, "dragon": 45, "compactions": 6, "slack": 20}
stage_table = []
for key, label, b, kind in (("entry", "Read, then to Nether entry", 67, "gather"), ("pearls", "14 pearls", 42, "pearls"), ("fortress", "Fortress found", 20, "fortress"), ("rods", "7 rods", 28, "rods"),
                            ("home", "Home, bank", 12, "bank"), ("eyes", "Eyes, stronghold, End entry", 42, "eyes"), ("crystals", "Ten crystals", 18, "crystals"), ("dragon", "Dragon", 45, "dragon")):
    stage_table.append({"key": key, "label": label, "budget": b, "work": stage_work[kind], "recover": stage_rec[kind], "actual": stage_work[kind] + stage_rec[kind], "over": stage_work[kind] + stage_rec[kind] - b})
activity = {"stretches": stretch_rows, "minutes": dict(by_kind), "share_recover": by_kind["recover"] / sum(by_kind.values()), "work_min": sum(v for k, v in by_kind.items() if k != "recover"), "stages": stage_table,
            "budget_sum": sum(BUDGET.values()), "recover_per_death_min": by_kind["recover"] / 10, "target_h": 5.0, "missed_by_min": D["official_h"] * 60 - 300, "room_for_recovery_at_5h": 300 - sum(v for k, v in by_kind.items() if k != "recover")}

# --- The status line: state at the end of each program. One regex for runs 2, 3 and 4.
STATUS = re.compile(r"\[pos\(([-\d.]+),([-\d.]+),([-\d.]+)\) hp([\d.]+) food(\d+) t\d+ (\w+)\] deaths(\d+) sealed:(YES|NO[^ ]*(?: [^ ]+)*?) food-items:(\d+) free:(\d+)")


def status_rows(run):
    ev, pr, spawn, t0, win, end = bounds(run)
    rows = []
    for p in sorted(pr, key=lambda x: x["startedAt"]):
        if ts(p["startedAt"]) > end:
            continue
        txt = (p.get("output") or "") + "\n" + str(p.get("returned") or "")
        m = None
        for m in STATUS.finditer(txt):
            pass
        if not m:
            continue
        tail = txt[m.end():]
        rows.append({"t": ts(p.get("endedAt") or p["startedAt"]), "dim": m.group(6), "hp": float(m.group(4)), "sealed": m.group(8).startswith("YES"), "deaths": int(m.group(7)),
                     "obsidian": int((re.search(r"\bobsidian:(\d+)", tail) or [0, 0])[1]), "fns": int((re.search(r"flint_and_steel:(\d+)", tail) or [0, 0])[1]), "rods": int((re.search(r"\bblaze_rod:(\d+)", tail) or [0, 0])[1]), "pearls": int((re.search(r"\bender_pearl:(\d+)", tail) or [0, 0])[1])})
    return rows


sealed = {}
for k in ("run2", "run3", "run4"):
    rows_ = status_rows(RUN[k])
    if rows_:
        sealed[k] = {"programs_with_status": len(rows_), "sealed_share": sum(r["sealed"] for r in rows_) / len(rows_), "by_dim": {dim: {"n": sum(1 for r in rows_ if r["dim"] == dim), "sealed": sum(1 for r in rows_ if r["dim"] == dim and r["sealed"])} for dim in sorted({r["dim"] for r in rows_})}}
rows = status_rows(THIS)

# --- Nether entries: the camera's Overworld to Nether changes, with the last status before and the first inside.
entries, prev_dim = [], None
for tt, f in fr_t:
    if tt > WIN:
        break
    if f["dim"] == "the_nether" and prev_dim == "overworld":
        lo = [r for r in rows if r["t"] <= tt and r["dim"] == "overworld"]
        last = lo[-1] if lo else None
        hi = next((r for r in rows if r["t"] >= tt - timedelta(seconds=15) and r["dim"] == "the_nether"), None)
        ok_b = bool(last and last["obsidian"] >= 10 and last["fns"] >= 1)
        ok_a = bool(hi and hi["obsidian"] >= 10 and hi["fns"] >= 1)
        entries.append({"h": H4(tt), "clock": clock(H4(tt)), "obsidian": last["obsidian"] if last else None, "fns": last["fns"] if last else None, "status_age_s": (tt - last["t"]).total_seconds() if last else None, "inside_obsidian": hi["obsidian"] if hi else None, "inside_fns": hi["fns"] if hi else None, "ok_before": ok_b, "ok_either": ok_b or ok_a})
    prev_dim = f["dim"]
dim_changes, prev_dim = [], None
for tt, f in fr_t:
    if tt <= WIN + timedelta(seconds=60) and f["dim"] != prev_dim:
        dim_changes.append({"h": H4(tt), "dim": f["dim"]})
        prev_dim = f["dim"]

# --- The rules, from the programs' text. Library installs are left out of counts of what programs passed.
txt_of = lambda p: (p.get("output") or "") + "\n" + str(p.get("returned") or "")
calls_only = [p for p in before if not INSTALL(p["code"])]
floor_hits = [{"h": H4(ts(p["startedAt"])), "hp": float(m.group(1))} for p in before for m in re.finditer(r"HP FLOOR hit at ([\d.]+)", txt_of(p))]
auto_seal = []
for p in before:
    for m in re.finditer(r"AUTO-SEAL (\{[^\n]*\})", txt_of(p)):
        auto_seal.append({"h": H4(ts(p["startedAt"])), "ok": '"ok":true' in m.group(1), "dim": (rows[-1]["dim"] if False else None)})
auto_dive = [{"h": H4(ts(p["startedAt"]))} for p in before if "AUTO-DIVE" in txt_of(p)]
gate_refusals = [{"h": H4(ts(p["startedAt"])), "text": m.group(0)[:120]} for p in before for m in re.finditer(r"NETHER GATE: [^\n|]*|\bGATE [^\n|]*|\bgate \[\"[^\]]+\]", txt_of(p))]
rules = {"force_passed_in_programs": sum(bool(re.search(r"\bforce\s*:", p["code"])) for p in calls_only), "programs_calling_gate": sum("L.gate(" in p["code"] or "netherGate(" in p["code"] for p in calls_only),
         "programs_calling_usePortal": sum("usePortal" in p["code"] for p in calls_only), "gate_refusals": gate_refusals, "floor_hits": len(floor_hits), "floor_hits_detail": floor_hits, "floor_off_programs": sum(bool(re.search(r"floorOff\s*=\s*true", p["code"])) for p in calls_only),
         "hpfloor_changes": sum(bool(re.search(r"hpFloor\s*=", p["code"])) for p in calls_only), "auto_seal": len(auto_seal), "auto_seal_ok": sum(a["ok"] for a in auto_seal), "auto_dive": len(auto_dive), "auto_dive_hours": [a["h"] for a in auto_dive],
         "auto_seal_off_programs": sum(bool(re.search(r"autoSealOff\s*=\s*true", p["code"])) for p in calls_only), "no_dive_programs": sum(bool(re.search(r"noDive\s*=\s*true", p["code"])) for p in calls_only),
         "client_world_writes": sum("setBlockStateId" in p["code"] or "world.setBlock" in p["code"] for p in calls_only), "velocity_writes": sum(bool(re.search(r"velocity\s*(\.\w+)?\s*=[^=]", p["code"])) or "velocity.set" in p["code"] for p in calls_only),
         "position_writes": sum(bool(re.search(r"entity\.position\s*(\.\w+)?\s*=[^=]", p["code"])) or "position.set(" in p["code"] for p in calls_only), "raw_client": sum("_client" in p["code"] for p in before), "physics_touches": sum("physicsEnabled" in p["code"] or "bot.physics" in p["code"] for p in calls_only),
         "process_or_net_modules": sum(bool(re.search(r"require\(['\"](child_process|fs|net|http|https|dgram|tls)['\"]\)", p["code"])) for p in before), "chat_slash": sum(bool(re.search(r"\.chat\(\s*['\"`]/", p["code"])) for p in before), "hashed_seed": sum(bool(re.search(r"hashedSeed|\.seed\b|levelSeed", p["code"])) for p in before)}

# --- Items by time: rods and pearls, held at each program's end.
items = {"rods": [{"h": H4(r["t"]), "n": r["rods"]} for r in rows], "pearls": [{"h": H4(r["t"]), "n": r["pearls"]} for r in rows]}

# --- Tool calls, and what they read.
tr = jl(transcript(THIS))
calls, first_event = [], None
for d in tr:
    if d.get("timestamp") and first_event is None:
        first_event = ts(d["timestamp"])
    if d.get("type") == "assistant" and isinstance(d["message"].get("content"), list):
        for b in d["message"]["content"]:
            if b.get("type") == "tool_use" and ts(d["timestamp"]) <= WIN:
                calls.append({"t": ts(d["timestamp"]), "name": b["name"], "input": b["input"]})
tool_calls = Counter(x["name"] for x in calls).most_common()
bash_calls = [x for x in calls if x["name"] == "Bash"]
clock_checks = sum(bool(re.search(r"\bdate\b", x["input"].get("command", ""))) for x in bash_calls)


def inh_runs(s):
    return {k for k, v in IDS.items() if k != "run4" and v in s}


def reads_inherited(c_):
    if c_["name"] in ("Read", "Grep", "Glob"):
        return [str(c_["input"].get("file_path") or c_["input"].get("path") or "")] if "inherited" in str(c_["input"]) else []
    return [l for l in str(c_["input"].get("command") or "").splitlines() if re.search(r"inherited|\$INH\b|\$R[123]\b|\bINH\d?=", l) and "Find it:" not in l]


inh = []
for x in calls:
    ls = reads_inherited(x)
    if ls:
        s_ = "\n".join(ls)
        inh.append({"h": H4(x["t"]), "tool": x["name"], "runs": sorted(inh_runs(s_)), "before_first_program": x["t"] < T0, "text": re.sub(r"/private/tmp/claude-\d+/\S*", "<agent temp file>", s_.replace(str(THIS) + "/", "").replace(str(Path.home()), "~"))[:260]})
inherited_use = {"calls": len(inh), "before_first_program": sum(i["before_first_program"] for i in inh), "by_run": Counter(r for i in inh for r in i["runs"] if r != "run4").most_common(), "no_run_named": sum(not i["runs"] for i in inh),
                 "first_30_min": sum(i["h"] < 0.5 for i in inh), "hours": [round(i["h"], 3) for i in inh], "text": [{"h": round(i["h"], 2), "runs": i["runs"], "text": i["text"][:170]} for i in inh],
                 "read_camera_frames": any("camera-frames" in i["text"] or "camera/frames" in i["text"] for i in inh),
                 "read_project_readme": any(re.search(r"minecraft-dragon/README|\.\./README|run-4-plan", str(x["input"].get("file_path") or x["input"].get("command") or "")) for x in calls)}

# --- Library lineage: each line and name goes to the earliest run that has it.
libs = {k: lib_lines(RUN[k] / "workspace" / "lib") for k in RUN}
sets = {k: {l for ls in libs[k].values() for l in ls} for k in libs}


def origin_of_line(l):
    return "run1" if l in sets["run1"] else "run2" if l in sets["run2"] else "run3" if l in sets["run3"] else "own"


tally = Counter(origin_of_line(l) for ls in libs["run4"].values() for l in ls)
lines4 = sum(tally.values())
per_file = sorted(({"file": n, "lines": len(ls), "by_origin": dict(Counter(origin_of_line(l) for l in ls)), "in_run3": n in libs["run3"], "in_run2": n in libs["run2"], "in_run1": n in libs["run1"], "unchanged_from_run3": n in libs["run3"] and libs["run3"][n] == ls, "unchanged_from_run2": n in libs["run2"] and libs["run2"][n] == ls} for n, ls in libs["run4"].items()), key=lambda x: -x["lines"])
ws = THIS / "workspace"
git = lambda *a: subprocess.run(["git", "-C", str(ws), *a], capture_output=True, text=True, errors="replace").stdout
log = [l.split("|", 2) for l in git("log", "--reverse", "--format=%h|%cI|%s").splitlines()]
series = []
for h, when, subj in log:
    cnt, fs = Counter(), 0
    for path in git("ls-tree", "-r", "--name-only", h, "lib").splitlines():
        if path.endswith((".js", ".sh")) and not Path(path).name.startswith("."):
            fs += 1
            for l in git("show", f"{h}:{path}").splitlines():
                l = l.strip()
                if l and not l.startswith("//"):
                    cnt[origin_of_line(l)] += 1
    plan, lessons, targets = git("show", f"{h}:memory/00-plan.md"), git("show", f"{h}:memory/02-lessons.md"), git("show", f"{h}:memory/01-targets.md")
    series.append({"hash": h, "h": H4(ts(when)), "clock": clock(H4(ts(when))), "subject": subj, "lib": dict(cnt), "lib_lines": sum(cnt.values()), "lib_files": fs, "plan_chars": len(plan), "lessons_lines": len(lessons.splitlines()), "targets_chars": len(targets),
                   "plan_line1": plan.splitlines()[0][:220] if plan else "", "cut": next((l[:220] for l in plan.splitlines() if l.startswith("Cut")), None)})
DEF = re.compile(r"\bL\.(\w+)\s*=(?!=)")
defs = {k: set(DEF.findall("\n".join(f.read_text(errors="replace") for f in (RUN[k] / "workspace" / "lib").glob("*.js") if not f.name.startswith(".")))) for k in RUN}


FUNCS = set(re.findall(r"\bL\.(\w+)\s*=\s*(?:async\b|\(|function\b|\w+\s*=>|\{)", "\n".join(f.read_text(errors="replace") for f in (THIS / "workspace" / "lib").glob("*.js") if not f.name.startswith("."))))


def origin_of_name(n):
    return "run1" if n in defs["run1"] else "run2" if n in defs["run2"] else "run3" if n in defs["run3"] else "own"


per_hour, total_calls = defaultdict(Counter), Counter()
for p in calls_only:
    hh = min(6, int(H4(ts(p["startedAt"]))))
    for n in set(re.findall(r"\bL\.(\w+)", p["code"])):
        if n in NOT_FUNCTIONS or n not in defs["run4"] or n not in FUNCS:
            continue
        per_hour[hh][origin_of_name(n)] += 1
        total_calls[n] += 1
lineage = {"lines": dict(tally), "total_lines": lines4, "files": len(libs["run4"]), "share": {k: v / lines4 for k, v in tally.items()}, "lib_sizes": {k: {"files": len(libs[k]), "lines": sum(len(v) for v in libs[k].values())} for k in libs},
           "files_named_as_run3": sum(1 for n in libs["run4"] if n in libs["run3"]), "files_unchanged_from_run3": sum(x["unchanged_from_run3"] for x in per_file), "files_not_in_run3": sorted(n for n in libs["run4"] if n not in libs["run3"]), "per_file": per_file,
           "names": {k: sum(1 for n in defs["run4"] if origin_of_name(n) == k) for k in ("run1", "run2", "run3", "own")}, "uses": {k: sum(v for n, v in total_calls.items() if origin_of_name(n) == k) for k in ("run1", "run2", "run3", "own")},
           "per_hour": {str(h_): dict(x) for h_, x in sorted(per_hour.items())}, "top_own": Counter({n: v for n, v in total_calls.items() if origin_of_name(n) == "own"}).most_common(14), "top_run3": Counter({n: v for n, v in total_calls.items() if origin_of_name(n) == "run3"}).most_common(8),
           "top_run2": Counter({n: v for n, v in total_calls.items() if origin_of_name(n) == "run2"}).most_common(8), "top_run1": Counter({n: v for n, v in total_calls.items() if origin_of_name(n) == "run1"}).most_common(8),
           "named_tools": {n: {"programs": total_calls.get(n, 0), "origin": origin_of_name(n)} for n in ("wrapRun", "autoSeal", "seal6", "gate", "pearlFarm", "dive", "climbRing", "towerHit", "fightStep", "mortarCycle", "tun", "digTo", "probeTo", "dash", "usePortal", "grabKit", "reDig", "peek3", "dSample", "dInfo")}}
prog_files = {k: sum(1 for _ in (RUN[k] / "workspace" / "prog").glob("*")) if (RUN[k] / "workspace" / "prog").exists() else 0 for k in RUN}

# --- Memory: how the loop was kept.
is_write = lambda x, name: name in str(x["input"]) and (x["name"] in ("Write", "Edit") or re.search(r"open\(|>>?\s*\S*" + name + r"|cat\s*>|tee ", str(x["input"].get("command", ""))))
memory = {"plan_edits": sum(bool(is_write(x, "00-plan")) for x in calls), "targets_edits": sum(bool(is_write(x, "01-targets")) for x in calls), "lessons_edits": sum(bool(is_write(x, "02-lessons")) for x in calls), "tools_edits": sum(bool(is_write(x, "tools.md")) for x in calls),
          "lessons_lines": len((ws / "memory" / "02-lessons.md").read_text().splitlines()), "commits": len(log), "commits_before_win": sum(ts(w) <= WIN for _, w, _ in log), "prog_files": prog_files}

# --- Compactions, and whether all three manifests were read within 20 seconds.
stream = jl(THIS / "records" / "agent-stream.jsonl")
comp = [(d.get("compact_metadata") or {}) for d in stream if d.get("type") == "system" and d.get("subtype") == "compact_boundary"]
boundaries = [ts(d["timestamp"]) for d in tr if d.get("type") == "system" and d.get("subtype") == "compact_boundary" and d.get("timestamp") and ts(d["timestamp"]) <= WIN]
prog_starts = [ts(p["startedAt"]) for p in before]
compact_rows = []
for i, b in enumerate(boundaries):
    window = [x for x in calls if b <= x["t"] <= b + timedelta(seconds=60)]
    t_ = " ".join(str(x["input"]) for x in window)
    first_read = min(((x["t"] - b).total_seconds() for x in window if "manifest" in str(x["input"])), default=None)
    nxt = next((x for x in prog_starts if x > b), None)
    compact_rows.append({"h": H4(b), "clock": clock(H4(b)), "read_infra": "infrastructure-manifest" in t_, "read_planning": "planning-manifest" in t_, "read_speedrun": "speedrun-manifest" in t_, "first_read_s": first_read, "to_next_program_s": (nxt - b).total_seconds() if nxt else None, "pre": comp[i].get("pre_tokens") if i < len(comp) else None})

# --- Dragon health and the crystals, from program output.
dragon = []
for p in before:
    t_ = txt_of(p)
    vals = [float(v) for v in re.findall(r'"phase":-?\d+,"hp":([\d.]+)\}', t_)] + [float(v) for v in re.findall(r"\bD([\d.]+)/ph-?\d", t_)] + [float(v) for v in re.findall(r"\bhp\s*(\d+(?:\.\d+)?)\s*ph\b", t_)]
    if vals:
        dragon.append({"h": H4(ts(p.get("endedAt") or p["startedAt"])), "hp": vals[-1], "min": min(vals)})
run2_json = json.loads((PROJECT / "preprint-run2" / "data" / "run2.json").read_text())
FIRST_TO_SPAWN = M["run2"]["spawn_to_first_program_s"] / 3600
crystal_left = []
for p in before:
    t_ = txt_of(p)
    for m in re.finditer(r"\bleft (\d+)\b(?: arrows (\d+))?", t_):
        if H4(ts(p["startedAt"])) > 5.7:
            crystal_left.append({"h": H4(ts(p.get("endedAt") or p["startedAt"])), "left": int(m.group(1)), "arrows": int(m.group(2)) if m.group(2) else None})
fight_programs = [p for p in before if "fightStep" in p["code"] and not INSTALL(p["code"])]
perches = []
for p in fight_programs:
    cur = None
    for line in str(p.get("returned") or "").split("\n"):
        m = re.search(r"phase \d+->6 at .* yaw (\d+)", line)
        if m:
            cur = {"seq": p["seq"], "yaw": int(m.group(1)), "hits": 0, "damage": 0.0}
            perches.append(cur)
        m = re.search(r"dragon hp ([\d.]+)->([\d.]+)", line)
        if m and cur:
            cur["hits"] += 1
            cur["damage"] += float(m.group(1)) - float(m.group(2))
dragon.sort(key=lambda x: x["h"])
last_crystal = c("6:35:30")
end_stats = {"perches": perches, "first_end_entry_h": M["run4"]["milestones"]["the_end"], "last_crystal_h": last_crystal, "last_crystal_to_win_min": (D["official_h"] - last_crystal) * 60, "crystal_left": crystal_left, "fight_programs": len(fight_programs),
             "first_fight_step_h": H4(ts(fight_programs[0]["startedAt"])) if fight_programs else None, "last_fight_step_h": H4(ts(fight_programs[-1]["startedAt"])) if fight_programs else None}
end_stats["hp_at_last_crystal"] = next((x["hp"] for x in dragon if x["h"] >= last_crystal and x["hp"] < 200), None)

# --- Tokens, cost and effort.
results = [d for d in stream if d.get("type") == "result"]
efforts = Counter()
for d in tr:
    if d.get("type") == "api-request" and d.get("timestamp") and ts(d["timestamp"]) <= WIN:
        efforts[str((d.get("params") or {}).get("output_config", {}).get("effort"))] += 1
cost = {"total_usd": results[-1].get("total_cost_usd") if results else None, "turns": results[-1].get("num_turns") if results else None, "duration_ms": results[-1].get("duration_ms") if results else None, "api_ms": results[-1].get("duration_api_ms") if results else None, "model_usage": results[-1].get("modelUsage") if results else None, "results": len(results), "effort_requests": efforts.most_common()}

# --- After the win.
after = [p for p in programs if ts(p["startedAt"]) > WIN]
resp_after = [e for e in events if e["type"] == "bot_respawn" and ts(e["t"]) > WIN]
death_after = [e for e in events if e["type"] in ("death", "bot_death") and ts(e["t"]) > WIN]
frames_after = [(f["t"], f["dim"]) for t, f in fr_t if t > WIN][:12]
after_win = {"programs": len(after), "starts": [H4(ts(p["startedAt"])) for p in after], "respawn_s_after_win": (ts(resp_after[0]["t"]) - WIN).total_seconds() if resp_after else None, "deaths_after_win": len(death_after), "frames": frames_after,
             "last_output": txt_of(after[-1])[-260:] if after else None}
frame_stats = {"to_win": sum(1 for t, _ in fr_t if t <= WIN), "total": len(frames), "max_gap_s": max((fr_t[i + 1][0] - fr_t[i][0]).total_seconds() for i in range(len(fr_t) - 1) if fr_t[i + 1][0] <= WIN), "median_gap_s": statistics.median((fr_t[i + 1][0] - fr_t[i][0]).total_seconds() for i in range(len(fr_t) - 1) if fr_t[i + 1][0] <= WIN)}
server_log = (THIS / "records" / "server.log").read_text(errors="replace")
log_checks = {"win_line": next((l for l in server_log.splitlines() if "Free the End" in l), None), "cant_keep_up": len(re.findall("Can't keep up", server_log))}

# --- Bartering, as before.
barter = {"programs_naming_barter": sum(bool(re.search("barter", p["code"], re.I)) for p in before), "programs_piglin_and_gold_ingot": sum(bool(re.search("piglin", p["code"], re.I) and "gold_ingot" in p["code"]) for p in calls_only)}

(PRE / "data").mkdir(exist_ok=True)
TEAM = {"win_h": 1634 / 60, "programs": 2783, "distinct_lines": 63313, "deaths": 605, "milestones_min": {"stone_tools": 6, "iron_tools": 14, "bucket": 14, "flint_and_steel": 64, "nether_portal": 102, "fortress": 177, "ender_pearls": 186, "blaze_rods": 257, "eyes_of_ender": 643, "stronghold": 797, "the_end": 813, "ten_crystals": 1594, "dragon": 1634}}
out = {"runs": M, "team": TEAM, "rates": rates, "by_place": by_place, "recovery": recovery, "activity": activity, "sealed": sealed, "nether_entries": entries, "dim_changes": dim_changes, "rules": rules, "items": items, "tool_calls": tool_calls, "bash_calls": len(bash_calls), "clock_checks": clock_checks,
       "first_event_utc": first_event.isoformat(), "inherited_use": inherited_use, "lineage": lineage, "commits": series, "memory": memory, "compactions": compact_rows, "dragon": dragon, "dragon_run2": run2_json["run2"]["dragon"], "run2_ten_h_from_first_program": 8 + 10 / 60, "end": end_stats, "cost": cost, "after_win": after_win, "frames": frame_stats, "log_checks": log_checks, "barter": barter}
(PRE / "data" / "run4.json").write_text(json.dumps(out, indent=1, default=str))

P = lambda name, v: print(name + ":", json.dumps(v, default=str))
for k in M:
    print(k, clock(M[k]["official_h"]), "from first program", clock(M[k]["from_first_program_h"]), "deaths", len(M[k]["deaths"]), "programs", M[k]["programs"]["before_end"], "real", M[k]["programs"]["real"], "chain5", M[k]["chain_5min"], "chain10", M[k]["chain_10min"], "mingap", round(M[k]["min_gap_min"], 1), "between", M[k]["deaths_between_programs"], "20s", M[k]["deaths_within_20s_of_program_end"], "running", round(M[k]["running_share"], 3), "lines", M[k]["programs"]["distinct_lines"], "median", M[k]["programs"]["median_s_real"])
    print("   pauses", {a: round(b, 1) for a, b in M[k]["pauses"].items()}, "restarts", M[k]["server_restarts"], "connects", M[k]["bot_connects"])
    print("   world", {a: (round(b, 1) if isinstance(b, float) else b) for a, b in M[k]["world"].items() if a not in ("path_blocks", "path_hours", "blocks_per_h")})
    print("   path", {a: round(b) for a, b in M[k]["world"]["path_blocks"].items()}, "bph", {a: round(b) for a, b in M[k]["world"]["blocks_per_h"].items()})
    print("   places", {a: M[k]["places"][a] for a in ("deaths_with_frame", "returned", "never", "median_back_s", "within_300s", "deaths_by_dim", "respawns_at_world_spawn")})
    print("   tokens", M[k]["tokens"])
P("rates", rates)
P("by_place", by_place)
P("recovery", recovery)
print("activity minutes", {k: round(v, 1) for k, v in by_kind.items()}, "share", round(activity["share_recover"], 3), "work", round(activity["work_min"], 1))
for s in stage_table:
    print("  ", s["label"], "budget", s["budget"], "work", round(s["work"], 1), "recover", round(s["recover"], 1), "actual", round(s["actual"], 1), "over", round(s["over"], 1))
P("sealed", sealed)
P("entries", entries)
P("rules", {k: v for k, v in rules.items() if k not in ("floor_hits_detail",)})
P("tool_calls", tool_calls)
print("bash", len(bash_calls), "clock checks", clock_checks)
P("inherited", {k: v for k, v in inherited_use.items() if k not in ("text", "hours")})
for x in inherited_use["text"]:
    print("  ", x["h"], x["runs"], x["text"][:130].replace("\n", " / "))
P("lineage", {k: v for k, v in lineage.items() if k not in ("per_file", "per_hour")})
P("per_hour", lineage["per_hour"])
for x in per_file[:18]:
    print("  ", x["file"], x["lines"], x["by_origin"], "unch3" if x["unchanged_from_run3"] else "", "unch2" if x["unchanged_from_run2"] else "")
P("memory", memory)
P("compactions", compact_rows)
print("commits")
for s in series:
    print("  ", s["clock"], s["hash"], s["lib_lines"], s["lib"], "|", s["subject"][:70], "|", (s["cut"] or "")[:90])
P("end", {k: v for k, v in end_stats.items() if k != "crystal_left"})
print("crystal left", [(clock(x["h"]), x["left"], x["arrows"]) for x in crystal_left])
print("dragon", [(clock(x["h"]), x["hp"]) for x in dragon if x["h"] > 6.3])
P("cost", cost)
P("after", after_win)
P("frames", frame_stats)
P("log", log_checks)
P("barter", barter)
print("deaths")
for d in D["deaths"]:
    print("  ", d["clock"], d["cause"], d["dim"], d["in_program"], d["since_program_end_s"], d["pos"], "|", d["text"])
print("gaps", [round(g, 1) for g in D["death_gaps_min"]])
