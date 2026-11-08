#!/usr/bin/env python3
"""Pull the numbers the team-run preprint needs out of run 2026-11-07-2154-team's records.

    python3 preprint-team/scripts/run_data.py   -> preprint-team/data/team.json

Reads only. Times are hours on the OFFICIAL clock, from the agents' first spawn (first bot_connected),
unless a name says otherwise, and everything is cut at the win unless a name says otherwise.

The people's account names are read from run.json and replaced by "Human 1" and "Human 2", in the
order run.json lists them, everywhere in the output, chat quotes included.

The dragon's health comes from the agents' own fight logs ("dragon hp a->b" lines, written with
Date.now() % 1e6 / 1000, so seconds of the day modulo 1000) and is cross-checked against the server's
death messages and the agents' own health in the same log line. Each drop is attributed by rule:
  2.25 and 5.0 -> FoxglenOpus's stone sword (5/4+1 on a body part, 5 on the head);
  2.75 -> VoidmothOpus's diamond sword (7/4+1);
  a drop that, added to the one before it within 0.6 s, makes 2.75 -> VoidmothOpus's sword landing
      inside the dragon's half-second of hurt immunity, so the game applied only the excess;
  a drop with no agent sword size and the agent's own health falling in the same line -> an explosion;
  any other logged drop -> the people;
  a stretch the logs did not see -> the people when no agent fight program ran then, else unattributed.
"""
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PRE = Path(__file__).resolve().parent.parent
PROJECT = PRE.parent
ID = "2026-11-07-2154-team"
RUN = next(p / "runs" / ID for p in [PROJECT, *PROJECT.parents] if (p / "runs" / ID).exists())
REC = RUN / "records"
AGENTS = ["FoxglenOpus", "VoidmothOpus"]
META = json.loads((RUN / "run.json").read_text())
PEOPLE = META["humans"]
LABEL = {name: f"Human {i + 1}" for i, name in enumerate(PEOPLE)}
# Short forms used in chat: each capitalised part of an account name with 4+ letters, so no name is written here.
SHORT = {name: [w for w in re.findall(r"[A-Z][a-z]+", name) if len(w) >= 4] for name in PEOPLE}


def anon(s):
    for name, lab in LABEL.items():
        s = re.sub(re.escape(name), lab, s, flags=re.I)
        for nick in SHORT.get(name, []):
            s = re.sub(r"\b" + nick + r"\b", lab, s, flags=re.I)
    return s


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


def clock(h):
    s = int(round(h * 3600))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def cause(text):
    """The earlier papers' rule list, in its order, plus the bed explosion's message."""
    t = text.lower()
    rules = [
        ("Bed or anchor explosion", "intentional game design"), ("Own explosion", "blown up by"),
        ("Dragon breath", "ender dragon using magic"), ("Dragon (fall, contact)", "by ender dragon"),
        ("Void", "out of the world"), ("Drowning", "drown"),
        ("Lava and fire", "lava"), ("Lava and fire", "burn"), ("Lava and fire", "crisp"), ("Lava and fire", "flames"),
        ("Skeletons", "skeleton"), ("Zombies", "zombie"), ("Creepers", "creeper"), ("Spiders", "spider"),
        ("Silverfish", "silverfish"), ("Endermites", "endermite"), ("Piglins", "piglin"), ("Endermen", "enderman"), ("Blazes", "blaze"),
        ("Hoglins", "hoglin"), ("Falls", "fell"), ("Falls", "hit the ground"), ("Falls", "doomed to fall"),
    ]
    for label, key in rules:
        if key in t:
            return label
    return "Other"


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
T0 = min(ts(p["startedAt"]) for a in AGENTS for p in programs[a])
H = lambda t: (t - SPAWN).total_seconds() / 3600
clock_ = {"spawn_utc": SPAWN.isoformat(), "first_program_utc": T0.isoformat(), "win_utc": WIN.isoformat(), "official_h": WIN_EV["elapsedMs"] / 3.6e6,
          "from_first_program_h": WIN_EV["elapsedFromFirstProgramMs"] / 3.6e6, "programs_before_win_event": WIN_EV["programsBeforeWin"],
          "spawn_to_first_program_s": (T0 - SPAWN).total_seconds(), "winner": who(WIN_EV["player"]),
          "first_program_s": {a: (min(ts(p["startedAt"]) for p in programs[a]) - SPAWN).total_seconds() for a in AGENTS}}

