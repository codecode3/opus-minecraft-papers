#!/usr/bin/env python3
"""Pull the numbers the second team-run preprint needs out of run 2026-11-14-2158-team's records.

    python3 preprint-team2/scripts/run_data.py   -> preprint-team2/data/team2.json

Reads only. Times are seconds or hours on the OFFICIAL clock, from the agents' first spawn (first
bot_connected), and everything is cut at the win unless a name says otherwise.

The people's account names are read from run.json and replaced by "Human 1" and "Human 2", in the
order run.json lists them, everywhere in the output, chat quotes included. In the agents' own chat
lines the short forms of their names are written out in full (FableFox, FableFire).

The dragon's health comes from the agents' own fight logs ("dragon hp a->b" lines, written with
Date.now() % 1e6 / 1000, so epoch seconds modulo 1000). Each drop is tied to what the same
log line says the logging agent was doing, and to arrows the agents' mortar programs report.
"""
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PRE = Path(__file__).resolve().parent.parent
PROJECT = PRE.parent
ID = "2026-11-14-2158-team"
RUN = next(p / "runs" / ID for p in [PROJECT, *PROJECT.parents] if (p / "runs" / ID).exists())
REC = RUN / "records"
AGENTS = ["FableFox", "FableFire"]
META = json.loads((RUN / "run.json").read_text())
PEOPLE = META["humans"]
LABEL = {name: f"Human {i + 1}" for i, name in enumerate(PEOPLE)}
SHORT = {name: [w for w in re.findall(r"[A-Z][a-z]+", name) if len(w) >= 4] for name in PEOPLE}


def anon(s):
    for name, lab in LABEL.items():
        s = re.sub(re.escape(name), lab, s, flags=re.I)
        for nick in SHORT.get(name, []):
            s = re.sub(r"\b" + nick + r"\b", lab, s, flags=re.I)
    return s


def full(s):
    """An agent's own short forms of the agents' names, written out."""
    s = re.sub(r"(?<![A-Za-z])Fox\b", "FableFox", s)
    return re.sub(r"(?<![A-Za-z])Fire\b", "FableFire", s)


def who(p):
    return LABEL.get(p, p)


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


def clock(sec):
    s = int(round(sec))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def text_of(p):
    r = p.get("returned")
    r = r if isinstance(r, str) else json.dumps(r)
    return ((p.get("output") or "") + "\n" + (r or "")).replace("\\n", "\n").replace('\\"', '"')


# --- Clock.
events = jl(REC / "events.jsonl")
programs = {a: jl(REC / f"programs-{a}.jsonl") for a in AGENTS}
SPAWN = min(ts(e["t"]) for e in events if e["type"] == "bot_connected")
WIN_EV = next(e for e in events if e["type"] == "win")
WIN = ts(WIN_EV["t"])
WIN_S = WIN_EV["elapsedMs"] / 1000
T0 = min(ts(p["startedAt"]) for a in AGENTS for p in programs[a])
S = lambda t: (t - SPAWN).total_seconds()
clock_ = {"spawn_utc": SPAWN.isoformat(), "first_program_utc": T0.isoformat(), "win_utc": WIN.isoformat(), "official_s": WIN_S,
          "official": clock(WIN_S), "from_first_program_s": WIN_EV["elapsedFromFirstProgramMs"] / 1000,
          "programs_before_win_event": WIN_EV["programsBeforeWin"], "spawn_to_first_program_s": S(T0), "winner": who(WIN_EV["player"]),
          "first_program_s": {a: S(min(ts(p["startedAt"]) for p in programs[a])) for a in AGENTS}}

# --- Steps and advancements.
milestones = {e["key"]: {"s": S(ts(e["t"])), "clock": clock(S(ts(e["t"]))), "by": who(e["player"])} for e in events if e["type"] == "milestone"}
adv = [{"s": S(ts(e["t"])), "by": who(e["player"]), "text": e["text"]} for e in events if e["type"] == "advancement" and ts(e["t"]) <= WIN]
first_adv = {}
for a in adv:
    first_adv.setdefault(a["by"], {}).setdefault(a["text"], a["s"])

