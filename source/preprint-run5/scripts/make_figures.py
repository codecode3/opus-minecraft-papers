#!/usr/bin/env python3
"""Draw the run 5 preprint's figures from preprint-run5/data/run5.json.

    <python with matplotlib> preprint-run5/scripts/make_figures.py   -> preprint-run5/figures/fig*.pdf

Hours are on the official clock, from the player's first spawn. The estimates in figure 1 are typed
in here from the plan's own text at each commit (git log of run-5-plan.md).
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

PRE = Path(__file__).resolve().parent.parent
FIG = PRE / "figures"
(FIG / "preview").mkdir(parents=True, exist_ok=True)
D = json.loads((PRE / "data" / "run5.json").read_text())
WIN = D["win_s"] / 3600

plt.rcParams.update({
    "font.family": "Avenir Next", "font.size": 8, "pdf.fonttype": 42, "axes.linewidth": 0.6,
    "axes.edgecolor": "#c9ccd1", "xtick.color": "#5f6368", "ytick.color": "#5f6368",
    "axes.labelcolor": "#5f6368", "text.color": "#1f1f1f",
})
TEAL, PURPLE, GREY, RED, INK = "#0f8f7c", "#5b3fd6", "#9aa0a6", "#c5221f", "#1f1f1f"
DIM = {"overworld": "#cfe8c8", "the_nether": "#f3c9c0", "the_end": "#e9e3b4"}
DIMNAME = {"overworld": "Overworld", "the_nether": "Nether", "the_end": "The End"}
hm = lambda h, _=None: f"{int(h)}:{int(round((h % 1) * 60)):02d}"


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / "preview" / f"{name}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def clean(ax, keep=("bottom", "left")):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)


# Figure 1: the estimate through the planning conversation.
# (label, headline %, headline range, what the headline measured, no-preparation %, its range)
EDITS = [
    ("Before the\nmodel", 25, None, "a judgement", 25, None),
    ("06:44\nodds model", 37.5, (30, 51), "one attempt", 37.5, (30, 51)),
    ("18:07\npreparation\nplayer", 50, (41, 71), "one attempt, after a\npreparation player", 43.75, (34, 57)),
    ("18:16\ntwo attempts", 75, (65, 92), "at least one\nof two attempts", 43.75, (34, 57)),
    ("18:22\ngate, fast mode", 75, (71, 86), "one attempt, with an\nunmeasured fast mode", 43.75, (33, 58)),
    ("18:37\nrehearsals\nwith fixes", 75, (74, 78), "one attempt, after\na passed rehearsal", 50, (50, 57)),
    ("19:02\nfrozen for\nthe run", 50.3, (31.9, 68.7), "", 50.3, (31.9, 68.7)),
]
ASKS = [(0.5, '"1.5 in 4"'), (1.5, '"2 in 4"'), (2.5, '"3 in 4"'), (3.5, '"do not cheat\non the figure"'), (4.5, '"Fast mode is\nnot allowed"'),
        (5.5, '"no preparation\nplayer"')]
fig, ax = plt.subplots(figsize=(6.9, 3.5))
xs = list(range(len(EDITS)))
ax.axhline(75, color="#e8eaed", lw=0.8)
ax.axhline(50, color="#e8eaed", lw=0.8)
ax.axhline(37.5, color="#e8eaed", lw=0.8)
for x, (_, h, hr, what, n, nr) in zip(xs, EDITS):
    if nr:
        ax.plot([x + 0.08, x + 0.08], nr, color=TEAL, lw=3.5, alpha=0.3, solid_capstyle="butt")
    if hr and x < 6:
        ax.plot([x - 0.08, x - 0.08], hr, color=PURPLE, lw=3.5, alpha=0.3, solid_capstyle="butt")
ax.plot([x - 0.08 for x in xs[:6]], [e[1] for e in EDITS[:6]], color=PURPLE, lw=1.3, marker="o", ms=4.5, label="The figure the plan quoted first")
ax.plot([x + 0.08 for x in xs], [e[4] for e in EDITS], color=TEAL, lw=1.3, marker="o", ms=4.5,
        label="One attempt with no preparation player and no rehearsal (what was run)")
for x, (_, h, hr, what, n, nr) in zip(xs, EDITS):
    if 2 <= x <= 5:
        ax.text(x - 0.08, (hr[1] if hr else h) + 2.5, what, ha="center", va="bottom", fontsize=6, color=PURPLE, linespacing=1.15)
for x, t in ASKS:
    ax.axvline(x, color="#dadce0", lw=0.7, ls=":")
    ax.text(x, 4, t, ha="center", va="bottom", fontsize=6.3, color=INK, style="italic", linespacing=1.15,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#dadce0", lw=0.5))
ax.text(6.08, 72, "s.d. 18 points", ha="center", fontsize=6, color=TEAL)
ax.set_xticks(xs)
ax.set_xticklabels([e[0] for e in EDITS], fontsize=6.8, linespacing=1.15)
ax.set_yticks([0, 25, 37.5, 50, 75, 100])
ax.set_yticklabels(["0", "25%\n1 in 4", "1.5 in 4", "50%\n2 in 4", "75%\n3 in 4", "100%"], fontsize=6.8)
ax.set_ylim(0, 108)
ax.set_xlim(-0.5, 6.5)
ax.set_ylabel("Estimated chance of a win under 5:00")
ax.set_xlabel("Edits of the plan on 11 November 2026 (Central time); the owner's words between them")
ax.legend(loc="upper left", frameon=False, fontsize=7, bbox_to_anchor=(0.0, 1.12), ncol=1)
clean(ax)
save(fig, "fig1_estimate")

# Figure 2: the steps, against the earlier runs.
E = D["earlier"]
ROWS = [("run5", "Run 5: Fable 5.2, low", TEAL), ("bench_fable", "Benchmark: Fable 5.2, low (stopped)", "#7fc8bb"),
        ("bench_opus", "Benchmark: Opus 5.5, xhigh (stopped)", "#b3a4ee"), ("run4", "Run 4: Opus 5.5, xhigh", PURPLE)]
mine = {m["key"]: m["clock"] for m in D["milestones"]}
get = lambda who, k: (mine if who == "run5" else E[who]["milestones"]).get(k)
KEYS = [("nether_portal", "Nether portal"), ("fortress", "Nether fortress"), ("blaze_rods", "Blaze rods"), ("ender_pearls", "Ender pearls"),
        ("eyes_of_ender", "Eyes of Ender"), ("stronghold", "Stronghold"), ("the_end", "The End"), ("dragon", "Ender Dragon")]
fig, ax = plt.subplots(figsize=(6.9, 2.45))
for i, (k, lab) in enumerate(KEYS):
    y = len(KEYS) - 1 - i
    vals = [get(w, k) for w, _, _ in ROWS if get(w, k) is not None]
    ax.plot([min(vals) / 3600, max(vals) / 3600], [y, y], color="#dadce0", lw=1.2, zorder=1)
    for w, _, c in reversed(ROWS):
        v = get(w, k)
        if v is not None:
            ax.scatter(v / 3600, y, s=46 if w == "run5" else 26, color=c, zorder=4 if w == "run5" else 3, edgecolor="white", linewidth=0.7)
    ax.text(mine[k] / 3600, y + 0.33, hm(mine[k] / 3600), ha="center", fontsize=6.3, color=TEAL)
ax.axvline(5, color=RED, lw=0.8, ls="--")
ax.text(5.04, len(KEYS) - 1.0, "goal: 5:00", color=RED, fontsize=7)
ax.set_yticks(range(len(KEYS)))
ax.set_yticklabels([lab for _, lab in reversed(KEYS)])
ax.set_xlim(0, 7.1)
ax.set_ylim(-0.6, len(KEYS) - 0.3)
ax.xaxis.set_major_formatter(hm)
ax.set_xlabel("Official clock (h:mm after first spawn)")
ax.grid(axis="x", color="#eef0f2", lw=0.6)
ax.set_axisbelow(True)
clean(ax, keep=("bottom",))
ax.tick_params(axis="y", length=0)
ax.legend(handles=[Line2D([], [], marker="o", ls="", color=c, label=l) for _, l, c in ROWS], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=7)
save(fig, "fig2_steps")

# Figure 3: the run, with the size of the model's context.
fig, axes = plt.subplots(3, 1, figsize=(6.9, 4.5), sharex=True, gridspec_kw={"height_ratios": [1.15, 0.45, 2.0], "hspace": 0.13})
ax = axes[0]
spans = D["dims"] + [[D["win_s"], None]]
for (a, d), (b, _) in zip(spans, spans[1:]):
    ax.axvspan(a / 3600, b / 3600, ymin=0, ymax=0.55, color=DIM[d], lw=0)
for s in D["stages"]:
    for a, b in s.get("recover", []):
        ax.plot([a / 3600, b / 3600], [0.62, 0.62], color=INK, lw=2.2, solid_capstyle="butt")
    for a, b in s.get("food", []):
        ax.plot([a / 3600, b / 3600], [0.62, 0.62], color="#e8710a", lw=2.2, solid_capstyle="butt")
    ax.plot([s["b"] / 3600] * 2, [0, 0.74], color="#5f6368", lw=0.6)
names = {"to_nether": "To the\nNether", "fort_rods": "7 rods", "pearls": "13 pearls", "home_eyes": "Eyes", "crossing": "Crossing, base, End entry",
         "crystals": "Crystals", "dragon": "Dragon"}
for s in D["stages"]:
    ax.text((s["a"] + s["b"]) / 7200, 0.80 if s["key"] not in ("home_eyes", "crystals") else 0.97, names[s["key"]], ha="center", va="bottom", fontsize=6.4,
            color="#5f6368", linespacing=1.1)
for d in D["deaths"]:
    ax.scatter(d["clock"] / 3600, 0.275, marker="x", s=30, color=INK, lw=1.3, zorder=3)
ax.set_ylim(0, 1.25)
ax.set_yticks([])
clean(ax, keep=())
ax.legend(handles=[Patch(color=DIM[k], label=DIMNAME[k]) for k in DIM] + [Line2D([], [], marker="x", ls="", color=INK, label="death"),
                   Line2D([], [], color=INK, lw=2.2, label="recovering a kit"), Line2D([], [], color="#e8710a", lw=2.2, label="unforeseen food work")],
          loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=6, frameon=False, fontsize=6.6, handlelength=1.4, columnspacing=1.2)
ax = axes[1]
for a, b in D["programs"]["spans"]:
    ax.axvspan(a / 3600, b / 3600, color=TEAL, lw=0, alpha=0.85)
ax.set_yticks([])
ax.set_ylabel("program\nrunning", rotation=0, ha="right", va="center", fontsize=6.8)
clean(ax, keep=())
ax = axes[2]
ctx = [(c / 3600, t / 1000) for c, t in D["context"] if c <= D["win_s"]]
ax.plot(*zip(*ctx), color=PURPLE, lw=1.1, drawstyle="steps-post")
ax.fill_between([c for c, _ in ctx], [t for _, t in ctx], step="post", color=PURPLE, alpha=0.08, lw=0)
ax.axhline(383, color=GREY, lw=0.7, ls="--")
ax.text(0.03, 392, "compaction window set for the run: 383,000 tokens", fontsize=6.5, color="#5f6368")
for c in D["compactions"]:
    ax.axvline(c["clock"] / 3600, color=RED, lw=0.8)
    ax.text(c["clock"] / 3600 + 0.04, 250, f"compaction at {hm(c['clock'] / 3600)}\n{c['pre'] / 1000:.0f}k to {c['post'] / 1000:.0f}k tokens", fontsize=6.5, color=RED, va="top")
ax.axvline(WIN, color=TEAL, lw=1.0)
ax.text(WIN - 0.04, 60, f"win\n{D['win_clock']}", ha="right", fontsize=7, color=TEAL)
ax.set_ylim(0, 430)
ax.set_xlim(0, 4.75)
ax.set_ylabel("Tokens in the model's context\n(thousands, each request)")
ax.set_xlabel("Official clock (h:mm after first spawn)")
ax.xaxis.set_major_formatter(hm)
ax.grid(color="#eef0f2", lw=0.6)
ax.set_axisbelow(True)
clean(ax)
save(fig, "fig3_run")

# Figure 4: the prediction frozen before the run, and what the run showed.
fig, (ax, bx) = plt.subplots(1, 2, figsize=(6.9, 2.9), gridspec_kw={"width_ratios": [1.55, 1], "wspace": 0.28})
st = D["stages"]
for i, s in enumerate(st):
    y = len(st) - 1 - i
    p = s["prior"]
    ax.plot([p["5"], p["95"]], [y, y], color="#c9ccd1", lw=6, solid_capstyle="butt", zorder=1)
    ax.plot([p["50"]] * 2, [y - 0.24, y + 0.24], color="#5f6368", lw=1.2, zorder=2)
    obs = s["work_less_food_min"]
    out = obs < p["5"] or obs > p["95"]
    ax.scatter(obs, y, s=38, color=RED if out else TEAL, zorder=4, edgecolor="white", linewidth=0.7)
    ax.text(obs, y + 0.36, f"{obs:.0f}", ha="center", fontsize=6.5, color=RED if out else TEAL)
    if s["food_min"]:
        ax.scatter(s["work_min"], y, s=30, facecolor="white", edgecolor="#e8710a", linewidth=1.1, zorder=3)
        ax.text(s["work_min"], y + 0.36, f"{s['work_min']:.0f} with the food work", ha="left", fontsize=6.2, color="#e8710a")
ax.set_yticks(range(len(st)))
ax.set_yticklabels([s["label"] for s in reversed(st)], fontsize=7)
ax.set_xlim(0, 92)
ax.set_ylim(-0.6, len(st) - 0.35)
ax.set_xlabel("Minutes of work in the stage, without death recovery")
ax.grid(axis="x", color="#eef0f2", lw=0.6)
ax.set_axisbelow(True)
clean(ax, keep=("bottom",))
ax.tick_params(axis="y", length=0)
ax.legend(handles=[Line2D([], [], color="#c9ccd1", lw=6, label="predicted, 5th to 95th percentile"), Line2D([], [], color="#5f6368", lw=1.2, label="predicted median"),
                   Line2D([], [], marker="o", ls="", color=TEAL, label="run 5"), Line2D([], [], marker="o", ls="", color=RED, label="run 5, outside the range")],
          loc="lower center", frameon=False, fontsize=6.3, bbox_to_anchor=(0.4, 1.0), ncol=2)


def beta(a, b):
    lg = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    xs = [i / 400 for i in range(1, 400)]
    return xs, [math.exp(lg + (a - 1) * math.log(x) + (b - 1) * math.log(1 - x)) for x in xs]


POST = json.loads((PRE / "data" / "posterior.json").read_text())
x, y = beta(POST["prior"]["beta_a"], POST["prior"]["beta_b"])
bx.plot([100 * v for v in x], y, color=GREY, lw=1.3)
bx.fill_between([100 * v for v in x], y, color=GREY, alpha=0.12, lw=0)
x, y2 = beta(POST["posterior"]["beta_a"], POST["posterior"]["beta_b"])
bx.plot([100 * v for v in x], y2, color=TEAL, lw=1.3)
bx.fill_between([100 * v for v in x], y2, color=TEAL, alpha=0.12, lw=0)
bx.text(22, max(y) + 0.35, f"before the run\n{100 * POST['prior']['p_win_mu']:.0f}%, s.d. {100 * POST['prior']['p_win_sigma']:.0f}", fontsize=6.8, color="#5f6368", ha="center")
bx.text(56, max(y2) * 0.86, f"after it\n{100 * POST['posterior']['p_win_mu']:.0f}%, s.d. {100 * POST['posterior']['p_win_sigma']:.0f}", fontsize=6.8, color=TEAL, ha="right")
bx.set_yticks([])
bx.set_xlim(0, 100)
bx.set_ylim(0, max(y2) * 1.1)
bx.set_xlabel("Chance that a run of this plan wins under 5:00 (%)")
clean(bx, keep=("bottom",))
save(fig, "fig4_prediction")
# Figure 5: the subscription's 5-hour usage window through the run.
fig, ax = plt.subplots(figsize=(6.9, 2.5))
wins = {}
for x in D["limits"]:
    if x["five_hour"] is not None and x["clock"] <= D["win_s"] + 150:
        wins.setdefault(x["five_hour_resets_s"], []).append((x["clock"] / 3600, 100 * x["five_hour"]))
for i, (reset, pts) in enumerate(sorted(wins.items())):
    ax.plot(*zip(*pts), color=PURPLE, lw=1.4, drawstyle="steps-post", label="5-hour window" if i == 0 else None)
    ax.fill_between([p[0] for p in pts], [p[1] for p in pts], step="post", color=PURPLE, alpha=0.08, lw=0)
first = sorted(wins.items())[0]
peak = max(first[1], key=lambda p: p[1])
ax.axvline(first[0] / 3600, color=GREY, lw=0.8, ls=":")
ax.text(first[0] / 3600 + 0.04, 64, f"window resets\nat {hm(first[0] / 3600)}", fontsize=6.8, color="#5f6368", va="top")
ax.annotate(f"{peak[1]:.0f}% at {hm(peak[0])}", xy=peak, xytext=(peak[0] - 0.75, peak[1] + 7), fontsize=7, color=PURPLE,
            arrowprops=dict(arrowstyle="-", color=PURPLE, lw=0.6))
wk = [(x["clock"] / 3600, 100 * x["seven_day"]) for x in D["limits"] if x["seven_day"] is not None and x["clock"] <= D["win_s"] + 150]
ax.plot(*zip(*wk), color=TEAL, lw=1.1, drawstyle="steps-post", label="7-day window")
ax.axhline(100, color=RED, lw=0.8, ls="--")
ax.text(0.04, 103, "limit: requests refused", color=RED, fontsize=6.8)
ax.axvline(WIN, color=TEAL, lw=1.0)
ax.text(WIN - 0.04, 88, f"win\n{D['win_clock']}", ha="right", fontsize=7, color=TEAL, va="top")
ax.set_ylim(0, 115)
ax.set_xlim(0, 4.75)
ax.set_ylabel("Share of the usage window (%)")
ax.set_xlabel("Official clock (h:mm after first spawn)")
ax.xaxis.set_major_formatter(hm)
ax.grid(color="#eef0f2", lw=0.6)
ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=7, bbox_to_anchor=(0.0, 0.9))
clean(ax)
save(fig, "fig5_usage")
print("figures written")