# --- Steps (the server's first-of-anyone milestones) and advancements.
milestones = {e["key"]: {"h": H(ts(e["t"])), "clock": clock(H(ts(e["t"]))), "by": who(e["player"])} for e in events if e["type"] == "milestone"}
adv = [{"h": H(ts(e["t"])), "by": who(e["player"]), "text": e["text"]} for e in events if e["type"] == "advancement" and ts(e["t"]) <= WIN]
first_adv = {}
for a in adv:
    first_adv.setdefault(a["by"], {}).setdefault(a["text"], a["h"])

# --- Where each agent was: the dimension at the end of each program (the HUD's "t<ticks> <dim>").
DIM_RE = re.compile(r"\bt\d+ (overworld|the_nether|the_end)\b|\bdim (overworld|the_nether|the_end)\b")
dims = {}
for a in AGENTS:
    seq = []
    for p in programs[a]:
        m = DIM_RE.findall(text_of(p))
        if m:
            d = [x or y for x, y in m][-1]
            t = ts(p.get("endedAt") or p["startedAt"])
            if not seq or seq[-1]["dim"] != d:
                seq.append({"h": H(t), "dim": d, "seq": p["seq"]})
    dims[a] = seq

# --- Nether entries and the gate.
entries = {}
for a in AGENTS:
    ent = [s for prev, s in zip(dims[a], dims[a][1:]) if prev["dim"] == "overworld" and s["dim"] == "the_nether"]
    by_seq = {p["seq"]: p for p in programs[a]}
    refusals = [p["seq"] for p in programs[a] if "NETHER GATE:" in text_of(p) + str(p.get("error") or "") and ts(p["startedAt"]) <= WIN]
    entries[a] = {"n": len(ent), "clocks": [clock(s["h"]) for s in ent], "by_use_portal": sum("usePortal" in by_seq[s["seq"]]["code"] for s in ent),
                  "gate_refusals": len(refusals)}

# --- Deaths.
deaths = []
for e in events:
    if e["type"] != "death" or ts(e["t"]) > WIN:
        continue
    t = ts(e["t"])
    d = {"h": H(t), "clock": clock(H(t)), "player": who(e["player"]), "agent": e["player"] in AGENTS, "cause": cause(e["text"]), "text": anon(e["text"])}
    if e["player"] in AGENTS:
        # The bot respawns at once, so the program the death ended already prints the Overworld; use those
        # that ended at least 10 s before it.
        past = [s for s in dims[e["player"]] if s["h"] < d["h"] - 10 / 3600]
        d["dim"] = past[-1]["dim"] if past else "overworld"
        bd = [x for x in events if x["type"] == "bot_death" and x["player"] == e["player"] and abs((ts(x["t"]) - t).total_seconds()) < 5]
        d["pos"] = bd[0]["pos"] if bd else None
    deaths.append(d)
END_ENTRY_H = milestones["the_end"]["h"]
death_stats = {
    "total": len(deaths), "agents": sum(d["agent"] for d in deaths), "people": sum(not d["agent"] for d in deaths),
    "by_player": Counter(d["player"] for d in deaths), "people_before_end": sum((not d["agent"]) and d["h"] < END_ENTRY_H for d in deaths),
    "people_in_end_window": sum((not d["agent"]) and d["h"] >= END_ENTRY_H for d in deaths),
    "causes_agents": Counter(d["cause"] for d in deaths if d["agent"]), "causes_people": Counter(d["cause"] for d in deaths if not d["agent"]),
    "agent_rate_per_agent_hour": sum(d["agent"] for d in deaths) / (2 * clock_["official_h"]),
}

# --- Programs.
def merge(spans):
    out = []
    for a_, b_ in sorted(spans):
        if out and a_ <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b_)
        else:
            out.append([a_, b_])
    return out


