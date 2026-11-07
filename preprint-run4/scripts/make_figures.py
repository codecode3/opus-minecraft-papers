#!/usr/bin/env python3
"""Draw the run 4 preprint's figures from preprint-run4/data/run4.json.

    <python with matplotlib + pillow> preprint-run4/scripts/make_figures.py   -> preprint-run4/figures/*.pdf

Same style as the earlier preprints: pastel bands for the stages, small letter-spaced labels, item icons
from the Pixel Perfection texture pack (CC BY-SA 4.0, in ../preprint/figures/icons/). Run colours checked
with the dataviz validator; the team is a neutral dashed reference, always labelled. Hours are hours on the
official clock, from the player's first spawn, except the team's, which run from its first program.
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import FancyBboxPatch
from matplotlib.patheffects import withStroke
from PIL import Image

PRE = Path(__file__).resolve().parent.parent
FIG = PRE / "figures"
ICONS = PRE.parent / "preprint" / "figures" / "icons"
ALL = json.loads((PRE / "data" / "run4.json").read_text())
R = ALL["runs"]
D, TEAM = R["run4"], ALL["team"]
WIN = D["official_h"]

plt.rcParams.update({
    "font.family": "Avenir Next", "font.size": 7, "pdf.fonttype": 42, "axes.linewidth": 0.6,
    "axes.edgecolor": "#c9ccd1", "xtick.color": "#5f6368", "ytick.color": "#5f6368",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.labelcolor": "#5f6368", "text.color": "#1f1f1f",
})
HALO = [withStroke(linewidth=1.6, foreground="white")]
F = lambda size: max(6.0, size * 1.12)  # printed at about 1:1, so nothing in a figure is under 6 pt
INK, INK2, MUTED, GRID = "#1f1f1f", "#5f6368", "#9aa0a6", "#e8eaed"
RED = "#d93025"
OVER, NETH, END = "#1baf7a", "#eb6834", "#6250d6"
C4, C2, C1, C3, TEAMC = "#6250d6", "#0f8fb3", "#c4761c", "#c23b7a", "#7a8087"  # validated with validate_palette.js
WORK, RECOVER = "#5b6472", "#f4b6ae"
COL = {"run1": C1, "run2": C2, "run3": C3, "run4": C4}
NAME = {"run1": "Run 1", "run2": "Run 2", "run3": "Run 3", "run4": "Run 4"}
M = D["milestones"]
LAST_CRYSTAL = ALL["end"]["last_crystal_h"]
# Ten crystals: no event marks this step. Run 4 from its program output; runs 1 and 2 from their papers, moved to the official clock.
TEN = {"run4": LAST_CRYSTAL, "run2": 8 + 10 / 60 + R["run2"]["spawn_to_first_program_s"] / 3600, "run1": 59 + 48 / 60 + R["run1"]["spawn_to_first_program_s"] / 3600}
STAGES = [("OVERWORLD", 0, M["nether_portal"], "#edf6ea", "#3c8a3a"), ("NETHER AND BACK", M["nether_portal"], M["the_end"], "#fcefe9", "#c5462b"), ("THE END", M["the_end"], WIN, "#f0effa", "#5b4fc4")]
STEPS = [("stone_tools", "Stone tools", "stone_pickaxe"), ("iron_tools", "Iron tools", "iron_pickaxe"), ("bucket", "Bucket", "bucket"),
         ("flint_and_steel", "Flint and steel", "flint_and_steel"), ("nether_portal", "Nether portal", "obsidian"), ("ender_pearls", "Ender pearls", "ender_pearl"),
         ("fortress", "Nether fortress", "nether_bricks"), ("blaze_rods", "Blaze rods", "blaze_rod"),
         ("eyes_of_ender", "Eyes of Ender", "ender_eye"), ("stronghold", "Stronghold", "end_portal_frame_top"), ("the_end", "The End", "end_stone"),
         ("ten_crystals", "Ten crystals", "end_crystal"), ("dragon", "Ender Dragon", "dragon_egg")]


def ms(run, k):
    if k == "ten_crystals":
        return TEN.get(run)
    return R[run]["milestones"].get(k)


def ht(k):
    return TEAM["milestones_min"][k] / 60


def hm(h):
    if h is None:
        return "--"
    m = int(h * 60 + 1e-6)  # floor, as verify-run.py reports it
    return f"{m // 60}:{m % 60:02d}"


def place_icon(ax, name, xy, zoom=0.55, coords="data"):
    im = Image.open(ICONS / f"{name}.png").convert("RGBA")
    ab = AnnotationBbox(OffsetImage(im, zoom=zoom, interpolation="nearest", resample=False), xy, xycoords=coords, frameon=False, pad=0, zorder=6)
    ax.add_artist(ab)


def stage_bands(ax, labels=True, y=1.0):
    for name, a, b, band, col in STAGES:
        ax.axvspan(a, b, color=band, zorder=0, lw=0)
        if labels and name:
            ax.text(a + 0.04, y, name, ha="left", transform=ax.get_xaxis_transform(), fontsize=F(5.2), color=col, fontweight="demibold", va="bottom")


def clean(ax, left=False):
    for s in ("top", "right") + (("left",) if not left else ()):
        ax.spines[s].set_visible(False)
    if not left:
        ax.set_yticks([])


def axes_quiet(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#dadce0")
    ax.spines["bottom"].set_color("#dadce0")


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(FIG / "preview" / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def caps(ax, x, y, text, **kw):
    ax.text(x, y, " ".join(text.upper()).replace("   ", "  "), fontsize=F(5), color=MUTED, fontweight="demibold", **kw)


# ---------------------------------------------------------------- Figure 1: the attempts, step by step
def fig_steps():
    fig = plt.figure(figsize=(6.4, 2.9))
    ax = fig.add_axes([0.185, 0.095, 0.46, 0.825])
    n = len(STEPS)
    for a, b, col in [(0, 4, "#edf6ea"), (5, 9, "#fcefe9"), (10, 12, "#f0effa")]:
        ax.axhspan(a - 0.5, b + 0.5, color=col, lw=0, zorder=0)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xlim(-0.15, 11.3)
    ax.axvline(5, color=INK2, lw=0.6, ls=(0, (2, 2)), zorder=1)
    ax.text(5.06, -0.1, "plan: 5 h", fontsize=F(5.2), color=INK2, ha="left", va="center")
    for run, lw, z in (("run3", 1.0, 2), ("run2", 1.0, 3), ("run4", 1.5, 4)):
        pts = [(ms(run, k), i) for i, (k, _, _) in enumerate(STEPS) if ms(run, k) is not None]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.plot(xs, ys, color=COL[run], lw=lw, zorder=z, solid_joinstyle="round")
        ax.plot(xs, ys, ls="none", marker="o", ms=2.6 if run == "run4" else 2.0, color=COL[run], mew=0, zorder=z + 0.5)
    ax.text(ms("run4", "dragon") - 0.12, 12.0, "This run", fontsize=F(6), fontweight="demibold", color=INK, ha="right", va="center", path_effects=HALO)
    ax.text(ms("run2", "dragon") + 0.14, 12.0, "Run 2", fontsize=F(6), fontweight="demibold", color=INK, ha="left", va="center", path_effects=HALO)
    ax.text(10.95, 7.9, "Run 3, no win", fontsize=F(6), fontweight="demibold", color=INK, ha="right", va="center", path_effects=HALO)
    for k, (key, label, ic) in enumerate(STEPS):
        place_icon(ax, ic, (-0.022, k), zoom=0.34, coords=ax.get_yaxis_transform())
        ax.text(-0.05, k, label, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=F(5.8), fontweight="demibold", color=INK)
        for x, h, bold, dag in ((1.125, ms("run4", key), True, key == "ten_crystals"), (1.262, ms("run2", key), False, key == "ten_crystals"), (1.4, ms("run3", key), False, False),
                                (1.535, ms("run1", key), False, key == "ten_crystals"), (1.67, ht(key), False, False)):
            ax.text(x, k, hm(h) + ("†" if dag else ""), transform=ax.get_yaxis_transform(), ha="right", va="center",
                    fontsize=F(5.6), color=INK if bold else INK2, fontweight="demibold" if bold else "normal")
    for x, t in ((1.125, "This run"), (1.262, "Run 2"), (1.4, "Run 3"), (1.535, "Run 1"), (1.67, "Team")):
        ax.text(x, -0.95, t, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=F(5.2), color=MUTED, fontweight="demibold")
    caps(ax, 0.0, 1.035, "Four Opus attempts, step by step", transform=ax.transAxes)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#dadce0")
    ax.set_yticks([])
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_xticklabels(["0 h", "2 h", "4 h", "6 h", "8 h", "10 h"])
    ax.tick_params(axis="x", labelsize=F(5.2), pad=1.5)
    save(fig, "fig1_steps")


# ---------------------------------------------------------------- Figure 2: the plan against the clock
def fig_plan():
    A = ALL["activity"]
    fig = plt.figure(figsize=(6.4, 2.5))
    ax = fig.add_axes([0.215, 0.1, 0.70, 0.8])
    rows = list(A["stages"]) + [{"key": "slack", "label": "Compactions and slack", "budget": 26, "work": 0, "recover": 0, "actual": 0, "over": -26}]
    H = 0.27
    for i, s in enumerate(rows):
        ax.barh(i - H / 2 - 0.02, s["budget"], height=H, color="white", edgecolor=INK2, lw=0.7, zorder=3)
        ax.barh(i + H / 2 + 0.02, s["work"], height=H, color=WORK, lw=0, zorder=3)
        ax.barh(i + H / 2 + 0.02, s["recover"], left=s["work"], height=H, color=RECOVER, lw=0, zorder=3)
        ax.text(-2.5, i, s["label"], ha="right", va="center", fontsize=F(5.8), color=INK, fontweight="demibold")
        top = max(s["budget"], s["actual"])
        lab = f"+{s['over']:.0f}" if s["over"] > 0 else f"−{abs(s['over']):.0f}"
        ax.text(top + 2.2, i, lab + " min", ha="left", va="center", fontsize=F(5.6), color=INK if s["over"] > 0 else INK2, fontweight="demibold" if s["over"] > 0 else "normal")
    ax.set_ylim(len(rows) - 0.45, -0.75)
    ax.set_xlim(0, 150)
    ax.set_xticks([0, 30, 60, 90, 120, 150])
    ax.set_xticklabels(["0", "30", "60", "90", "120", "150 min"])
    ax.tick_params(axis="x", labelsize=F(5.2), pad=1.5)
    for x in (30, 60, 90, 120, 150):
        ax.axvline(x, color=GRID, lw=0.4, zorder=0)
    clean(ax)
    ax.spines["bottom"].set_color("#dadce0")
    caps(ax, -0.285, 1.035, "Budget against the clock, by stage", transform=ax.transAxes)
    # Key, in the empty upper right
    x0 = 82
    ax.barh(6.95, 8, left=x0, height=0.3, color="white", edgecolor=INK2, lw=0.7, zorder=3)
    ax.text(x0 + 10, 6.95, "budget in the plan (300 min)", fontsize=F(5.3), color=INK2, va="center")
    ax.barh(7.55, 8, left=x0, height=0.3, color=WORK, lw=0, zorder=3)
    ax.text(x0 + 10, 7.55, f"working ({A['work_min']:.0f} min)", fontsize=F(5.3), color=INK2, va="center")
    ax.barh(8.15, 8, left=x0, height=0.3, color=RECOVER, lw=0, zorder=3)
    ax.text(x0 + 10, 8.15, f"recovering from a death ({A['minutes']['recover']:.0f} min)", fontsize=F(5.3), color=INK2, va="center")
    save(fig, "fig2_plan")


# ---------------------------------------------------------------- Figure 3: the whole run
def fig_run():
    fig = plt.figure(figsize=(6.4, 3.25))
    hs = [0.2, 0.17, 0.095, 0.095, 0.27]
    axs, top = [], 0.97
    for h in hs:
        axs.append(fig.add_axes([0.125, top - h, 0.855, h - 0.018]))
        top -= h
    a0, a1, a2, a3, a4 = axs
    for a in axs:
        stage_bands(a, labels=(a is a0), y=1.04)
        a.set_xlim(-0.06, WIN + 0.06)
        clean(a)
        a.set_xticks([])
    a0.set_ylim(0, 1)
    marks = [("iron_tools", "Iron", "iron_pickaxe", 0.72, 1), ("nether_portal", "Portal", "obsidian", 0.26, 1), ("ender_pearls", "First pearl", "ender_pearl", 0.72, 1),
             ("fortress", "Fortress", "nether_bricks", 0.26, 1), ("blaze_rods", "First rod", "blaze_rod", 0.72, 1), ("eyes_of_ender", "Eyes", "ender_eye", 0.26, 1),
             ("the_end", "Stronghold, End", "end_stone", 0.72, 1)]
    for k, label, ic, y, side in marks:
        x = M[k]
        place_icon(a0, ic, (x, y), zoom=0.36)
        a0.text(x + side * 0.1, y, label, fontsize=F(5.4), fontweight="demibold", va="center", ha="left" if side > 0 else "right")
    place_icon(a0, "end_crystal", (LAST_CRYSTAL, 0.26), zoom=0.36)
    a0.text(LAST_CRYSTAL - 0.1, 0.26, "Last crystal", fontsize=F(5.4), fontweight="demibold", va="center", ha="right")
    place_icon(a0, "dragon_egg", (WIN, 0.72), zoom=0.36)
    a0.text(WIN - 0.1, 0.72, "Dragon", fontsize=F(5.4), fontweight="demibold", va="center", ha="right")
    a1.set_ylim(-0.1, 1.1)
    a1.text(-0.13, 0.5, "opus", fontsize=F(6.5), fontweight="demibold", color=END, ha="right", va="center")
    for adv in D["advancements"]:
        a1.plot(adv["h"], 0.86, marker="D", ms=2.8, color=INK, mew=0, zorder=4)
    for dth in D["deaths"]:
        a1.plot([dth["h"]] * 2, [0.46, 0.72], color=RED, lw=1.1, zorder=4)
    for c in ALL["commits"]:
        if 0 <= c["h"] <= WIN + 0.02:
            a1.plot([c["h"]] * 2, [0.22, 0.34], color=INK2, lw=0.6, zorder=4)
    for c in ALL["compactions"]:
        a1.plot(c["h"], 0.08, marker="v", ms=3, color=INK2, mew=0, zorder=4)
    # Where the player was, from the camera
    a2.set_ylim(0, 1)
    ch = ALL["dim_changes"] + [{"h": WIN, "dim": None}]
    dcol = {"overworld": OVER, "the_nether": NETH, "the_end": END}
    for u, v in zip(ch, ch[1:]):
        if u["dim"]:
            a2.barh(0.5, v["h"] - u["h"], left=u["h"], height=0.9, color=dcol[u["dim"]], lw=0, zorder=3)
    a2.text(-0.13, 0.5, "Place", fontsize=F(5.6), fontweight="demibold", ha="right", va="center")
    # Working or recovering
    a3.set_ylim(0, 1)
    for s in ALL["activity"]["stretches"]:
        a3.barh(0.5, s["b"] - s["a"], left=s["a"], height=0.9, color=(RECOVER if s["kind"] == "recover" else WORK), lw=0, zorder=3)
    a3.text(-0.13, 0.5, "Doing", fontsize=F(5.6), fontweight="demibold", ha="right", va="center")
    pph = D["programs"]["per_half_hour"]
    for b_, n_ in pph:
        lo, hi = b_ / 2 + 0.02, min(b_ / 2 + 0.48, WIN)  # the last bin is cut at the win
        a4.bar(lo, n_, width=hi - lo, align="edge", color="#a8c7fa", lw=0, zorder=3)
    a4.set_ylim(0, 105)
    a4.text(-0.13, 50, "Programs\nper half hour", fontsize=F(5.6), fontweight="demibold", ha="right", va="center", linespacing=1.2)
    a4.set_yticks([0, 30, 60, 90])
    a4.tick_params(axis="y", labelsize=F(5), length=0, pad=1)
    a4.yaxis.tick_right()
    for y in (30, 60, 90):
        a4.axhline(y, color="white", lw=0.5, zorder=1)
    a4.spines["bottom"].set_visible(True)
    a4.spines["bottom"].set_color("#dadce0")
    ticks = list(range(0, 7))
    a4.set_xticks(ticks[:-1] + [WIN])
    a4.set_xticklabels([f"{t} h" for t in ticks[:-1]] + ["6 h 51"], fontsize=F(5.4))
    a4.get_xticklabels()[-1].set_fontweight("demibold")
    a4.axvline(5, color=INK2, lw=0.6, ls=(0, (2, 2)), zorder=5)
    a4.text(5.04, 102, "plan: 5 h", fontsize=F(5.2), color=INK2, va="top", ha="left")
    lg = fig.add_axes([0.0, -0.05, 0.98, 0.05])
    lg.axis("off")
    lg.set_xlim(0, 1)
    lg.set_ylim(0, 1)
    x = 0.0
    for m_, c, t in (("D", INK, "advancement"), ("|", RED, "death"), ("|", INK2, "commit"), ("v", INK2, "compaction")):
        lg.plot(x + 0.006, 0.35, marker=m_, ms=3 if m_ != "|" else 5, color=c, mew=0.8 if m_ == "|" else 0)
        x += 0.016
        lg.text(x, 0.35, t, fontsize=F(5.3), color=INK2, va="center")
        x += 0.0088 * len(t) + 0.028
    for c, t in ((OVER, "Overworld"), (NETH, "Nether"), (END, "End"), (WORK, "working"), (RECOVER, "recovering")):
        lg.add_patch(plt.Rectangle((x, 0.14), 0.011, 0.42, color=c, lw=0))
        x += 0.015
        lg.text(x, 0.35, t, fontsize=F(5.3), color=INK2, va="center")
        x += 0.0088 * len(t) + 0.022
    save(fig, "fig3_run")


# ---------------------------------------------------------------- Figure 4: what came from whom
READS = [(0.0, 0.57, "first 34 min:\nnotes, libraries,\npearl and room\nprograms"), (0.93, 1.45, "pearls, mortar,\nbow, cobwebs"), (2.11, 2.24, "rooms, crystals"), (3.2, 3.92, "End, eyes,\nstronghold"), (4.13, 4.69, "run 2's arrival\nand fight programs"), (5.64, 6.6, "run 2's dragon,\nmortar, last crystals")]
ORIGIN = (("run1", C1, "Run 1"), ("run2", C2, "Run 2"), ("run3", C3, "Run 3"), ("own", C4, "This run"))


def fig_lineage():
    fig = plt.figure(figsize=(6.4, 3.65))
    top = fig.add_axes([0.075, 0.70, 0.905, 0.265])
    mid = fig.add_axes([0.075, 0.385, 0.905, 0.27])
    use = fig.add_axes([0.075, 0.06, 0.905, 0.255])
    for a in (top, mid):
        stage_bands(a, labels=(a is top), y=1.02)
        a.set_xlim(-0.08, WIN + 0.06)
    top.set_ylim(0, 6)
    for a_, b_, lab in READS:
        top.text(0.0 if a_ == 0 else (a_ + b_) / 2, 1.05, lab, fontsize=F(4.9), color=INK2, ha="left" if a_ == 0 else "center", va="bottom", linespacing=1.12, zorder=5)
    for t in ALL["inherited_use"]["text"]:
        rs = t["runs"]
        col = C2 if "run2" in rs else (C3 if "run3" in rs else (C1 if "run1" in rs else MUTED))
        top.plot([t["h"]] * 2, [0.2, 0.75], color=col, lw=0.9, zorder=4, solid_capstyle="butt")
    clean(top)
    top.set_xticks([])
    top.spines["bottom"].set_visible(False)
    top.text(-0.06, 5.75, f"Each tick: one tool call naming an earlier player's folder ({ALL['inherited_use']['calls']})", fontsize=F(5.3), color=INK2, va="top", fontweight="demibold")
    # Library per commit
    cs = [c for c in ALL["commits"] if c["lib_lines"] > 0 and c["h"] <= WIN + 0.02]
    xs = [max(0, c["h"]) for c in cs] + [WIN]
    y0 = [0] * len(xs)
    for k, col, _ in ORIGIN:
        vals = [c["lib"].get(k, 0) for c in cs]
        vals.append(vals[-1])
        y1 = [a + b for a, b in zip(y0, vals)]
        mid.fill_between(xs, y0, y1, step="post", color=col, alpha=0.9 if k == "own" else 0.7, lw=0, zorder=2)
        y0 = y1
    mid.set_ylim(0, 4100)
    mid.set_xlim(-0.08, WIN + 0.06)
    last = cs[-1]["lib"]
    mid.text(3.4, 1200, f"First written by run 1: {last['run1']:,} of {cs[-1]['lib_lines']:,} lines", fontsize=F(5.6), color="white", fontweight="demibold", va="center", ha="center")
    mid.text(WIN - 0.06, 3880, f"This run: {cs[0]['lib']['own']} lines at its first library commit, {last['own']} at the win", fontsize=F(5.4), color=INK, ha="right", va="center")
    axes_quiet(mid)
    mid.set_yticks([0, 1000, 2000, 3000])
    mid.set_yticklabels(["0", "1,000", "2,000", "3,000"])
    mid.tick_params(axis="y", labelsize=F(5), pad=1)
    mid.set_xticks([])
    mid.text(-0.065, 0.5, "Library lines", transform=mid.transAxes, rotation=90, fontsize=F(5.3), color=INK2, va="center", ha="center", fontweight="demibold")
    # Calls per hour, by origin of the name
    O = ALL["lineage"]["per_hour"]
    use.set_xlim(-0.08, WIN + 0.06)
    use.set_ylim(0, 100)
    for h_ in range(7):
        c_ = O[str(h_)]
        n_ = sum(c_.values())
        x0, x1 = h_ + 0.03, (WIN if h_ == 6 else h_ + 1) - 0.03
        y_ = 0
        for k_, col_, _ in ORIGIN:
            v_ = c_.get(k_, 0) / n_ * 100
            use.bar(x0, v_, x1 - x0, y_, align="edge", color=col_, lw=0, zorder=3, alpha=0.9 if k_ == "own" else 0.8)
            if v_ >= 9:
                use.text((x0 + x1) / 2, y_ + v_ / 2, f"{v_:.0f}%", ha="center", va="center", fontsize=F(5.0), color="white", fontweight="demibold", zorder=5)
            y_ += v_
    axes_quiet(use)
    use.set_yticks([0, 50, 100])
    use.set_yticklabels(["0", "50%", "100%"])
    use.tick_params(axis="y", labelsize=F(5), pad=1)
    use.set_xticks(list(range(0, 7)))
    use.set_xticklabels([f"{t} h" for t in range(0, 7)], fontsize=F(5.2))
    use.text(-0.065, 0.5, "Calls in programs", transform=use.transAxes, rotation=90, fontsize=F(5.3), color=INK2, va="center", ha="center", fontweight="demibold")
    x_ = 0.0
    use.text(x_, 1.065, "First written by", transform=use.transAxes, fontsize=F(5.3), color=INK2, va="center")
    x_ += 0.115
    for _, col_, lab_ in ORIGIN:
        use.add_patch(plt.Rectangle((x_, 1.035), 0.012, 0.06, transform=use.transAxes, color=col_, lw=0, clip_on=False))
        use.text(x_ + 0.017, 1.065, lab_, transform=use.transAxes, fontsize=F(5.3), color=INK, va="center")
        x_ += 0.017 + len(lab_) * 0.0098 + 0.03
    save(fig, "fig4_lineage")


# ---------------------------------------------------------------- Figure 5: deaths across the runs
def fig_deaths():
    fig = plt.figure(figsize=(6.4, 2.85))
    # Rasters on one clock
    a = fig.add_axes([0.075, 0.57, 0.915, 0.37])
    caps(a, 0.0, 1.05, "Every death on one clock; red ticks came within 5 minutes of the one before", transform=a.transAxes)
    order = ("run4", "run2", "run3", "run1")
    for i, run in enumerate(order):
        a.plot([0, min(R[run]["official_h"], 11)], [i, i], color=GRID, lw=2.4, zorder=1, solid_capstyle="butt")
        prev = None
        for d in R[run]["deaths"]:
            if d["h"] > 11:
                break
            chain = prev is not None and (d["h"] - prev) * 60 <= 5
            a.plot([d["h"]] * 2, [i - 0.3, i + 0.3], color=RED if chain else INK, lw=1.0 if chain else 0.9, zorder=3)
            prev = d["h"]
        n = R[run]["chain_5min"]
        label = {"run4": f"Run 4: 10 deaths, {n} in chains", "run2": f"Run 2: 16, {n} in chains", "run3": f"Run 3: 34, {n} in chains", "run1": f"Run 1 (first 11 h)"}[run]
        a.text(-0.09, i, NAME[run], ha="right", va="center", fontsize=F(5.6), fontweight="demibold", color=INK)
        if run in ("run4", "run2"):
            a.text(R[run]["official_h"] + 0.1, i, label.split(": ")[1], ha="left", va="center", fontsize=F(5.3), color=INK2)
        elif run == "run3":
            a.text(11.06, i, "34, 9 in chains", ha="left", va="center", fontsize=F(5.3), color=INK2)
        else:
            a.text(11.06, i, f"115 in 61 h,\n31 in chains", ha="left", va="center", fontsize=F(5.3), color=INK2, linespacing=1.05)
    a.set_ylim(3.55, -0.55)
    a.set_xlim(-0.05, 12.3)
    a.set_xticks(range(0, 12))
    a.set_xticklabels([f"{t} h" for t in range(0, 12)], fontsize=F(5.2))
    clean(a)
    a.spines["bottom"].set_color("#dadce0")
    # By place
    b = fig.add_axes([0.075, 0.1, 0.42, 0.33])
    caps(b, 0.0, 1.05, "Deaths per hour in each place", transform=b.transAxes)
    S = ALL["by_place"]
    runs = ("run1", "run2", "run3", "run4")
    W = 0.2
    for i, (name, k) in enumerate((("Overworld", "overworld"), ("Nether", "the_nether"), ("End", "the_end"))):
        for j, run in enumerate(runs):
            v = S[run][k]["per_h"]
            x = i + (j - 1.5) * W
            if v is None:
                b.text(x, 0.12, "–", ha="center", fontsize=F(5), color=MUTED)
                continue
            b.bar(x, v, width=W - 0.03, color=COL[run], lw=0, zorder=3)
            b.text(x, v + 0.18, f"{v:.1f}", ha="center", fontsize=F(5), color=INK2, fontweight="demibold" if run == "run4" else "normal")
    b.set_xticks(range(3))
    b.set_xticklabels(["Overworld", "Nether", "End"], fontsize=F(5.4))
    b.set_ylim(0, 8.6)
    b.set_yticks([])
    for s_ in ("top", "right", "left"):
        b.spines[s_].set_visible(False)
    b.spines["bottom"].set_color("#dadce0")
    # Back at the spot
    c = fig.add_axes([0.575, 0.1, 0.415, 0.33])
    caps(c, 0.0, 1.05, "Back at the spot of each death", transform=c.transAxes)
    for run in runs:
        p = R[run]["places"]
        vals = sorted(v / 60 for v in p["back_s"])
        tot = p["deaths_with_frame"]
        xs = [0.1] + vals + [600]
        ys = [0] + [(i + 1) / tot * 100 for i in range(len(vals))] + [len(vals) / tot * 100]
        c.step(xs, ys, where="post", color=COL[run], lw=1.5 if run == "run4" else 1.0, zorder=4 if run == "run4" else 3)
    c.set_xscale("log")
    c.set_xlim(0.3, 600)
    c.set_ylim(0, 105)
    c.set_xticks([1, 5, 30, 180, 600])
    c.set_xticklabels(["1 min", "5", "30", "3 h", "10 h"], fontsize=F(5.2))
    c.minorticks_off()
    c.set_yticks([0, 50, 100])
    c.set_yticklabels(["0", "50%", "100%"], fontsize=F(5))
    axes_quiet(c)
    c.axvline(5, color=GRID, lw=0.6, zorder=1)
    # One legend, under both panels
    lg = fig.add_axes([0.075, -0.045, 0.915, 0.05])
    lg.axis("off")
    lg.set_xlim(0, 1)
    lg.set_ylim(0, 1)
    x = 0.0
    labels = {r: f"{NAME[r]}: {R[r]['places']['returned']} of {R[r]['places']['deaths_with_frame']} back" for r in runs}
    for r in runs:
        lg.plot(x + 0.006, 0.4, marker="o", ms=3.8, color=COL[r], mew=0)
        lg.text(x + 0.018, 0.4, labels[r], fontsize=F(5.3), color=INK2, va="center")
        x += 0.018 + len(labels[r]) * 0.0078 + 0.03
    lg.text(1, 0.4, "Time after the death (log scale)", fontsize=F(5.3), color=MUTED, ha="right", va="center")
    save(fig, "fig5_deaths")


# ---------------------------------------------------------------- Figure 6: the End
CRYSTALS = [  # x, height, z, method group; from the programs' own kill lines
    (42, 92, 0, 1), (-13, 77, -40, 1),
    (12, 101, -40, 2), (-13, 89, 39, 2), (-42, 86, -1, 2), (-34, 98, 24, 2), (-34, 95, -25, 2),
    (33, 83, -25, 3), (33, 80, 24, 3), (12, 104, 39, 4)]
DEATHS_END = [(3.7, -17.3, "7"), (3.7, -17.7, "8"), (0.3, -17.5, "9"), (24.5, -20.8, "10")]  # positions from the death events


def fig_end():
    fig = plt.figure(figsize=(6.4, 2.75))
    m = fig.add_axes([0.0, 0.05, 0.43, 0.87])
    caps(m, 0.03, 1.02, "The ten crystals, from above", transform=m.transAxes)
    m.set_aspect("equal")
    m.set_xlim(-58, 118)
    m.set_ylim(58, -62)
    m.add_patch(FancyBboxPatch((-56, -61), 172, 117, boxstyle="round,pad=0,rounding_size=6", fc="#f6f5fd", ec="none", zorder=0))
    m.add_patch(plt.Circle((0, 0), 43, fc="none", ec="#e1def7", lw=4, zorder=1))
    m.plot(0, 0, marker="s", ms=4.5, color="#3c4043", zorder=4)
    m.text(-3, 4.5, "exit portal", fontsize=F(4.7), color=INK2, ha="right", va="top")
    m.plot(100, 0, marker="s", ms=4.2, color="#202124", zorder=4)
    m.text(100, 5, "arrival over\nthe void,\ndeath 6", fontsize=F(4.6), color=INK2, ha="center", va="top", linespacing=1.1)
    m.plot(4, -8, marker="^", ms=5, color=NETH, zorder=6)
    m.annotate("mortar pit", xy=(4, -8), xytext=(21, -2), fontsize=F(5), color=INK, ha="center", va="center", fontweight="demibold",
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5), zorder=7)
    for x, z, lab in DEATHS_END:
        m.plot(x, z, marker="x", ms=3.6, mew=1.0, color=RED, zorder=6)
    m.text(10, -23, "deaths 7, 8, 9, 10", fontsize=F(4.8), color=RED, ha="center", va="bottom")
    colors = {1: "#8a7be0", 2: END, 3: "#c23b7a", 4: "#0f8fb3"}
    for x, y, z, g in CRYSTALS:
        m.plot(x, z, marker="o", ms=8, mfc="white", mec=colors[g], mew=1.2, zorder=5)
        place_icon(m, "end_crystal", (x, z), zoom=0.26)
        r = math.hypot(x, z)
        m.text(x * (1 + 10 / r), z * (1 + 10 / r), str(y), fontsize=F(4.6), color=INK2, ha="center", va="center")
    key = [(1, "by 5:52", "2 by peek shots"), (2, "by 6:07", "5 by mortar, 20 arrows"), (3, "by 6:35", "2 from sealed towers"), (4, "6:35", "1 by egg, from a tower")]
    for j, (g, t, what) in enumerate(key):
        yy = -55 + 7.4 * j
        m.plot(52, yy, marker="o", ms=4.5, mfc="white", mec=colors[g], mew=1.1)
        m.text(56.5, yy, f"{t}  {what}", fontsize=F(4.7), color=INK2, va="center")
    m.text(114, 54, "Numbers: crystal height", fontsize=F(4.5), color=MUTED, ha="right", va="bottom")
    m.axis("off")
    b = fig.add_axes([0.51, 0.17, 0.48, 0.72])
    caps(b, 0.0, 1.05, "The dragon's health after the last crystal", transform=b.transAxes)
    # Run 2's hours in this list run from its first program; its last crystal is at 8:10 on that clock.
    r2 = [(0.0, 200.0)] + [((x["h"] - ALL["run2_ten_h_from_first_program"]) * 60, x["hp"]) for x in ALL["dragon_run2"] if x["h"] >= ALL["run2_ten_h_from_first_program"]]
    r4 = [(0.0, ALL["end"]["hp_at_last_crystal"])] + [((x["h"] - LAST_CRYSTAL) * 60, x["hp"]) for x in ALL["dragon"] if LAST_CRYSTAL <= x["h"] <= WIN + 0.01]
    r4 = [(min(t, (WIN - LAST_CRYSTAL) * 60), hp) for t, hp in r4]
    r2_end = (R["run2"]["from_first_program_h"] - ALL["run2_ten_h_from_first_program"]) * 60
    r2 = [(min(t, r2_end), hp) for t, hp in r2]
    b.step([p[0] for p in r2], [p[1] for p in r2], where="post", color=C2, lw=1.0, zorder=3)
    b.step([p[0] for p in r4], [p[1] for p in r4], where="post", color=C4, lw=1.5, zorder=4)
    for dth in R["run2"]["deaths"]:
        t_ = (dth["h"] - R["run2"]["spawn_to_first_program_s"] / 3600 - ALL["run2_ten_h_from_first_program"]) * 60
        if t_ >= 0:
            b.plot([t_] * 2, [-14, -4], color=RED, lw=0.9, clip_on=False, zorder=4)
    b.text(6.2, -9, "run 2's deaths", fontsize=F(4.8), color=RED, va="center", ha="right")
    b.annotate("This run: 15 min, no deaths,\n8 perches, no damage taken", xy=((WIN - LAST_CRYSTAL) * 60, 2), xytext=(19, 28), fontsize=F(5.2), color=INK, ha="left", va="center", linespacing=1.15, fontweight="demibold",
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    b.text(37, 118, "Run 2: 57 min,\n4 deaths", fontsize=F(5.2), color=INK, ha="left", va="center", linespacing=1.15, fontweight="demibold")
    b.annotate("two perches,\n56 each", xy=(9.1, 128), xytext=(1.0, 120), fontsize=F(5.0), color=INK2, ha="left", va="center", linespacing=1.1, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    b.set_xlim(0, 60)
    b.set_ylim(-16, 210)
    b.set_xticks([0, 15, 30, 45, 60])
    b.set_xticklabels(["0", "15", "30", "45", "60 min"], fontsize=F(5.2))
    b.set_yticks([0, 100, 200])
    b.tick_params(axis="y", labelsize=F(5))
    axes_quiet(b)
    b.spines["bottom"].set_position(("data", -16))
    b.text(1, -0.14, "Minutes since the last crystal", transform=b.transAxes, ha="right", va="top", fontsize=F(5.3), color=MUTED)
    save(fig, "fig6_end")


if __name__ == "__main__":
    (FIG / "preview").mkdir(parents=True, exist_ok=True)
    fig_steps()
    fig_plan()
    fig_run()
    fig_lineage()
    fig_deaths()
    fig_end()
    print("figures written")