# --- Where each agent was: the dimension at the end of each program.
DIM_RE = re.compile(r"\bt\d+ (overworld|the_nether|the_end)\b|\bdim(?:ension)? (overworld|the_nether|the_end)\b")
dims = {}
for a in AGENTS:
    seq = []
    for p in programs[a]:
        m = DIM_RE.findall(text_of(p))
        if m:
            d = [x or y for x, y in m][-1]
            t = ts(p.get("endedAt") or p["startedAt"])
            if not seq or seq[-1]["dim"] != d:
                seq.append({"s": S(t), "dim": d, "seq": p["seq"]})
    dims[a] = seq
dim_hours = {}
for a in AGENTS:
    seq = [x for x in dims[a] if x["s"] < WIN_S] + [{"s": WIN_S, "dim": None}]
    acc = Counter()
    for u, v in zip(seq, seq[1:]):
        acc[u["dim"]] += (v["s"] - u["s"]) / 3600
    acc["overworld"] += seq[0]["s"] / 3600
    dim_hours[a] = {k: round(v, 3) for k, v in acc.items()}
entries = {}
for a in AGENTS:
    ent = [s for prev, s in zip(dims[a], dims[a][1:]) if prev["dim"] == "overworld" and s["dim"] == "the_nether" and s["s"] < WIN_S]
    by_seq = {p["seq"]: p for p in programs[a]}
    entries[a] = {"n": len(ent), "clocks": [clock(s["s"]) for s in ent], "gate_in_code": sum(bool(re.search(r"gate", by_seq[s["seq"]]["code"], re.I)) for s in ent),
                  "gate_refusals": sum("GATE" in text_of(p) and "refus" in text_of(p).lower() for p in programs[a])}

# --- Deaths.
CAUSES = [("Own explosion", "blown up by"), ("Dragon breath", "ender dragon using magic"), ("Dragon (fall, contact)", "ender dragon"),
          ("Zombified piglins", "zombified piglin"), ("Spiders", "spider"), ("Endermen", "enderman"), ("Falls", "hit the ground"), ("Falls", "fell")]
deaths = []
for e in events:
    if e["type"] != "death" or ts(e["t"]) > WIN:
        continue
    t = S(ts(e["t"]))
    cause = next((lab for lab, key in CAUSES if key in e["text"].lower()), "Other")
    d = {"s": t, "clock": clock(t), "player": who(e["player"]), "agent": e["player"] in AGENTS, "cause": cause, "text": anon(e["text"])}
    if d["agent"]:
        past = [x for x in dims[e["player"]] if x["s"] < t - 10]
        d["dim"] = past[-1]["dim"] if past else "overworld"
    deaths.append(d)
death_stats = {"total": len(deaths), "agents": sum(d["agent"] for d in deaths), "people": sum(not d["agent"] for d in deaths),
               "by_player": Counter(d["player"] for d in deaths), "causes_people": Counter(d["cause"] for d in deaths if not d["agent"]),
               "people_before_end": sum((not d["agent"]) and d["s"] < milestones["the_end"]["s"] for d in deaths),
               "agent_rate_per_agent_hour": sum(d["agent"] for d in deaths) / (2 * WIN_S / 3600)}


# --- Programs.
def merge(spans):
    out = []
    for a_, b_ in sorted(spans):
        if out and a_ <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b_)
        else:
            out.append([a_, b_])
    return out