prog_stats = {}
all_spans, all_lines = [], set()
for a in AGENTS:
    before = [p for p in programs[a] if p.get("endedAt") and ts(p["endedAt"]) <= WIN]  # the harness's count: ended before the win
    spans = [(ts(p["startedAt"]), ts(p["endedAt"]) if p.get("endedAt") else ts(p["startedAt"])) for p in before]
    all_spans += spans
    m = merge(spans)
    t0 = min(s for s, _ in spans)
    lines = {l.strip() for p in before for l in p["code"].splitlines() if l.strip() and not l.strip().startswith("//")}
    all_lines |= lines
    pph = Counter(int(H(ts(p["startedAt"])) * 4) for p in before)
    pauses = [(m[i + 1][0] - m[i][1]).total_seconds() for i in range(len(m) - 1)]
    prog_stats[a] = {"before_win": len(before), "running_at_win": sum(ts(p["startedAt"]) <= WIN for p in programs[a]) - len(before),
                     "after_win": sum(ts(p["startedAt"]) > WIN for p in programs[a]),"median_s": statistics.median((p.get("durationMs") or 0) / 1000 for p in before),
                     "running_share": sum((b_ - a_).total_seconds() for a_, b_ in m) / (WIN - t0).total_seconds(), "distinct_lines": len(lines),
                     "per_quarter_hour": sorted(pph.items()), "timed_out": sum(bool(p.get("timedOut")) for p in before), "errors": sum(bool(p.get("error")) for p in before),
                     "median_pause_s": statistics.median(pauses), "total_pause_h": sum(pauses) / 3600, "longest_pause_s": max(pauses),
                     "prog_files": sum(1 for _ in (RUN / f"workspace-{a}" / "prog").glob("*"))}
mu = merge(all_spans)
prog_stats["both"] = {"before_win": sum(prog_stats[a]["before_win"] for a in AGENTS), "distinct_lines": len(all_lines),
                      "running_share_any": sum((b_ - a_).total_seconds() for a_, b_ in mu) / (WIN - T0).total_seconds()}

# --- Chat.
chat = [e for e in events if e["type"] == "chat"]
chat_before = [e for e in chat if ts(e["t"]) <= WIN]
agent_msgs = [ts(e["t"]) for e in chat if e["player"] in AGENTS]
waits = []
for e in chat_before:
    if e["player"] in PEOPLE:
        t = ts(e["t"])
        nxt = next((x for x in agent_msgs if x > t), None)
        if nxt:
            waits.append((nxt - t).total_seconds())
joins = [e for e in events if e["type"] in ("player_join", "player_leave") and e["player"] in PEOPLE]
first_join = {who(p): H(min(ts(e["t"]) for e in joins if e["player"] == p and e["type"] == "player_join")) for p in PEOPLE}
per_quarter = defaultdict(Counter)
for e in chat_before:
    per_quarter[who(e["player"])][int(H(ts(e["t"])) * 4)] += 1
chat_stats = {"messages_before_win": Counter(who(e["player"]) for e in chat_before), "messages_total": len(chat),
              "people_messages": sum(e["player"] in PEOPLE for e in chat_before), "agent_messages": sum(e["player"] in AGENTS for e in chat_before),
              "wait_to_next_agent_message_s": {"median": statistics.median(waits), "p90": sorted(waits)[int(0.9 * len(waits))], "within_60s": sum(w <= 60 for w in waits) / len(waits), "n": len(waits)},
              "people_first_join_h": first_join, "per_quarter_hour": {k: sorted(v.items()) for k, v in per_quarter.items()}}
chat_log = [{"h": H(ts(e["t"])), "clock": clock(H(ts(e["t"]))), "by": who(e["player"]), "text": anon(e["text"])} for e in chat]

# --- The dragon's health, from both agents' fight logs.
LINE = re.compile(r"(?m)^(\d+\.\d) (.*)$")
drops, samples, fight_spans = {}, [], []
for a in AGENTS:
    for p in programs[a]:
        if ts(p["startedAt"]) < SPAWN + timedelta(hours=3.4):
            continue
        s0 = ts(p["startedAt"])
        day = s0.replace(hour=0, minute=0, second=0, microsecond=0)
        sod = (s0 - day).total_seconds()
        t_ = text_of(p)
        if "fightStep" in p["code"] and p.get("endedAt"):
            fight_spans.append((a, s0, ts(p["endedAt"])))
        for m in LINE.finditer(t_):
            c = float(m.group(1))
            t = sod - sod % 1000 + c
            if t < sod - 5:
                t += 1000
            when = day + timedelta(seconds=t)
            line = m.group(2)
            ph = re.search(r"\bD([\d.]+)/ph(-?\d+)", line)
            me = re.search(r"\bhp(\d+)\b", line)
            if ph:
                samples.append({"t": when, "hp": float(ph.group(1)), "phase": int(ph.group(2)), "agent": a})
            dm = re.match(r"dragon hp ([\d.]+)->([\d.]+)", line)
            if dm:
                k = (round(float(dm.group(1)), 3), round(float(dm.group(2)), 3))
                drops.setdefault(k, []).append({"t": when, "agent": a, "seq": p["seq"], "me": int(me.group(1)) if me else None})
        for m in re.finditer(r'"phase":(-?\d+),"hp":([\d.]+)\}', t_):
            samples.append({"t": ts(p.get("endedAt") or p["startedAt"]), "hp": float(m.group(2)), "phase": int(m.group(1)), "agent": a})

