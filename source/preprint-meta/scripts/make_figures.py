#!/usr/bin/env python3
"""Draw the figures of the planning-loop paper.

    <python with matplotlib> preprint-meta/scripts/make_figures.py   -> preprint-meta/figures/fig*.pdf

fig1_loop       the loop, drawn by hand from the paper's Table 2
fig2_estimate   the estimate at each edit of the plan; the numbers are typed in from the plan's own
                text at each commit (git log of run-5-plan.md), as in preprint-run5
fig3_forecast   the frozen forecast, a win-only update and the full update (data/posterior.json)
fig4_context    the planning session's context through the day (data/session.json)
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PRE = Path(__file__).resolve().parent.parent
FIG = PRE / "figures"
(FIG / "preview").mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "Avenir Next", "font.size": 8, "pdf.fonttype": 42, "axes.linewidth": 0.6,
    "axes.edgecolor": "#c9ccd1", "xtick.color": "#5f6368", "ytick.color": "#5f6368",
    "axes.labelcolor": "#5f6368", "text.color": "#1f1f1f",
})
TEAL, PURPLE, GREY, RED, INK, ORANGE = "#0f8f7c", "#5b3fd6", "#9aa0a6", "#c5221f", "#1f1f1f", "#e8710a"


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / "preview" / f"{name}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def clean(ax, keep=("bottom", "left")):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)


hhmm = lambda h, _=None: f"{int(h):02d}:{int(round((h % 1) * 60)) % 60:02d}"

# ---------------------------------------------------------------- Figure 1: the loop
fig, ax = plt.subplots(figsize=(6.9, 3.9))
ax.set_xlim(-1, 101)
ax.set_ylim(-4, 60)
ax.axis("off")


def box(x, y, w, h, title, body, ec, fc="white", tc=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", fc=fc, ec=ec, lw=1.0))
    ax.text(x + w / 2, y + h - 2.1, title, ha="center", va="top", fontsize=6.6, weight="bold", color=tc)
    ax.text(x + w / 2, y + h - 5.6, body, ha="center", va="top", fontsize=6.1, color="#3c4043", linespacing=1.25)


def arrow(a, b, color=INK, ls="-", rad=0.0, lw=1.0):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls=ls, shrinkA=0, shrinkB=0,
                                                    connectionstyle=f"arc3,rad={rad}", mutation_scale=9))


W, H, Y = 18.0, 15.5, 13.5
XS = [0.0, 20.5, 41.0, 61.5, 82.0]
STEPS = [
    ("1  Fit a model", "a simulation of\nthe run, fitted to\nthree earlier players", GREY),
    ("2  Plan in the model", "edit the plan,\nsimulate 40,000 runs,\nread the estimate", PURPLE),
    ("3  Freeze a forecast", "50% under 5:00,\ns.d. 18 points,\nwritten to a file", TEAL),
    ("4  Act once", "run 5, on a new\nrandom world: won\nat 4:39:54, 4 deaths", ORANGE),
    ("5  Update", "stage times and\ndeaths scored:\n73%, s.d. 7 points", TEAL),
]
for x, (t, b, c) in zip(XS, STEPS):
    box(x, Y, W, H, t, b, c)
for x0, x1 in zip(XS, XS[1:]):
    arrow((x0 + W + 0.5, Y + H / 2), (x1 - 0.5, Y + H / 2))
# The search inside step 2.
arrow((XS[1] + W - 3.5, Y - 0.5), (XS[1] + 3.5, Y - 0.5), color=PURPLE, rad=-0.9)
ax.text(XS[1] + W / 2, Y - 7.6, "repeat until the\nestimate meets the target", ha="center", va="top", fontsize=6.3, color=PURPLE, linespacing=1.2)
# The return path.
ax.plot([XS[4] + W / 2, XS[4] + W / 2, XS[0] + W / 2], [Y - 0.5, -2.0, -2.0], color=GREY, lw=1.0, ls=(0, (3, 2)))
arrow((XS[0] + W / 2, -2.0), (XS[0] + W / 2, Y - 0.6), color=GREY)
ax.text(71, -1.2, "6  Replan: refit the model with run 5 and price the next plan (not done yet)", ha="center", va="bottom", fontsize=6.5, color="#5f6368")
# The human.
PX, PY, PW, PH = 20.5, 46.5, 59.0, 12.0
ax.add_patch(FancyBboxPatch((PX, PY), PW, PH, boxstyle="round,pad=0.25,rounding_size=1.2", fc="#f3f0fd", ec=PURPLE, lw=1.0))
ax.text(PX + PW / 2, PY + PH - 1.8, "The human", ha="center", va="top", fontsize=7.6, weight="bold", color=PURPLE)
ax.text(PX + PW / 2, PY + PH - 5.6, "sets the goal, the target for the estimate, what is not allowed and when to act;\nnever edits the plan",
        ha="center", va="top", fontsize=6.0, color="#3c4043", linespacing=1.25)
for x, lab in ((XS[1] + W / 2, "target: 1.5, then 2,\nthen 3 in 4;\n\"do not cheat\non the figure\""),
               (XS[2] + W / 2, "\"mu and sigma ...\nwith no rehersal\";\n\"save all this\""),
               (XS[3] + W / 2, "\"begin the run\"")):
    arrow((x, PY - 0.5), (x, Y + H + 0.6), color=PURPLE)
    ax.text(x + 1.0, (PY + Y + H) / 2, lab, ha="left", va="center", fontsize=6.0, color=PURPLE, style="italic", linespacing=1.15)
save(fig, "fig1_loop")

# ---------------------------------------------------------------- Figure 2: the estimate at each edit
# (label, the figure quoted first %, its range, what it measured, the fixed case %, its range)
EDITS = [
    ("Before the\nmodel", 25, None, "", 25, None),
    ("06:44\nodds model", 37.5, (30, 51), "", 37.5, (30, 51)),
    ("18:07\npreparation\nplayer", 50, (41, 71), "after a\npreparation player", 43.75, (34, 57)),
    ("18:16\ntwo attempts", 75, (65, 92), "at least one\nof two attempts", 43.75, (34, 57)),
    ("18:22\ngate, fast mode", 75, (71, 86), "with an unmeasured\nfast mode", 43.75, (33, 58)),
    ("18:37\nrehearsals\nwith fixes", 75, (74, 78), "after a passed\nrehearsal", 50, (50, 57)),
    ("19:02\nfrozen", 50.3, (31.9, 68.7), "", 50.3, (31.9, 68.7)),
]
TARGETS = [(0.5, 1.5, 37.5), (1.5, 2.5, 50), (2.5, 5.5, 75)]  # (from edit, to edit, the target the human had set)
fig, ax = plt.subplots(figsize=(6.9, 3.3))
xs = list(range(len(EDITS)))
for a, b, t in TARGETS:
    ax.plot([a, b], [t, t], color=RED, lw=1.1, ls=(0, (4, 2)))
ax.text(4.0, 62.5, "the target the human had set", color=RED, fontsize=6.5, ha="center")
ax.annotate("", xy=(3.6, 74.2), xytext=(3.9, 65.5), arrowprops=dict(arrowstyle="-", color=RED, lw=0.5))
for x, (_, h, hr, what, n, nr) in zip(xs, EDITS):
    if nr:
        ax.plot([x + 0.09] * 2, nr, color=TEAL, lw=3.5, alpha=0.3, solid_capstyle="butt")
    if hr and x < 6:
        ax.plot([x - 0.09] * 2, hr, color=PURPLE, lw=3.5, alpha=0.3, solid_capstyle="butt")
ax.plot([x - 0.09 for x in xs[:6]], [e[1] for e in EDITS[:6]], color=PURPLE, lw=1.3, marker="o", ms=4.5, label="The figure the plan quoted first (the estimand changed from edit to edit)")
ax.plot([x + 0.09 for x in xs], [e[4] for e in EDITS], color=TEAL, lw=1.3, marker="o", ms=4.5,
        label="A fixed estimand: one attempt, no preparation player, no rehearsal (what was run)")
for x, (_, h, hr, what, n, nr) in zip(xs, EDITS):
    if what:
        ax.text(x - 0.09, (hr[1] if hr else h) + 2.5, what, ha="center", va="bottom", fontsize=6, color=PURPLE, linespacing=1.15)
ax.text(6.09, 71.5, "s.d. 18 points", ha="center", fontsize=6, color=TEAL)
ax.set_xticks(xs)
ax.set_xticklabels([e[0] for e in EDITS], fontsize=6.8, linespacing=1.15)
ax.set_yticks([0, 25, 37.5, 50, 75, 100])
ax.set_yticklabels(["0", "25%\n1 in 4", "1.5 in 4", "50%\n2 in 4", "75%\n3 in 4", "100%"], fontsize=6.8)
ax.set_ylim(0, 108)
ax.set_xlim(-0.5, 6.5)
ax.set_ylabel("Estimated chance of a win under 5:00")
ax.set_xlabel("Edits of the plan on 11 November 2026 (Central time)")
ax.legend(loc="upper left", frameon=False, fontsize=6.8, bbox_to_anchor=(0.0, 1.17), ncol=1)
clean(ax)
save(fig, "fig2_estimate")

# ---------------------------------------------------------------- Figure 3: forecast, win-only update, full update
P = json.loads((PRE / "data" / "posterior.json").read_text())


def beta_pdf(x, a, b):
    return math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + (a - 1) * math.log(x) + (b - 1) * math.log(1 - x))


a0, b0 = P["prior"]["beta_a"], P["prior"]["beta_b"]
a1, b1 = P["posterior"]["beta_a"], P["posterior"]["beta_b"]
CURVES = [
    (a0, b0, GREY, "-", "Frozen before the run"),
    (a0 + 1, b0, PURPLE, (0, (4, 2)), "Updated on the win alone"),
    (a1, b1, TEAL, "-", "Updated on stage times, deaths and the surprise"),
]
grid = [i / 500 for i in range(1, 500)]
fig, ax = plt.subplots(figsize=(6.9, 2.5))
for a, b, c, ls, lab in CURVES:
    ys = [beta_pdf(x, a, b) for x in grid]
    mean = a / (a + b)
    ax.plot([100 * x for x in grid], ys, color=c, lw=1.5, ls=ls, label=f"{lab}: {100 * mean:.0f}%")
    ax.plot([100 * mean] * 2, [0, beta_pdf(mean, a, b)], color=c, lw=0.7, ls=":")
ax.set_xlim(0, 100)
ax.set_ylim(0, None)
ax.set_yticks([])
ax.set_xticks(range(0, 101, 10))
ax.set_xticklabels([f"{v}%" for v in range(0, 101, 10)])
ax.set_xlabel("Chance that one run of this plan frees the End in under 5:00")
ax.set_ylabel("Belief (density)")
ax.legend(loc="upper left", frameon=False, fontsize=7)
clean(ax, keep=("bottom",))
save(fig, "fig3_forecast")
win_only = (a0 + 1) / (a0 + b0 + 1)

# ---------------------------------------------------------------- Figure 4: the planning session's context
S = json.loads((PRE / "data" / "session.json").read_text())
LABELS = [(6.65, "\"1.5 in 4\""), (18.10, "\"2 in 4\""), (18.32, "\"3 in 4 ...\ndo not cheat\""), (18.77, "\"mu and\nsigma\""),
          (19.03, "\"save\nall this\""), (19.26, "\"double\ncheck\""), (20.96, "\"begin\nthe run\"")]
PANELS = [(6.15, 6.85), (18.0, 21.1)]
fig, axes = plt.subplots(1, 2, figsize=(6.9, 2.75), sharey=True, gridspec_kw={"width_ratios": [1, 4.2], "wspace": 0.05})
for ax, (lo, hi) in zip(axes, PANELS):
    cuts = [lo] + [c["h"] for c in S["compactions"] if lo <= c["h"] <= hi] + [hi]
    for a, b in zip(cuts, cuts[1:]):  # one line per stretch between compactions
        pts = [(h, n) for h, n in S["ctx"] if a < h <= b]
        ax.plot([h for h, _ in pts], [n / 1000 for _, n in pts], color=TEAL, lw=1.0, marker="o", ms=1.6)
    for c in S["compactions"]:
        if lo <= c["h"] <= hi:
            ax.axvline(c["h"], color=RED, lw=0.8, ls="--")
            ax.text(c["h"] + 0.02, 296, f"compacted\n{c['pre'] // 1000}k to {c['post'] // 1000}k", color=RED, fontsize=5.8, va="top", linespacing=1.1)
    for p in S["prompts"]:
        if lo <= p["h"] <= hi:
            ax.plot([p["h"]] * 2, [-13, -3], color=PURPLE, lw=0.9, clip_on=False)
    for i, (h, lab) in enumerate(LABELS):
        if lo <= h <= hi:
            ax.text(h, 14 if i % 2 == 0 else 52, lab, ha="center", va="bottom", fontsize=5.6, color=PURPLE, style="italic", linespacing=1.1,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    ax.set_xlim(lo, hi)
    ax.set_ylim(-14, 300)
    ax.xaxis.set_major_formatter(hhmm)
    ax.grid(axis="y", color="#eef0f2", lw=0.6)
    ax.set_axisbelow(True)
    clean(ax, keep=("bottom", "left") if ax is axes[0] else ("bottom",))
axes[0].set_xticks([6.25, 6.5])
axes[1].set_xticks([18 + i / 2 for i in range(7)])
axes[1].tick_params(axis="y", length=0)
axes[0].set_yticks([0, 100, 200, 300])
axes[0].set_ylabel("Tokens in the context (thousands)")
fig.text(0.5, -0.04, "Central time, 11 November 2026 (no prompts between 06:42 and 18:06); purple ticks are the human's prompts", ha="center", fontsize=7.5, color="#5f6368")
save(fig, "fig4_context")

# ---------------------------------------------------------------- Figure 5: the three levels
fig, ax = plt.subplots(figsize=(6.9, 3.0))
ax.set_xlim(0, 112)
ax.set_ylim(0, 44)
ax.axis("off")


def lbox(x, y, w, h, tag, title, body, ec, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", fc=fc, ec=ec, lw=1.0))
    ax.text(x + w / 2, y + h - 1.8, tag, ha="center", va="top", fontsize=6.0, color=ec)
    ax.text(x + w / 2, y + h - 4.6, title, ha="center", va="top", fontsize=6.8, weight="bold", color=INK)
    ax.text(x + w / 2, y + h - 8.4, body, ha="center", va="top", fontsize=5.7, color="#3c4043", linespacing=1.25)


def link(a, b, color, ls="-"):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0, ls=ls, shrinkA=0, shrinkB=0, mutation_scale=9))


BY, BH, BW = 21, 17, 19
LX = [0.5, 34.0, 67.5]
lbox(LX[0], BY, BW, BH, "LEVEL 3", "The human", "sets the goal, target\nand constraints; steers\nand probes the planner", PURPLE, "#f3f0fd")
lbox(LX[1], BY, BW, BH, "LEVEL 2", "The planning agent", "codes, simulates, plans,\nforecasts and does the\nBayesian update", TEAL)
lbox(LX[2], BY, BW, BH, "LEVEL 1", "The player", "an autonomous loop:\nwrites programs,\nreads results", ORANGE)
ax.add_patch(FancyBboxPatch((99.0, BY), 12.5, BH, boxstyle="round,pad=0.25,rounding_size=1.2", fc="#f8f9fa", ec=GREY, lw=1.0))
ax.text(105.25, BY + BH / 2, "Minecraft\nworld and\nworkspace\nfiles", ha="center", va="center", fontsize=6.3, color="#3c4043", linespacing=1.25)
# level 3 <-> level 2
link((LX[0] + BW + 0.6, BY + 11.5), (LX[1] - 0.6, BY + 11.5), PURPLE)
link((LX[1] - 0.6, BY + 5.5), (LX[0] + BW + 0.6, BY + 5.5), TEAL)
ax.text((LX[0] + BW + LX[1]) / 2, BY + 12.3, "prompts", ha="center", va="bottom", fontsize=5.8, color=PURPLE)
ax.text((LX[0] + BW + LX[1]) / 2, BY + 4.7, "plans, estimates,\nexplanations", ha="center", va="top", fontsize=5.8, color=TEAL, linespacing=1.15)
# level 2 -> level 1
link((LX[1] + BW + 0.6, BY + BH / 2), (LX[2] - 0.6, BY + BH / 2), INK)
ax.text((LX[1] + BW + LX[2]) / 2, BY + BH / 2 + 0.9, "inputs, fixed\nbefore the run", ha="center", va="bottom", fontsize=5.8, color=INK, linespacing=1.15)
ax.text((LX[1] + BW + LX[2]) / 2, BY + BH / 2 - 1.0, "no messages\nduring play", ha="center", va="top", fontsize=5.8, color="#5f6368", style="italic", linespacing=1.15)
# level 1 <-> world
link((LX[2] + BW + 0.6, BY + 11.5), (98.5, BY + 11.5), ORANGE)
link((98.5, BY + 5.5), (LX[2] + BW + 0.6, BY + 5.5), GREY)
ax.text((LX[2] + BW + 99.0) / 2, BY + 12.3, "programs", ha="center", va="bottom", fontsize=6.0, color=ORANGE)
ax.text((LX[2] + BW + 99.0) / 2, BY + 4.7, "results", ha="center", va="top", fontsize=6.0, color="#5f6368")
# records back up
ax.plot([LX[2] + BW / 2, LX[2] + BW / 2, LX[1] + BW / 2], [BY - 0.5, 12.5, 12.5], color=GREY, lw=1.0, ls=(0, (3, 2)))
link((LX[1] + BW / 2, 12.5), (LX[1] + BW / 2, BY - 0.6), GREY)
ax.text((LX[1] + LX[2] + BW) / 2, 11.6, "the run's records, after the run", ha="center", va="top", fontsize=6.0, color="#5f6368")
# the interface bracket and the three orders
ax.plot([LX[0], LX[0], LX[1] + BW, LX[1] + BW], [BY + BH + 2.2, BY + BH + 3.6, BY + BH + 3.6, BY + BH + 2.2], color=PURPLE, lw=0.8)
ax.text((LX[0] + LX[1] + BW) / 2, BY + BH + 4.3, "the human-AI interface", ha="center", va="bottom", fontsize=6.6, color=PURPLE, weight="bold")
ax.text(LX[0], 15.5, "The human's meta space, three orders:", fontsize=6.2, color=PURPLE, weight="bold", va="top")
for k, t in enumerate(("1  what the planner should optimise", "2  why the planner answers as it does", "3  what the planner can be driven to do")):
    ax.text(LX[0], 12.3 - 3.1 * k, t, fontsize=6.1, color=PURPLE, va="top")
save(fig, "fig5_levels")

print(f"win-only update: {100 * win_only:.1f}%   prior {100 * a0 / (a0 + b0):.1f}%   posterior {100 * a1 / (a1 + b1):.1f}%")
print(f"context: {S['requests']} requests, peak {S['peak_tokens']}, {len(S['compactions'])} compactions, {len(S['prompts'])} prompts")