prog_stats, all_spans, all_lines = {}, [], set()
for a in AGENTS:
    started = [p for p in programs[a] if ts(p["startedAt"]) <= WIN]
    before = [p for p in started if p.get("endedAt") and ts(p["endedAt"]) <= WIN]
    spans = [(S(ts(p["startedAt"])), min(S(ts(p["endedAt"])) if p.get("endedAt") else WIN_S, WIN_S)) for p in started]
    all_spans += spans
    m = merge(spans)
    lines = {l.strip() for p in started for l in p["code"].splitlines() if l.strip() and not l.strip().startswith("//")}
    all_lines |= lines
    pauses = [m[i + 1][0] - m[i][1] for i in range(len(m) - 1)]
    durs = [(p.get("durationMs") or 0) / 1000 for p in before]
    ws = RUN / f"workspace-{a}"
    count = lambda d: sum(len(f.read_text(errors="replace").splitlines()) for f in d.glob("*") if f.is_file() and not f.name.startswith("."))
    prog_stats[a] = {"started_before_win": len(started), "ended_before_win": len(before), "after_win": len(programs[a]) - len(started),
                     "median_s": statistics.median(durs), "over_60s": sum(d >= 60 for d in durs),
                     "running_share": sum(b_ - a_ for a_, b_ in m) / (WIN_S - spans[0][0]), "distinct_lines": len(lines),
                     "timed_out": sum(bool(p.get("timedOut")) for p in started), "errors": sum(bool(p.get("error")) for p in started),
                     "longest_pause_s": max(pauses), "median_pause_s": statistics.median(pauses),
                     "per_quarter_hour": sorted(Counter(int(S(ts(p["startedAt"])) // 900) for p in started).items()),
                     "spans": [[round(a_), round(b_)] for a_, b_ in m],
                     "lib_files": len(list((ws / "lib").glob("*"))), "lib_lines": count(ws / "lib"), "prog_files": len(list((ws / "prog").glob("*"))),
                     "lessons_lines": len((ws / "memory" / "02-lessons.md").read_text().splitlines())}
mu = merge(all_spans)
prog_stats["both"] = {"started_before_win": sum(prog_stats[a]["started_before_win"] for a in AGENTS), "distinct_lines": len(all_lines),
                      "errors": sum(prog_stats[a]["errors"] for a in AGENTS), "timed_out": sum(prog_stats[a]["timed_out"] for a in AGENTS),
                      "running_share_any": sum(b_ - a_ for a_, b_ in mu) / (WIN_S - S(T0))}

# --- Chat.
chat = [e for e in events if e["type"] == "chat"]
chat_before = [e for e in chat if ts(e["t"]) <= WIN]
agent_msgs = [ts(e["t"]) for e in chat if e["player"] in AGENTS]
waits = []
for e in chat_before:
    if e["player"] in PEOPLE:
        nxt = next((x for x in agent_msgs if x > ts(e["t"])), None)
        if nxt:
            waits.append((nxt - ts(e["t"])).total_seconds())
per_quarter = defaultdict(Counter)
for e in chat_before:
    per_quarter[who(e["player"])][int(S(ts(e["t"])) // 900)] += 1
# The harness splits a long line in two events at the same second; count those as one message.
def messages(player):
    n, last = 0, None
    for e in chat_before:
        if e["player"] == player:
            if last is None or (ts(e["t"]) - last).total_seconds() > 0.5:
                n += 1
            last = ts(e["t"])
    return n
chat_stats = {"lines_before_win": Counter(who(e["player"]) for e in chat_before), "lines_total": len(chat), "lines_before_win_total": len(chat_before),
              "messages_before_win": {who(p): messages(p) for p in AGENTS + PEOPLE},
              "wait_s": {"median": statistics.median(waits), "p90": sorted(waits)[int(0.9 * len(waits))], "within_60s": sum(w <= 60 for w in waits) / len(waits), "n": len(waits), "max": max(waits)},
              "per_quarter_hour": {k: sorted(v.items()) for k, v in per_quarter.items()}}
chat_log = [{"s": S(ts(e["t"])), "clock": clock(S(ts(e["t"]))), "by": who(e["player"]),
             "text": full(anon(e["text"])) if e["player"] in AGENTS else anon(e["text"])} for e in chat]

# --- People on the server.
joins = [e for e in events if e["type"] in ("player_join", "player_leave") and e["player"] in PEOPLE]
presence = {}
for p in PEOPLE:
    spans, on = [], None
    for e in sorted((e for e in joins if e["player"] == p), key=lambda e: e["t"]):
        if e["type"] == "player_join" and on is None:
            on = S(ts(e["t"]))
        elif e["type"] == "player_leave" and on is not None:
            spans.append([on, S(ts(e["t"]))])
            on = None
    if on is not None:
        spans.append([on, WIN_S])
    spans = [[a_, min(b_, WIN_S)] for a_, b_ in spans if a_ <= WIN_S]
    presence[who(p)] = {"spans": spans, "first_join_s": spans[0][0], "joins": len(spans)}

# --- The dragon's health, from both agents' fight logs.
LINE = re.compile(r"(?m)^(\d+\.\d) (.*)$")
drops, samples = {}, []
for a in AGENTS:
    for p in programs[a]:
        if S(ts(p["startedAt"])) < milestones["the_end"]["s"] - 60:
            continue
        s0 = ts(p["startedAt"])
        e0 = s0.timestamp()  # the logs' clock is epoch seconds modulo 1000
        t_ = text_of(p)
        for m in LINE.finditer(t_):
            c = float(m.group(1))
            t = e0 - e0 % 1000 + c
            if t < e0 - 5:
                t += 1000
            when = s0 + timedelta(seconds=t - e0)
            line = m.group(2)
            ph = re.search(r"\bD([\d.]+)/ph(-?\d+)", line)
            if ph:
                samples.append({"s": S(when), "hp": float(ph.group(1)), "phase": int(ph.group(2)), "agent": a})
            dm = re.match(r"dragon hp ([\d.]+)->([\d.]+)", line)
            if dm:
                k = (round(float(dm.group(1)), 3), round(float(dm.group(2)), 3))
                drops.setdefault(k, []).append({"s": S(when), "agent": a, "seq": p["seq"], "line": line})
        for m in re.finditer(r'"phase":(-?\d+),"hp":([\d.]+)\}', t_):
            samples.append({"s": S(ts(p.get("endedAt") or p["startedAt"])), "hp": float(m.group(2)), "phase": int(m.group(1)), "agent": a})
by_from = defaultdict(list)
for (a_, b_), v in drops.items():
    by_from[a_].append((b_, min(x["s"] for x in v), v))
chain, known = [], sorted(by_from)
hp = max(known) if known else 0
while known:
    opts = by_from.get(hp)
    if not opts:
        nxt = max((k for k in known if k < hp), default=None)
        if nxt is None:
            break
        chain.append({"gap": True, "from": hp, "to": nxt})
        hp = nxt
        continue
    b_, t, v = max(opts, key=lambda o: o[0])
    chain.append({"gap": False, "from": hp, "to": b_, "s": t, "clock": clock(t), "d": round(hp - b_, 3), "logged_by": sorted({y["agent"] for y in v}), "line": v[0]["line"]})
    hp = b_
    if hp <= 0:
        break
samples.sort(key=lambda s: s["s"])
# FableFire's bot reconnected at 1:39:28 and its library read the old bot's frozen data until it was reinstalled,
# so the health curve is the running minimum of every reading.
curve, low = [], 200.0
for s in samples:
    if s["s"] <= WIN_S + 3 and s["hp"] < low - 1e-6:
        low = s["hp"]
        curve.append([round(s["s"], 1), round(low, 2)])
# Crystals: each agent's mortar log lists the crystal it shot at and whether it was gone afterwards.
crystals = {}
for a in AGENTS:
    gone, arrows, hits = {}, [], 0
    for p in programs[a]:
        t_ = text_of(p)
        for m in re.finditer(r'"c":"([-\d,]+)","end":"[^"]*","n":\d+,"gone":true', t_):
            gone.setdefault(m.group(1), clock(S(ts(p["startedAt"]))))
        arrows += [int(x) for x in re.findall(r"arrows (\d+) hp", t_)]
        hits += sum(int(x) for x in re.findall(r"(?m)^hits (\d+) stop", t_))
    crystals[a] = {"gone_after_its_shot": gone, "arrows_first_last": [arrows[0], arrows[-1]] if arrows else None, "sword_hits_on_dragon": hits}
seen10 = next((re.search(r"crystals 10 ([-\d, ]+)", text_of(p)) for a in AGENTS for p in programs[a] if "crystals 10 " in text_of(p)), None)
crystals["all_ten"] = seen10.group(1).split() if seen10 else None
crystals["not_in_either_log"] = [c for c in (crystals["all_ten"] or []) if all(c not in crystals[a]["gone_after_its_shot"] for a in AGENTS)]
last_c = next(e for e in chat if e["player"] == "FableFire" and "all crystals dead" in e["text"])
crystals["all_dead_said_s"] = S(ts(last_c["t"]))
dragon = {"curve": curve, "crystals": crystals, "chain": chain, "top_of_chain": max(known) if known else None,
          "series": [{"s": round(s["s"], 1), "hp": s["hp"], "phase": s["phase"]} for s in samples if s["s"] <= WIN_S + 3]}

# --- Model use: each session's result line, context size per request, compactions, the usage window.
SESS = {v["sessionId"]: a for a, v in META["agents"].items()}
usage, context, compactions, limits, turns, tools, efforts, hooks = {}, {}, [], {}, {}, {}, Counter(), []
for a in AGENTS:
    st = jl(REC / f"agent-stream-{a}.jsonl")
    res = [d for d in st if d.get("type") == "result"][-1]
    mu_ = list(res["modelUsage"].values())[0]
    usage[a] = {"usd": res["total_cost_usd"], "turns": res["num_turns"], "duration_s": res["duration_ms"] / 1000, "api_s": res["duration_api_ms"] / 1000,
                "cache_read": mu_["cacheReadInputTokens"], "cache_write_1h": mu_["cacheCreationEphemeral1hInputTokens"], "cache_write_5m": mu_["cacheCreationEphemeral5mInputTokens"],
                "input": mu_["inputTokens"], "output": mu_["outputTokens"], "thinking": mu_.get("thinkingTokens"), "context_window": mu_.get("contextWindow"),
                "model": list(res["modelUsage"])[0]}
    stamp, rows = None, []
    for d in st:
        if d.get("timestamp"):
            stamp = d["timestamp"]
        if d.get("type") == "rate_limit_event":
            i = d["rate_limit_info"]
            w = i.get("unifiedWindows") or {}
            rows.append({"s": round(S(ts(stamp))) if stamp else 0, "status": i.get("status"), "five_hour": (w.get("five_hour") or {}).get("utilization"),
                         "five_hour_resets_s": round((w.get("five_hour") or {}).get("resetsAt", 0) - SPAWN.timestamp()),
                         "seven_day": (w.get("seven_day") or {}).get("utilization"), "seven_day_resets_s": round((w.get("seven_day") or {}).get("resetsAt", 0) - SPAWN.timestamp()),
                         "overage": i.get("overageStatus"), "overage_reason": i.get("overageDisabledReason")})
        if d.get("type") == "system" and d.get("subtype") == "compact_boundary":
            m = d.get("compact_metadata") or {}
            compactions.append({"agent": a, "s": round(S(ts(stamp))), "pre": m.get("pre_tokens"), "post": m.get("post_tokens")})
    limits[a] = rows
    tr = REC / "transcripts" / f"{META['agents'][a]['sessionId']}.jsonl"
    seen, ctx, n, tl = set(), [], 0, Counter()
    for d in jl(tr):
        if d.get("type") == "user" and d.get("timestamp") and "Stop hook feedback" in json.dumps(d.get("message", "")):
            hooks.append({"agent": a, "clock": clock(S(ts(d["timestamp"])))})
        if d.get("type") != "assistant" or not d.get("timestamp"):
            continue
        msg = d["message"]
        for c in msg["content"]:
            if c["type"] == "tool_use":
                tl[c["name"]] += 1
        if msg.get("id") in seen:
            continue
        seen.add(msg.get("id"))
        u = msg.get("usage") or {}
        tot = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        c = S(ts(d["timestamp"]))
        if tot and c <= WIN_S + 240:
            ctx.append([round(c), tot])
            n += c <= WIN_S
    context[a], turns[a], tools[a] = ctx, n, dict(tl)
    usage[a]["requests_to_win"] = n
    usage[a]["context_max"] = max(t for _, t in ctx)
    usage[a]["context_at_win"] = [t for c, t in ctx if c <= WIN_S][-1]
usage["total_usd"] = sum(usage[a]["usd"] for a in AGENTS)
all_limits = sorted((r for a in AGENTS for r in limits[a]), key=lambda r: r["s"])
usage["window"] = {"first": all_limits[0], "last": all_limits[-1], "peak_five_hour": max(r["five_hour"] for r in all_limits),
                   "refused": sum(r["status"] != "allowed" for r in all_limits), "rows": len(all_limits),
                   "at_win": [r for r in all_limits if r["s"] <= WIN_S][-1]}

# --- After the win.
after = {}
for a in AGENTS:
    jumped = next((p for p in programs[a] if ts(p["startedAt"]) > WIN and re.search(r"overworld", text_of(p))), None)
    after[a] = {"programs": prog_stats[a]["after_win"], "overworld_program_end_s": S(ts(jumped["endedAt"])) - WIN_S if jumped else None}
after["deaths_after_win"] = sum(e["type"] == "death" and ts(e["t"]) > WIN for e in events)

# --- Server log, connections and camera checks.
log = (REC / "server.log").read_text(errors="replace")
frames = sorted(jl(RUN / "server" / "camera" / "frames.jsonl"), key=lambda f: f["t"])
ft = [ts(f["t"]) for f in frames if ts(f["t"]) <= WIN]
gaps_f = [(ft[i + 1] - ft[i]).total_seconds() for i in range(len(ft) - 1)]
checks = {"win_line": anon(next((l for l in log.splitlines() if "has made the advancement [Free the End]" in l), "")),
          "rcon_client_times": re.findall(r"\[(\d\d:\d\d:\d\d)\] \[RCON Listener #1/INFO\]: Thread RCON Client", log),
          "issued_commands": len(re.findall(r"issued server command", log)), "cant_keep_up": len(re.findall("Can't keep up", log)),
          "ops": json.loads((RUN / "server" / "ops.json").read_text()),
          "bot_connects": Counter(e["player"] for e in events if e["type"] == "bot_connected"),
          "bot_kicks": [{"clock": clock(S(ts(e["t"]))), "player": e["player"]} for e in events if e["type"] == "bot_kicked" and ts(e["t"]) <= WIN],
          "server_ready_events": sum(e["type"] == "server_ready" for e in events),
          "frames_to_win": len(ft), "frame_median_gap_s": statistics.median(gaps_f), "frame_max_gap_s": max(gaps_f),
          "frames_by_player": Counter(f.get("player") for f in frames if ts(f["t"]) <= WIN),
          "slash_commands_in_programs": {a: sum(bool(re.search(r"bot\.chat\(\s*['\"`]/", p["code"])) for p in programs[a]) for a in AGENTS}}
BEDCALL = re.compile(r"\bL\.(placeBed|bedCamp|setSpawn)\(|\bbot\.sleep\(")
LIBDEF = re.compile(r"L\.(placeBed|bedCamp|setSpawn)\s*=\s*async")
checks["bed_calls_outside_overworld"] = {}
for a in AGENTS:
    n = 0
    for p in programs[a]:
        past = [x for x in dims[a] if x["s"] <= S(ts(p["startedAt"]))]
        away = past and past[-1]["dim"] != "overworld"
        if LIBDEF.search(p["code"]):
            continue
        n += bool(away and any(BEDCALL.search(l) and not l.strip().startswith("//") for l in p["code"].splitlines()))
    checks["bed_calls_outside_overworld"][a] = n

# --- Earlier runs, on the official clock (seconds): run 5 and the first team run from their papers' data.
R5 = json.loads((PROJECT / "preprint-run5" / "data" / "run5.json").read_text())
earlier = {"run5": {"official_s": R5["win_s"], "milestones": {m["key"]: m["clock"] for m in R5["milestones"]} if isinstance(R5["milestones"], list) else R5["milestones"],
                    "deaths": len(R5["deaths"]), "programs": R5["programs"]["to_win"], "usd": R5["usage"]["cost_usd"]}}
# The first team run (two Opus 5.5 agents and the same two people), from its published paper.
T1H = {"stone_tools": 0.04517472222222222, "iron_tools": 0.24059166666666668, "bucket": 0.24106666666666668, "flint_and_steel": 0.7723561111111111,
       "nether_portal": 0.8115341666666667, "fortress": 0.9274441666666666, "ender_pearls": 1.0079913888888887, "blaze_rods": 1.0533669444444445,
       "eyes_of_ender": 2.8725055555555556, "stronghold": 3.502314722222222, "the_end": 3.503148611111111, "ten_crystals": 3.7324755555555558, "dragon": 4.6044413888888895}
R4 = json.loads((PROJECT / "preprint-run4" / "data" / "run4.json").read_text())
earlier["gemini_team"] = {"milestones": {k: v * 60 for k, v in R4["team"]["milestones_min"].items()}}
earlier["run5"]["ten_crystals_s"] = 3 * 3600 + 42 * 60
earlier["team1"] = {"official_s": 16575.989, "milestones": {k: v * 3600 for k, v in T1H.items()}, "agent_deaths": 7, "people_deaths": 31, "programs": 695, "usd": 87.57,
                    "chat_lines": 367, "wait_median_s": 42}

out = {"run": ID, "model": META["model"], "effort": META["effort"], "inherit": META["inheritFrom"], "clock": clock_, "milestones": milestones, "first_adv": first_adv,
       "advancements": adv, "dims": dims, "dim_hours": dim_hours, "entries": entries, "deaths": deaths, "death_stats": death_stats, "programs": prog_stats,
       "chat": chat_stats, "presence": presence, "dragon": dragon, "usage": usage, "context": context, "compactions": compactions,
       "limits": limits, "tools": tools, "hooks": hooks, "after_win": after, "checks": checks, "earlier": earlier, "people": list(LABEL.values())}
(PRE / "data").mkdir(exist_ok=True)
(PRE / "data" / "team2.json").write_text(json.dumps(out, indent=1, default=str))

P = lambda name, v: print(name + ":", json.dumps(v, default=str))
P("clock", clock_)
for k, v in milestones.items():
    print("  ", k, v["clock"], v["by"])
P("dims", {a: [(clock(s["s"]), s["dim"]) for s in dims[a]] for a in AGENTS})
P("dim_hours", dim_hours)
P("entries", entries)
P("death_stats", death_stats)
P("programs", {a: {k: v for k, v in prog_stats[a].items() if k not in ("per_quarter_hour", "spans")} for a in AGENTS + ["both"]})
P("chat", {k: v for k, v in chat_stats.items() if k != "per_quarter_hour"})
P("presence", presence)
for x in chain:
    print("  ", x.get("clock"), f"{x['from']:.2f}->{x['to']:.2f}", x.get("d"), x.get("logged_by"), (x.get("line") or "GAP")[:150])
P("curve", curve)
P("crystals", crystals)
P("usage", usage)
P("compactions", compactions)
P("turns", turns)
P("tools", tools)
P("hooks", hooks)
P("after", after)
P("checks", checks)
P("earlier run5", earlier["run5"])
P("first_adv", {p: {k: clock(s) for k, s in v.items()} for p, v in first_adv.items()})