# Chain the drops into one path from 200 to 0, skipping the coarse ones that sum finer ones.
by_from = defaultdict(list)
for (a_, b_), v in drops.items():
    by_from[a_].append((b_, min(x["t"] for x in v), v))
chain, hp = [], None
known = sorted(by_from)
hp = max(known)
while True:
    opts = by_from.get(hp)
    if not opts:
        nxt = max((k for k in known if k < hp), default=None)
        if nxt is None:
            break
        chain.append({"gap": True, "from": hp, "to": nxt})
        hp = nxt
        continue
    b_, t, v = max(opts, key=lambda o: o[0])  # the finest step
    chain.append({"gap": False, "from": hp, "to": b_, "t": t, "v": v})
    hp = b_
    if hp <= 0:
        break
FOX, VOID = "FoxglenOpus", "VoidmothOpus"


def fighting(t):
    return [a for a, s, e in fight_spans if s <= t <= e]


attrib, prev = [], None
for x in chain:
    if x["gap"]:
        continue
    d = round(x["from"] - x["to"], 3)
    me = [y["me"] for y in x["v"] if y["me"] is not None]
    if abs(d - 2.25) < 0.005 or abs(d - 5.0) < 0.005:
        src = "FoxglenOpus"
    elif abs(d - 2.75) < 0.005:
        src = "VoidmothOpus"
    elif prev and (x["t"] - prev["t"]).total_seconds() < 0.6 and abs(prev["d"] + d - 2.75) < 0.01 and prev["src"] != "VoidmothOpus":
        src = "VoidmothOpus"
    elif prev and (x["t"] - prev["t"]).total_seconds() < 0.6 and abs(d - 0.5) < 0.005 and abs(prev["d"] - 2.25) < 0.005:
        src = "VoidmothOpus"
    elif d > 5.5 and any(y["me"] is not None and y["me"] < 20 for y in x["v"]) and x["to"] > 0:
        src = "explosion"
    else:
        src = "people"
    row = {"t": x["t"], "clock": clock(H(x["t"])), "from": x["from"], "to": x["to"], "d": d, "src": src, "logged_by": sorted({y["agent"] for y in x["v"]}), "me_hp": me}
    attrib.append(row)
    prev = row
# Explosions: check the line before shows the agent's health higher, and tie them to server messages.
for r in attrib:
    if r["src"] == "explosion":
        near = [e for e in events if e["type"] == "death" and abs((ts(e["t"]) - r["t"]).total_seconds()) < 6]
        r["deaths_within_6s"] = [anon(e["text"]) + " (" + f"{(ts(e['t']) - r['t']).total_seconds():+.1f} s)" for e in near]
gaps = []
for x in chain:
    if x["gap"]:
        # when: between the last sample at x["from"] and the first at x["to"]
        a_ = max((s["t"] for s in samples if abs(s["hp"] - x["from"]) < 0.001), default=None)
        b_ = min((s["t"] for s in samples if abs(s["hp"] - x["to"]) < 0.001), default=None)
        busy = sorted({a for a, s, e in fight_spans if a_ and b_ and s <= b_ and e >= a_})
        gaps.append({"from": x["from"], "to": x["to"], "d": round(x["from"] - x["to"], 3), "after": clock(H(a_)) if a_ else None, "before": clock(H(b_)) if b_ else None,
                     "fight_programs_running": busy, "src": "unattributed" if busy or not a_ else "people (no agent fight program running)"})
# The start of the chain: the dragon had 200 when the last crystal fell.
first = max(by_from)
if first < 200:
    gaps.insert(0, {"from": 200.0, "to": first, "d": round(200 - first, 3), "after": "last crystal", "before": clock(H(min(s["t"] for s in samples if abs(s["hp"] - first) < 0.001))),
                    "fight_programs_running": [], "src": "unattributed"})
damage = Counter()
for r in attrib:
    damage[r["src"]] += r["d"]
for g in gaps:
    damage["people" if g["src"].startswith("people") else "unattributed"] += g["d"]
damage = {k: round(v, 3) for k, v in damage.items()}
perches = []
for r in attrib:
    if r["src"] in ("FoxglenOpus", "VoidmothOpus"):
        if perches and (r["t"] - perches[-1]["last"]).total_seconds() < 20:
            p = perches[-1]
        else:
            p = {"start": r["t"], "last": r["t"], "by": Counter()}
            perches.append(p)
        p["last"] = r["t"]
        p["by"][r["src"]] += r["d"]
perch_rows = [{"clock": clock(H(p["start"])), "by": {k: round(v, 2) for k, v in p["by"].items()}} for p in perches]
# Phase-1 (strafe) stretches, from the samples.
samples.sort(key=lambda s: s["t"])
strafes, cur = [], None
for s in samples:
    if s["phase"] == 1:
        cur = cur or [s["t"], s["t"]]
        cur[1] = s["t"]
    elif cur:
        strafes.append(cur)
        cur = None
strafe_long = [{"from": clock(H(a_)), "to": clock(H(b_)), "min": (b_ - a_).total_seconds() / 60} for a_, b_ in strafes if (b_ - a_).total_seconds() > 240]
dragon = {"attrib": [{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()} for r in attrib], "gaps": gaps, "damage": damage,
          "perches": perch_rows, "strafes_over_4_min": strafe_long,
          "series": [{"h": H(s["t"]), "hp": s["hp"], "phase": s["phase"]} for s in samples if s["t"] <= WIN + timedelta(seconds=3)],
          "first_fight_program": clock(H(min(s for _, s, _ in fight_spans))), "fight_programs": len(fight_spans)}

# --- Crystals (VoidmothOpus's mortar log; the attribution of the last three is from the chat and both agents' notes).
crystals = {"by_voidmoth_bow": 8, "arrows": 21, "by_person": 1, "by_foxglen": 1, "last_crystal": None}
last = None
for e in chat:
    if e["player"] == FOX and "ALL CRYSTALS DOWN" in e["text"]:
        last = ts(e["t"])
crystals["last_crystal"] = clock(H(last)) if last else None
crystals["last_crystal_h"] = H(last) if last else None
crystals["last_crystal_to_win_min"] = (WIN - last).total_seconds() / 60 if last else None

# --- Cost, from each session's last result line.
cost = {}
for a in AGENTS:
    st = jl(REC / f"agent-stream-{a}.jsonl")
    res = [d for d in st if d.get("type") == "result"][-1]
    mu_ = list(res["modelUsage"].values())[0]
    comp = sum(1 for d in st if d.get("type") == "system" and d.get("subtype") == "compact_boundary")
    cost[a] = {"usd": res["total_cost_usd"], "turns": res["num_turns"], "duration_h": res["duration_ms"] / 3.6e6, "api_h": res["duration_api_ms"] / 3.6e6,
               "cache_read": mu_["cacheReadInputTokens"], "cache_write_1h": mu_["cacheCreationEphemeral1hInputTokens"], "cache_write_5m": mu_["cacheCreationEphemeral5mInputTokens"],
               "input": mu_["inputTokens"], "output": mu_["outputTokens"], "thinking": mu_.get("thinkingTokens"), "compactions": comp}
cost["total_usd"] = sum(cost[a]["usd"] for a in AGENTS)
efforts = Counter()
for f in (REC / "transcripts").glob("*.jsonl"):
    for d in jl(f):
        if d.get("type") == "api-request" and d.get("timestamp") and ts(d["timestamp"]) <= WIN:
            efforts[str((d.get("params") or {}).get("output_config", {}).get("effort"))] += 1
cost["effort_requests"] = efforts.most_common()
# Compactions and Stop-hook lines, timed from the transcripts (the stream has no timestamps).
SESS = {v["sessionId"]: a for a, v in META["agents"].items()}
compactions, hook_lines = [], []
for f in (REC / "transcripts").glob("*.jsonl"):
    a = SESS.get(f.stem)
    for d in jl(f):
        if d.get("subtype") == "compact_boundary" and d.get("timestamp"):
            compactions.append({"agent": a, "h": H(ts(d["timestamp"])), "clock": clock(H(ts(d["timestamp"])))})
        msg = json.dumps(d.get("message", ""))
        if d.get("type") == "user" and "Stop hook feedback" in msg and "being continued from a previous conversation" not in msg and d.get("timestamp"):
            hook_lines.append({"agent": a, "h": H(ts(d["timestamp"])), "clock": clock(H(ts(d["timestamp"])))})
compactions.sort(key=lambda c: c["h"])

# People's time on the server, from joins and leaves, cut at the win.
presence = {}
for p in PEOPLE:
    spans, on = [], None
    for e in sorted((e for e in joins if e["player"] == p), key=lambda e: e["t"]):
        if e["type"] == "player_join" and on is None:
            on = ts(e["t"])
        elif e["type"] == "player_leave" and on is not None:
            spans.append((on, ts(e["t"])))
            on = None
    if on is not None:
        spans.append((on, WIN))
    spans = [(a_, min(b_, WIN)) for a_, b_ in spans if a_ <= WIN]
    presence[who(p)] = {"spans": [[H(a_), H(b_)] for a_, b_ in spans], "hours": sum((b_ - a_).total_seconds() for a_, b_ in spans) / 3600, "joins": len(spans)}

# Agent hours in each dimension, from the status lines.
dim_hours = {}
for a in AGENTS:
    seq = dims[a] + [{"h": clock_["official_h"], "dim": None}]
    acc = Counter()
    for u, v in zip(seq, seq[1:]):
        acc[u["dim"]] += min(v["h"], clock_["official_h"]) - u["h"]
    acc["overworld"] += seq[0]["h"]  # spawn to the first status line
    dim_hours[a] = {k: round(v, 3) for k, v in acc.items()}

# --- After the win: the exit portal jump.
after = {}
for a in AGENTS:
    jumped = next((p for p in programs[a] if ts(p["startedAt"]) > WIN and re.search(r"dim overworld", text_of(p))), None)
    after[a] = {"programs": prog_stats[a]["after_win"], "overworld_program_end_s": (ts(jumped["endedAt"]) - WIN).total_seconds() if jumped else None}
go = next((e for e in chat if e["player"] in PEOPLE and e["text"].strip().upper().startswith("GO") and ts(e["t"]) > WIN), None)
after["go_s_after_win"] = (ts(go["t"]) - WIN).total_seconds() if go else None
after["deaths_after_win"] = sum(e["type"] == "death" and ts(e["t"]) > WIN for e in events)

# --- Server log and camera checks.
log = (REC / "server.log").read_text(errors="replace")
frames = sorted(jl(RUN / "server" / "camera" / "frames.jsonl"), key=lambda f: f["t"])
ft = [ts(f["t"]) for f in frames if ts(f["t"]) <= WIN]
checks = {"win_line": anon(next((l for l in log.splitlines() if "Free the End" in l), "")), "rcon_clients": len(re.findall(r"Thread RCON Client /127\.0\.0\.1 started", log)),
          "rcon_client_times": re.findall(r"\[(\d\d:\d\d:\d\d)\] \[RCON Listener #1/INFO\]: Thread RCON Client", log),
          "issued_commands": len(re.findall(r"issued server command", log)), "cant_keep_up": len(re.findall("Can't keep up", log)),
          "ops": json.loads((RUN / "server" / "ops.json").read_text()), "pause_events": sum(e["type"] in ("pause", "resume") for e in events),
          "bot_connects": Counter(e["player"] for e in events if e["type"] == "bot_connected"), "server_ready_events": sum(e["type"] == "server_ready" for e in events),
          "frames_to_win": len(ft), "frame_median_gap_s": statistics.median((ft[i + 1] - ft[i]).total_seconds() for i in range(len(ft) - 1)),
          "frame_max_gap_s": max((ft[i + 1] - ft[i]).total_seconds() for i in range(len(ft) - 1)), "frames_by_player": Counter(f.get("player") for f in frames if ts(f["t"]) <= WIN)}
slash = {a: sum(bool(re.search(r"bot\.chat\(\s*['\"`]/", p["code"])) for p in programs[a]) for a in AGENTS}
checks["slash_commands_in_programs"] = slash
# Bed calls outside the Overworld: the library's bed functions (and the bot.sleep inside L.setSpawn) are
# defined in every library reload, so count calls only in programs that do not reload the library.
BEDCALL = re.compile(r"\bL\.(placeBed|bedCamp|setSpawn)\(|\bbot\.sleep\(")
LIBDEF = re.compile(r"L\.(placeBed|bedCamp|setSpawn)\s*=\s*async")
checks["bed_calls_outside_overworld"] = {}
checks["library_reloads_outside_overworld"] = {}
for a in AGENTS:
    n = nl = 0
    for p in programs[a]:
        past = [s for s in dims[a] if s["h"] <= H(ts(p["startedAt"]))]
        away = past and past[-1]["dim"] != "overworld"
        if LIBDEF.search(p["code"]):
            nl += bool(away)
            continue
        calls = [l for l in p["code"].splitlines() if BEDCALL.search(l) and not l.strip().startswith("//")]
        n += bool(calls and away)
    checks["bed_calls_outside_overworld"][a] = n
    checks["library_reloads_outside_overworld"][a] = nl

# --- The earlier runs, from the run 4 paper's data, on the official clock.
R4 = json.loads((PROJECT / "preprint-run4" / "data" / "run4.json").read_text())
earlier = {k: {"official_h": v["official_h"], "from_first_program_h": v["from_first_program_h"], "deaths": len(v["deaths"]), "programs": v["programs"]["before_end"],
               "milestones": v["milestones"], "won": v["won"], "spawn_to_first_program_s": v["spawn_to_first_program_s"]} for k, v in R4["runs"].items()}
# The last crystal, as the run 4 paper dates it: run 4 from its program output, run 2 from its paper moved to the official clock.
earlier["run4"]["ten_crystals_h"] = R4["end"]["last_crystal_h"]
earlier["run2"]["ten_crystals_h"] = 8 + 10 / 60 + R4["runs"]["run2"]["spawn_to_first_program_s"] / 3600
earlier["gemini_team"] = R4["team"]

out = {"clock": clock_, "milestones": milestones, "first_adv": first_adv, "advancements": adv, "dims": dims, "entries": entries, "deaths": deaths, "death_stats": death_stats,
       "programs": prog_stats, "chat": chat_stats, "chat_log": chat_log, "dragon": dragon, "crystals": crystals, "cost": cost, "after_win": after, "checks": checks, "earlier": earlier,
       "people": list(LABEL.values()), "compactions": compactions, "hook_lines": hook_lines, "presence": presence, "dim_hours": dim_hours}
(PRE / "data").mkdir(exist_ok=True)
(PRE / "data" / "team.json").write_text(json.dumps(out, indent=1, default=str))

P = lambda name, v: print(name + ":", json.dumps(v, default=str))
print("official", clock(clock_["official_h"]), "from first program", clock(clock_["from_first_program_h"]), "spawn->first program s", round(clock_["spawn_to_first_program_s"], 1), clock_["first_program_s"])
for k, v in milestones.items():
    print("  ", k, v["clock"], v["by"])
P("first_adv agents", {a: {k: clock(h) for k, h in first_adv.get(a, {}).items()} for a in AGENTS})
P("dims", {a: [(clock(s["h"]), s["dim"]) for s in dims[a]] for a in AGENTS})
P("entries", entries)
P("death_stats", death_stats)
for d in deaths:
    if d["agent"]:
        print("  ", d["clock"], d["player"], d["cause"], d.get("dim"), d.get("pos"), "|", d["text"])
P("programs", {a: {k: v for k, v in prog_stats[a].items() if k != "per_quarter_hour"} for a in AGENTS})
P("programs both", prog_stats["both"])
P("chat", {k: v for k, v in chat_stats.items() if k != "per_quarter_hour"})
P("damage", damage)
print("sum", round(sum(damage.values()), 3))
for r in attrib:
    print("  ", r["clock"], f"{r['from']:.3f}->{r['to']:.3f} d={r['d']:.3f}", r["src"], r["logged_by"], r["me_hp"], r.get("deaths_within_6s", ""))
P("gaps", gaps)
P("perches", perch_rows)
P("strafes", strafe_long)
P("crystals", crystals)
P("cost", cost)
P("after", after)
P("checks", checks)
P("compactions", compactions)
P("hook_lines", hook_lines)
P("presence", {k: {"hours": v["hours"], "joins": v["joins"]} for k, v in presence.items()})
P("dim_hours", dim_hours)
P("first_adv people", {p: {k: clock(h) for k, h in first_adv.get(p, {}).items()} for p in LABEL.values()})
