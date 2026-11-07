#!/usr/bin/env python3
"""Draw the run 2 preprint's figures from preprint-run2/data/run2.json.

    <python with matplotlib + pillow> preprint-run2/scripts/make_figures.py   -> preprint-run2/figures/*.pdf

Same style as the first preprint's figures: pastel bands for the four stages, small letter-spaced labels,
item icons from the Pixel Perfection texture pack (CC BY-SA 4.0, in ../preprint/figures/icons/). Run colours
checked with the dataviz validator; the team is a neutral dashed reference, always labelled. Hours are hours
since each run's first program.
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
ALL = json.loads((PRE / "data" / "run2.json").read_text())
D, R1, TEAM = ALL["run2"], ALL["run1"], ALL["team"]
WIN = D["win_h"]

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
THIS, FIRST, TEAMC = END, "#c4761c", "#7a8087"  # this run, run 1, the team
M = D["milestones"]
TEN = 8 + 10 / 60  # the player's commit "All ten crystals destroyed at t+8:10"; the dashboard step never fired, in either run
R1_TEN = 59 + 48 / 60  # the first preprint
STAGES = [("OVERWORLD", 0, M["nether_portal"], "#edf6ea", "#3c8a3a"), ("NETHER", M["nether_portal"], M["stronghold"], "#fcefe9", "#c5462b"),
          ("", M["stronghold"], M["the_end"], "#eef0f4", "#6b7280"), ("THE END", M["the_end"], WIN, "#f0effa", "#5b4fc4")]
STEPS = [("stone_tools", "Stone tools", "stone_pickaxe"), ("iron_tools", "Iron tools", "iron_pickaxe"), ("bucket", "Bucket", "bucket"),
         ("flint_and_steel", "Flint and steel", "flint_and_steel"), ("nether_portal", "Nether portal", "obsidian"),
         ("fortress", "Nether fortress", "nether_bricks"), ("blaze_rods", "Blaze rods", "blaze_rod"), ("ender_pearls", "Ender pearls", "ender_pearl"),
         ("eyes_of_ender", "Eyes of Ender", "ender_eye"), ("stronghold", "Stronghold", "end_portal_frame_top"), ("the_end", "The End", "end_stone"),
         ("ten_crystals", "Ten crystals", "end_crystal"), ("dragon", "Ender Dragon", "dragon_egg")]


def h2(k):
    return TEN if k == "ten_crystals" else M[k]


def h1(k):
    return R1_TEN if k == "ten_crystals" else R1["milestones"][k]


def ht(k):
    return TEAM["milestones_min"][k] / 60


def hm(h):
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
            ax.text(a + 0.06, y, name, ha="left", transform=ax.get_xaxis_transform(), fontsize=F(5.2), color=col, fontweight="demibold", va="bottom")


def clean(ax, left=False):
    for s in ("top", "right") + (("left",) if not left else ()):
        ax.spines[s].set_visible(False)
    if not left:
        ax.set_yticks([])


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(FIG / "preview" / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def caps(ax, x, y, text, **kw):
    ax.text(x, y, " ".join(text.upper()).replace("   ", "  "), fontsize=F(5), color=MUTED, fontweight="demibold", **kw)


# ---------------------------------------------------------------- Figure 1: the three runs, step by step
def fig_steps():
    fig = plt.figure(figsize=(6.4, 2.75))
    ax = fig.add_axes([0.185, 0.1, 0.565, 0.82])
    n = len(STEPS)
    bands = [(0, 4, "#edf6ea"), (5, 8, "#fcefe9"), (9, 9, "#eef0f4"), (10, 12, "#f0effa")]
    for a, b, col in bands:
        ax.axhspan(a - 0.5, b + 0.5, color=col, lw=0, zorder=0)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xlim(-0.8, 62)
    for key, col, lw, ls, z in (("team", TEAMC, 0.9, (0, (2.2, 1.6)), 2), ("run1", FIRST, 1.0, "-", 3), ("run2", THIS, 1.4, "-", 4)):
        f = {"team": ht, "run1": h1, "run2": h2}[key]
        xs = [0] + [f(k) for k, _, _ in STEPS]
        ys = [0] + list(range(n))
        ax.step(xs, ys, where="post", color=col, lw=lw, ls=ls, zorder=z, solid_joinstyle="miter")
        ax.plot(xs[1:], ys[1:], ls="none", marker="o", ms=1.9 if key != "run2" else 2.3, color=col, mew=0, zorder=z + 0.5)
    ax.text(h2("dragon") + 0.9, n - 1.15, "This run", fontsize=F(6), fontweight="demibold", color=INK, ha="left", va="center", path_effects=HALO)
    ax.text(ht("dragon") + 0.9, n - 1.15, "The paper's team", fontsize=F(6), fontweight="demibold", color=INK, ha="left", va="center", path_effects=HALO)
    ax.text(h1("the_end") + 1.0, 9.65, "First Opus run", fontsize=F(6), fontweight="demibold", color=INK, ha="left", va="center", path_effects=HALO)
    for k, (key, label, ic) in enumerate(STEPS):
        place_icon(ax, ic, (-0.022, k), zoom=0.34, coords=ax.get_yaxis_transform())
        ax.text(-0.05, k, label, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=F(5.8), fontweight="demibold", color=INK)
        for x, f, bold in ((1.075, h2, True), (1.19, h1, False), (1.305, ht, False)):
            ax.text(x, k, hm(f(key)) + ("†" if key == "ten_crystals" and f is not ht else ""), transform=ax.get_yaxis_transform(), ha="right", va="center",
                    fontsize=F(5.6), color=INK if bold else INK2, fontweight="demibold" if bold else "normal")
    for x, t in ((1.075, "This run"), (1.19, "First run"), (1.305, "Team")):
        ax.text(x, -0.95, t, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=F(5.2), color=MUTED, fontweight="demibold")
    caps(ax, 0.0, 1.035, "The three runs, step by step", transform=ax.transAxes)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#dadce0")
    ax.set_yticks([])
    ax.set_xticks([0, 10, 20, 30, 40, 50, 60])
    ax.set_xticklabels(["0 h", "10 h", "20 h", "30 h", "40 h", "50 h", "60 h"])
    ax.tick_params(axis="x", labelsize=F(5.2), pad=1.5)
    save(fig, "fig1_steps")


# ---------------------------------------------------------------- Figure 2: what the player got, and its loop
def box(ax, x, y, w, h, title, body, title_col=INK, fc="white", ec="#e3e5e8", dashed=False, ic=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012", fc=fc, ec=ec, lw=0.7, ls=(0, (3, 2)) if dashed else "-"))
    tx = x + 0.014
    if ic:
        place_icon(ax, ic, (x + 0.026, y + h - 0.036), zoom=0.42)
        tx = x + 0.048
    ax.text(tx, y + h - 0.036, title, fontsize=F(6.1), fontweight="demibold", color=title_col, va="center")
    ax.text(x + 0.014, y + h - 0.057, body, fontsize=F(4.95), color=INK2, va="top", linespacing=1.38)


def arrow(ax, a, b, text=None, dashed=False, col="#9aa0a6", dy=0.018, dx=0.0, ha="center"):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=col, lw=0.8, mutation_scale=7, ls=(0, (3, 2)) if dashed else "-", shrinkA=0, shrinkB=0))
    if text:
        ax.text((a[0] + b[0]) / 2 + dx, (a[1] + b[1]) / 2 + dy, text, fontsize=F(4.7), color=MUTED, ha=ha)


def fig_setup():
    fig = plt.figure(figsize=(6.4, 3.75))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0.045, 0.665)
    # Row 1: what it was given
    box(ax, 0.004, 0.462, 0.33, 0.198, "The first player's folder (read-only, 1.0 GB)",
        "Its memory, its 51-file library, 68 program files,\ngit history, every program and event, its\nconversation, the server log, camera frames\nand the first paper. A generated INDEX.md\nlists it all.", fc="#fbf8f2", ec="#ecdfc8")
    box(ax, 0.345, 0.462, 0.32, 0.198, "Two manifests (2,018 words)",
        "Infrastructure: a sealed base with four walls,\nfloor, ceiling and torch; 10 mined obsidian and\nflint and steel before every Nether entry.\nPlanning: when to plan, target times, what to\navoid, budgets for each planning pass.", fc="#f6f8fd", ec="#d6e0f5")
    box(ax, 0.676, 0.462, 0.32, 0.198, "The objective and one request",
        "The first run's objective, plus: this is a speedrun,\nwith both earlier times. Before your first program,\nmeasure where the previous player lost time and\nlives, and plan with targets. After a miss or a\ndeath, change the tool.", fc="#f7f7f8")
    # Row 2: the agent and its files
    box(ax, 0.235, 0.232, 0.27, 0.173, "One Claude Opus 5.5 agent, xhigh",
        "The same harness as the first run.\n7 min 52 s of reading and measuring\nbefore its first program, while the\nworld was already running.", title_col=END, fc="#f6f5fd", ec="#d9d5f5")
    box(ax, 0.565, 0.232, 0.431, 0.173, "Its own workspace", "memory/: 00-plan (under 1,800 characters, rewritten as it\nwent), 01-targets, 02-lessons (112 lines), 03-world.\nlib/: 52 files, 81% of the lines identical to the first\nplayer's. 27 commits to the win.", ic="writable_book")
    arrow(ax, (0.17, 0.462), (0.27, 0.405))
    ax.text(0.2, 0.4335, "searched 19 times during the run", fontsize=F(4.7), color=MUTED, ha="right", va="center")
    arrow(ax, (0.505, 0.462), (0.42, 0.405))
    ax.text(0.472, 0.4335, "reread at all 7 compactions", fontsize=F(4.7), color=MUTED, ha="left", va="center")
    arrow(ax, (0.836, 0.462), (0.505, 0.385))
    arrow(ax, (0.505, 0.345), (0.565, 0.345))
    arrow(ax, (0.565, 0.305), (0.505, 0.305))
    # Row 3: the game
    box(ax, 0.235, 0.05, 0.17, 0.135, "780 programs", "JavaScript, a median\nof 5.9 s each.", ic="wooden_pickaxe")
    box(ax, 0.44, 0.05, 0.178, 0.135, "A Mineflayer bot", "The same library,\nno helpers added.", ic="crafting_table_front")
    box(ax, 0.653, 0.05, 0.343, 0.135, "A Minecraft server", "Java 1.20.4, survival on Easy, a new random\nseed that the agent never saw.", ic="grass_block_side")
    arrow(ax, (0.285, 0.232), (0.285, 0.185))
    ax.text(0.277, 0.2085, "writes", fontsize=F(4.7), color=MUTED, ha="right", va="center")
    arrow(ax, (0.355, 0.185), (0.355, 0.232))
    ax.text(0.363, 0.2085, "text back", fontsize=F(4.7), color=MUTED, ha="left", va="center")
    arrow(ax, (0.405, 0.117), (0.44, 0.117))
    arrow(ax, (0.618, 0.117), (0.653, 0.117))
    # The learning loop, on the left
    box(ax, 0.004, 0.05, 0.19, 0.355, "The loop it kept",
        "After a death or a miss:\n   find the cause, change\n   the tool, one line in the\n   lessons, commit.\nAfter a finished step:\n   actual against target,\n   rescale later targets,\n   rewrite the plan.\nAfter a compaction:\n   reread both manifests.", fc="#fdf6f4", ec="#f5d8cf", title_col="#b3361b")
    arrow(ax, (0.194, 0.33), (0.235, 0.33))
    save(fig, "fig2_setup")


# ---------------------------------------------------------------- Figure 3: the whole run
def fig_run():
    fig = plt.figure(figsize=(6.4, 3.2))
    hs = [0.22, 0.17, 0.25, 0.25]
    axs, top = [], 0.97
    for h in hs:
        axs.append(fig.add_axes([0.11, top - h, 0.87, h - 0.02]))
        top -= h
    a0, a1, a2, a3 = axs
    for a in axs:
        stage_bands(a, labels=(a is a0), y=1.04)
        a.set_xlim(-0.08, WIN + 0.08)
        clean(a)
        a.set_xticks([])
    a0.set_ylim(0, 1)
    marks = [("iron_tools", "Iron tools", "iron_pickaxe", 0.26, 1), ("nether_portal", "Nether portal", "obsidian", 0.26, 1), ("fortress", "Fortress", "nether_bricks", 0.72, 1),
             ("blaze_rods", "First rod", "blaze_rod", 0.26, 1), ("ender_pearls", "First pearl", "ender_pearl", 0.26, 1), ("eyes_of_ender", "Eyes", "ender_eye", 0.26, -1),
             ("stronghold", "Stronghold", "end_portal_frame_top", 0.72, -1), ("the_end", "The End", "end_stone", 0.26, -1), ("ten_crystals", "Ten crystals", "end_crystal", 0.72, 1)]
    for k, label, ic, y, side in marks:
        x = h2(k)
        place_icon(a0, ic, (x, y), zoom=0.36)
        a0.text(x + side * 0.14, y, label, fontsize=F(5.4), fontweight="demibold", va="center", ha="left" if side > 0 else "right")
    place_icon(a0, "dragon_egg", (WIN, 0.26), zoom=0.36)
    a0.text(WIN - 0.14, 0.26, "Dragon", fontsize=F(5.4), fontweight="demibold", va="center", ha="right")
    a1.set_ylim(-0.1, 1.1)
    a1.text(-0.2, 0.5, "opus", fontsize=F(6.5), fontweight="demibold", color=END, ha="right", va="center")
    for adv in D["advancements"]:
        a1.plot(adv["h"], 0.86, marker="D", ms=2.8, color=INK, mew=0, zorder=4)
    for dth in D["deaths"]:
        a1.plot([dth["h"]] * 2, [0.46, 0.72], color=RED, lw=0.9, zorder=4)
    for c in D["commits"]:
        if c["h"] >= 0 and c["h"] <= WIN + 0.02:
            a1.plot([c["h"]] * 2, [0.22, 0.34], color=INK2, lw=0.6, zorder=4)
    for c in D["compactions"]:
        a1.plot(c["h"], 0.08, marker="v", ms=3, color=INK2, mew=0, zorder=4)
    pph = D["programs"]["per_half_hour"]
    a2.bar([b / 2 + 0.25 for b, _ in pph], [n for _, n in pph], width=0.42, color="#a8c7fa", lw=0, zorder=3)
    a2.set_ylim(0, 72)
    a2.text(-0.2, 36, "Programs\nper half hour", fontsize=F(5.6), fontweight="demibold", ha="right", va="center", linespacing=1.2)
    a2.set_yticks([0, 30, 60]); a2.tick_params(axis="y", labelsize=F(5), length=0, pad=1)
    a2.yaxis.tick_right()
    for y in (30, 60):
        a2.axhline(y, color="white", lw=0.5, zorder=1)
    cx = [c[0] for c in D["ctx"]]
    cy = [c[1] / 1000 for c in D["ctx"]]
    a3.plot(cx, cy, color=END, lw=0.7, zorder=3)
    a3.axhline(350, color=INK2, lw=0.5, ls=(0, (2, 2)), zorder=2)
    a3.text(WIN + 0.05, 362, "350k", fontsize=F(5), color=INK2, va="bottom", ha="right")
    a3.set_ylim(0, 430)
    a3.set_yticks([0, 200, 400]); a3.set_yticklabels(["0", "200k", "400k"]); a3.tick_params(axis="y", labelsize=F(5), length=0, pad=1)
    a3.yaxis.tick_right()
    a3.text(-0.2, 215, "Context\n(tokens)", fontsize=F(5.6), fontweight="demibold", ha="right", va="center", linespacing=1.2)
    a3.spines["bottom"].set_visible(True); a3.spines["bottom"].set_color("#dadce0")
    ticks = list(range(0, 10))
    a3.set_xticks(ticks + [WIN])
    a3.set_xticklabels([f"{t} h" for t in ticks[:-1]] + ["", "9 h 07 min"], fontsize=F(5.4))
    a3.get_xticklabels()[-1].set_fontweight("demibold")
    lg = fig.add_axes([0.11, -0.045, 0.87, 0.05]); lg.axis("off"); lg.set_xlim(0, 1); lg.set_ylim(0, 1)
    x = 0.0
    for m, c, t in (("D", INK, "advancement"), ("|", RED, "death"), ("|", INK2, "commit"), ("v", INK2, "compaction")):
        lg.plot(x + 0.006, 0.35, marker=m, ms=3 if m != "|" else 5, color=c, mew=0.8 if m == "|" else 0)
        x += 0.016
        lg.text(x, 0.35, t, fontsize=F(5.3), color=INK2, va="center")
        x += 0.012 * len(t) * 0.55 + 0.03
    lg.text(1, 0.35, "Hours since the first program", fontsize=F(5.5), color=MUTED, ha="right", va="center")
    save(fig, "fig3_run")


# ---------------------------------------------------------------- Figure 4: the inherited library and the reads
READS = [(1.164, "blaze rooms"), (2.412, "blaze_rod"), (2.781, "zombified piglins"), (3.749, "closed room, 8 rods"), (4.493, "warped, pit, pearl"), (4.622, "bunker"),
         (4.624, "pit design"), (5.0, "warped"), (5.017, "pearl, warped"), (5.091, "endermen"), (6.511, "mortar, crystal"), (6.694, "eye, throw, stronghold"),
         (6.778, "dragon, fight pit"), (7.68, "mortar.js"), (7.882, "End arrival"), (7.889, "its progress log"), (7.964, "its fire program"), (7.974, "mortar"), (8.205, "its fight program")]


def fig_stigmergy():
    assert [r[0] for r in READS] == D["inherited_use"]["during_hours"]
    fig = plt.figure(figsize=(6.4, 3.75))
    top = fig.add_axes([0.075, 0.655, 0.905, 0.305])
    bot = fig.add_axes([0.075, 0.355, 0.905, 0.27])
    use = fig.add_axes([0.075, 0.06, 0.905, 0.25])
    for a in (top, bot):
        stage_bands(a, labels=(a is top), y=1.02)
        a.set_xlim(-0.1, WIN + 0.08)
    # Reads, labelled at two heights so that the words do not collide
    top.set_ylim(0, 6)
    labels = [("blaze rooms", 1.164, 1.7, "center"), ("blaze rods", 2.40, 1.7, "right"), ("zombified piglins", 2.79, 1.7, "left"), ("closed room, 8 rods", 3.749, 3.1, "center"),
              ("warped forest, pits,\npearls, bunker", 4.493, 1.7, "center"), ("warped, pearls, endermen", 5.017, 3.7, "center"), ("mortar, crystals,\neyes, dragon pit", 6.65, 1.7, "center"),
              ("mortar.js", 7.68, 3.1, "right"), ("End arrival, fire,\nmortar, its log", 7.90, 3.1, "left"), ("fight program", 8.215, 1.7, "left")]
    for lab, x, y, ha in labels:
        lead = {2.40: 2.412, 2.79: 2.781, 6.65: 6.694, 7.90: 7.974, 8.215: 8.205}.get(x, x)
        top.plot([lead, lead], [0.75, y - 0.12], color=MUTED, lw=0.4, zorder=2)
        top.text(x, y, lab, fontsize=F(4.9), color=INK2, ha=ha, va="bottom", linespacing=1.15, zorder=5)
    for h, _ in READS:
        top.plot([h, h], [0.2, 0.75], color=FIRST, lw=1.0, zorder=4, solid_capstyle="butt")
    top.text(0.06, 5.75, "Each tick: one search of the first player's folder during the run (19)", fontsize=F(5.3), color=INK2, va="top", fontweight="demibold")
    clean(top)
    top.set_xticks([]); top.spines["bottom"].set_visible(False)
    # Library
    cs = [c for c in D["commits"] if c["lib_lines"] > 0 and c["h"] <= WIN + 0.02]
    xs = [max(0, c["h"]) for c in cs] + [WIN]
    same = [c["lib_identical"] for c in cs] + [cs[-1]["lib_identical"]]
    new = [c["lib_lines"] - c["lib_identical"] for c in cs] + [cs[-1]["lib_lines"] - cs[-1]["lib_identical"]]
    bot.fill_between(xs, 0, same, step="post", color="#e7c9a2", lw=0, zorder=2)
    bot.fill_between(xs, same, [a + b for a, b in zip(same, new)], step="post", color=END, lw=0, alpha=0.85, zorder=2)
    bot.set_ylim(0, 4100)
    bot.text(0.25, 1300, f"Lines identical to a line in the first player's library: {cs[-1]['lib_identical']:,} at the win", fontsize=F(5.6), color=INK, fontweight="demibold", va="center")
    bot.text(WIN - 0.05, 3700, f"Lines it wrote: {cs[0]['lib_lines'] - cs[0]['lib_identical']} before its first program, {cs[-1]['lib_lines'] - cs[-1]['lib_identical']} at the win", fontsize=F(5.4), color=INK, ha="right", va="center")
    for s in ("top", "right"):
        bot.spines[s].set_visible(False)
    bot.spines["left"].set_color("#dadce0"); bot.spines["bottom"].set_color("#dadce0")
    bot.set_yticks([0, 1000, 2000, 3000]); bot.set_yticklabels(["0", "1,000", "2,000", "3,000"]); bot.tick_params(axis="y", labelsize=F(5), pad=1)
    bot.set_xticks([])
    bot.text(-0.065, 0.5, "Library lines", transform=bot.transAxes, rotation=90, fontsize=F(5.3), color=INK2, va="center", ha="center", fontweight="demibold")
    # Which tools the programs called, by when each name was first written
    O = D["tool_origin"]["per_hour"]
    SERIES = (("first_player", FIRST), ("before_first_program", "#a59be8"), ("during_run", END))
    use.set_xlim(-0.1, WIN + 0.08); use.set_ylim(0, 100)
    for h_ in range(9):
        c_ = O[str(h_)]
        n_ = sum(c_.values())
        x0, x1 = h_ + 0.03, (WIN if h_ == 8 else h_ + 1) - 0.03
        y_ = 0
        for k_, col_ in SERIES:
            v_ = c_[k_] / n_ * 100
            use.bar(x0, v_, x1 - x0, y_, align="edge", color=col_, lw=0, zorder=3)
            y_ += v_
        if h_ in (0, 4, 8):
            use.text((x0 + x1) / 2, 100 - c_["during_run"] / n_ * 50, f"{c_['during_run'] / n_ * 100:.0f}%", ha="center", va="center", fontsize=F(5.2), color="white", fontweight="demibold", zorder=5)
            use.text((x0 + x1) / 2, c_["first_player"] / n_ * 50, f"{c_['first_player'] / n_ * 100:.0f}%", ha="center", va="center", fontsize=F(5.2), color="white", fontweight="demibold", zorder=5)
    for s_ in ("top", "right"):
        use.spines[s_].set_visible(False)
    use.spines["left"].set_color("#dadce0"); use.spines["bottom"].set_color("#dadce0")
    use.set_yticks([0, 50, 100]); use.set_yticklabels(["0", "50%", "100%"]); use.tick_params(axis="y", labelsize=F(5), pad=1)
    use.set_xticks(list(range(0, 10))); use.set_xticklabels([f"{t} h" for t in range(0, 10)], fontsize=F(5.2))
    use.text(-0.065, 0.5, "Calls in programs", transform=use.transAxes, rotation=90, fontsize=F(5.3), color=INK2, va="center", ha="center", fontweight="demibold")
    x_ = 0.0
    for (k_, col_), lab_ in zip(SERIES, ("The first player's tools", "Written before its first program", "Written during the run")):
        use.add_patch(plt.Rectangle((x_, 1.035), 0.012, 0.06, transform=use.transAxes, color=col_, lw=0, clip_on=False))
        use.text(x_ + 0.017, 1.065, lab_, transform=use.transAxes, fontsize=F(5.3), color=INK, va="center")
        x_ += 0.017 + len(lab_) * 0.0098 + 0.03
    save(fig, "fig4_stigmergy")


# ---------------------------------------------------------------- Figure 5: targets against actuals, and the forecast
TARGETS = [("Stone tools", 6, 6, 4), ("Iron tools", 15, 15, 11), ("Base, food", 35, 35, 50), ("Flint and steel", 35, 35, 65), ("20 mined obsidian", 70, 70, 74), ("Nether portal", 85, 85, 79),
           ("Fortress located", 120, 120, 95), ("6 rods banked", 195, 280, 269), ("Kit rebuilt", None, 385, 396), ("Ender pearls", 315, 420, 420), ("12 eyes", 325, 430, 422), ("Bow, 29 arrows", 360, 465, 427),
           ("Portal room found", 405, 510, 439), ("Forward base", 435, 540, 458), ("The End", 450, 555, 475), ("Ten crystals", 510, 530, 490), ("Ender Dragon", 570, 600, 548)]


def fig_targets():
    fig = plt.figure(figsize=(6.4, 2.75))
    ax = fig.add_axes([0.135, 0.11, 0.455, 0.81])
    n = len(TARGETS)
    caps(ax, -0.28, 1.03, "Its own targets", transform=ax.transAxes)
    for i, (name, first, last, act) in enumerate(TARGETS):
        ax.axhline(i, color=GRID, lw=0.4, zorder=1)
        ax.text(-14, i, name, fontsize=F(5.6), color=INK, ha="right", va="center")
        lo, hi = min(last, act), max(last, act)
        ax.plot([lo, hi], [i, i], color=(RED if act > last else "#7c8ee0"), lw=1.3, zorder=2, solid_capstyle="butt")
        if first is not None and first != last:
            ax.plot(first, i, marker="o", ms=3, mfc="white", mec=MUTED, mew=0.6, zorder=3)
        ax.plot(last, i, marker="o", ms=3.8, mfc="white", mec=INK2, mew=0.8, zorder=4)
        ax.plot(act, i, marker="o", ms=3.8, color=END, mew=0, zorder=5)
    ax.set_ylim(n - 0.4, -0.6); ax.set_xlim(0, 620)
    ax.set_xticks([0, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600]); ax.set_xticklabels(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10 h"], fontsize=F(5.2))
    clean(ax)
    ax.spines["bottom"].set_color("#dadce0")
    ly = 2.2
    ax.plot(340, ly - 1.25, marker="o", ms=3, mfc="white", mec=MUTED, mew=0.6); ax.text(352, ly - 1.25, "first target, before play", fontsize=F(5.1), color=INK2, va="center")
    ax.plot(340, ly - 0.25, marker="o", ms=3.8, mfc="white", mec=INK2, mew=0.8); ax.text(352, ly - 0.25, "last target (rescaled)", fontsize=F(5.1), color=INK2, va="center")
    ax.plot(340, ly + 0.75, marker="o", ms=3.8, color=END, mew=0); ax.text(352, ly + 0.75, "actual", fontsize=F(5.1), color=INK2, va="center")
    # Forecast
    b = fig.add_axes([0.665, 0.2, 0.32, 0.72])
    caps(b, 0.0, 1.03, "Its forecast of the finish", transform=b.transAxes)
    f = D["forecast"]
    xs = [p["h"] for p in f] + [WIN]
    ys = [p["finish_h"] for p in f] + [f[-1]["finish_h"]]
    b.step(xs, ys, where="post", color=END, lw=1.1, zorder=3)
    b.axhline(WIN, color=INK, lw=0.7, ls=(0, (2, 2)), zorder=2)
    b.text(0.1, WIN - 0.1, "actual, 9 h 07 min", fontsize=F(5.2), color=INK, va="top", ha="left")
    b.set_xlim(-0.2, WIN + 0.3); b.set_ylim(8, 13.1)
    b.set_xticks(range(0, 10, 2)); b.set_xticklabels([f"{t} h" for t in range(0, 10, 2)], fontsize=F(5.2))
    b.set_yticks([9, 10, 11, 12, 13]); b.set_yticklabels(["9 h", "10 h", "11 h", "12 h", "13 h"], fontsize=F(5.2))
    for y in (9, 10, 11, 12, 13):
        b.axhline(y, color=GRID, lw=0.4, zorder=0)
    for sp in ("top", "right"):
        b.spines[sp].set_visible(False)
    b.spines["left"].set_color("#dadce0"); b.spines["bottom"].set_color("#dadce0")
    b.text(0.12, f[0]["finish_h"] + 0.09, "first, 9:30", fontsize=F(5.2), color=INK2)
    b.text(5.74, 12.58, "12:30", fontsize=F(5.2), color=INK2, ha="center")
    b.text(1, -0.15, "Hours since the first program", transform=b.transAxes, ha="right", va="top", fontsize=F(5.3), color=MUTED)
    save(fig, "fig5_targets")


# ---------------------------------------------------------------- Figure 6: deaths
def fig_deaths():
    fig = plt.figure(figsize=(6.4, 2.45))
    # Causes, per ten hours
    ax = fig.add_axes([0.105, 0.11, 0.27, 0.8])
    caps(ax, -0.38, 1.03, "By cause, per 10 hours", transform=ax.transAxes)
    c1, c2 = dict(map(tuple, R1["death_causes"])), dict(map(tuple, D["death_causes"]))
    groups = {"Dragon (fall, contact)": "Dragon breath, contact", "Dragon breath": "Dragon breath, contact", "Silverfish": "Other mobs", "Spiders": "Other mobs", "Hoglins": "Other mobs", "Pillagers": "Other mobs",
              "Stalactite": "Falls, stalactite", "Falls": "Falls, stalactite", "Withering": "Withering", "Blazes": "Blazes"}
    agg1, agg2 = {}, {}
    for src, dst in ((c1, agg1), (c2, agg2)):
        for k, v in src.items():
            g = groups.get(k, k)
            dst[g] = dst.get(g, 0) + v
    names = sorted(set(agg1) | set(agg2), key=lambda k: -(agg1.get(k, 0) / R1["win_h"] + agg2.get(k, 0) / WIN))
    for i, k in enumerate(names):
        r1, r2 = agg1.get(k, 0) / R1["win_h"] * 10, agg2.get(k, 0) / WIN * 10
        ax.plot([r1, r2], [i, i], color=GRID, lw=1.1, zorder=1)
        ax.plot(r1, i, marker="o", ms=3.6, color=FIRST, mew=0, zorder=3, clip_on=False)
        ax.plot(r2, i, marker="o", ms=3.6, color=THIS, mew=0, zorder=4, clip_on=False)
        ax.text(-0.3, i, k, fontsize=F(5.3), ha="right", va="center", color=INK)
    ax.set_ylim(len(names) - 0.4, -0.7); ax.set_xlim(0, 5.2)
    ax.set_xticks([0, 1, 2, 3, 4, 5]); ax.tick_params(axis="x", labelsize=F(5), pad=1.5)
    clean(ax); ax.spines["bottom"].set_color("#dadce0")
    # Where
    b = fig.add_axes([0.46, 0.2, 0.2, 0.71])
    caps(b, -0.1, 1.03, "By place, per hour", transform=b.transAxes)
    S = D["death_stats"]
    groups2 = [("Overworld", "overworld"), ("Nether", "the_nether"), ("End", "the_end")]
    for i, (name, k) in enumerate(groups2):
        b.bar(i - 0.19, S["rates_by_dim_run1"][k], width=0.34, color=FIRST, lw=0, zorder=3)
        b.bar(i + 0.19, S["rates_by_dim_run2"][k], width=0.34, color=THIS, lw=0, zorder=3)
        b.text(i - 0.19, S["rates_by_dim_run1"][k] + 0.12, f"{S['rates_by_dim_run1'][k]:.1f}", ha="center", fontsize=F(5), color=INK2)
        b.text(i + 0.19, S["rates_by_dim_run2"][k] + 0.12, f"{S['rates_by_dim_run2'][k]:.1f}", ha="center", fontsize=F(5), color=INK2)
    i = 3
    b.bar(i - 0.19, S["per_h_run1"], width=0.34, color=FIRST, lw=0, zorder=3); b.bar(i + 0.19, S["per_h_run2"], width=0.34, color=THIS, lw=0, zorder=3)
    b.text(i - 0.19, S["per_h_run1"] + 0.12, f"{S['per_h_run1']:.1f}", ha="center", fontsize=F(5), color=INK2, fontweight="demibold")
    b.text(i + 0.19, S["per_h_run2"] + 0.12, f"{S['per_h_run2']:.1f}", ha="center", fontsize=F(5), color=INK2, fontweight="demibold")
    b.set_xticks(range(4)); b.set_xticklabels(["Over-\nworld", "Nether", "End", "All"], fontsize=F(5.2), linespacing=1.0)
    b.set_ylim(0, 8.2); b.set_yticks([0, 4, 8]); b.tick_params(axis="y", labelsize=F(5), pad=1, length=0)
    for s in ("top", "right", "left"):
        b.spines[s].set_visible(False)
    b.spines["bottom"].set_color("#dadce0")
    for y in (4, 8):
        b.axhline(y, color=GRID, lw=0.4, zorder=0)
    # Recovery
    c = fig.add_axes([0.725, 0.2, 0.265, 0.71])
    caps(c, 0, 1.03, "Back at the spot of each death", transform=c.transAxes)
    for run, col, name in ((R1, FIRST, "First run"), (D, THIS, "This run")):
        p = run["places"]
        vals = [v / 60 for v in p["back_s"]]
        tot = p["deaths_with_frame"]
        xs = [0.1] + vals + [600]
        ys = [0] + [(i + 1) / tot * 100 for i in range(len(vals))] + [len(vals) / tot * 100]
        c.step(xs, ys, where="post", color=col, lw=1.1, zorder=3)
    c.set_xscale("log"); c.set_xlim(0.3, 600); c.set_ylim(0, 105)
    c.set_xticks([1, 5, 30, 180, 600]); c.set_xticklabels(["1 min", "5", "30", "3 h", ""], fontsize=F(5.2)); c.minorticks_off()
    c.set_yticks([0, 50, 100]); c.set_yticklabels(["0", "50%", "100%"], fontsize=F(5))
    for s in ("top", "right"):
        c.spines[s].set_visible(False)
    c.spines["left"].set_color("#dadce0"); c.spines["bottom"].set_color("#dadce0")
    c.axvline(5, color=GRID, lw=0.6, zorder=1)
    c.text(62, 97.5, "This run: 15 of 16", fontsize=F(5.2), color=INK, ha="center", va="bottom", fontweight="demibold")
    c.text(62, 24, "First run: 66 of 112", fontsize=F(5.2), color=INK, ha="center", va="top", fontweight="demibold")
    c.text(1, -0.15, "Time after the death (log scale)", transform=c.transAxes, ha="right", va="top", fontsize=F(5.3), color=MUTED)
    # One legend for the three panels
    lg = fig.add_axes([0.34, -0.045, 0.44, 0.05]); lg.axis("off"); lg.set_xlim(-0.03, 1); lg.set_ylim(0, 1)
    lg.plot(0.0, 0.4, marker="o", ms=3.8, color=FIRST, mew=0); lg.text(0.03, 0.4, "First run (60.8 h; 54.7 h by place)", fontsize=F(5.3), color=INK2, va="center")
    lg.plot(0.66, 0.4, marker="o", ms=3.8, color=THIS, mew=0); lg.text(0.69, 0.4, "This run (9.1 h)", fontsize=F(5.3), color=INK2, va="center")
    save(fig, "fig6_deaths")


# ---------------------------------------------------------------- Figure 7: the End
CRYSTALS = [  # x, y, z from the program at t+7:55; group by when each height left the list of living crystals
    (42, 104, 0, 1), (33, 101, 24, 1), (-42, 95, -1, 1), (12, 86, 39, 2), (33, 89, -25, 2), (-34, 98, 24, 2), (-34, 80, -25, 2), (-13, 92, -40, 2), (12, 77, -40, 3), (-13, 83, 39, 4)]


def fig_end():
    fig = plt.figure(figsize=(6.4, 2.65))
    m = fig.add_axes([0.0, 0.05, 0.41, 0.87])
    caps(m, 0.03, 1.02, "The ten crystals, from above", transform=m.transAxes)
    m.set_aspect("equal"); m.set_xlim(-58, 118); m.set_ylim(56, -62)
    m.add_patch(FancyBboxPatch((-56, -61), 172, 115, boxstyle="round,pad=0,rounding_size=6", fc="#f6f5fd", ec="none", zorder=0))
    m.add_patch(plt.Circle((0, 0), 43, fc="none", ec="#e1def7", lw=4, zorder=1))
    m.plot(0, 0, marker="s", ms=4.5, color="#3c4043", zorder=4)
    m.text(5, 6.5, "exit portal", fontsize=F(4.8), color=INK2, ha="left", va="top")
    m.plot(102, 0, marker="s", ms=4.2, color="#202124", zorder=4)
    m.text(102, 5, "arrival,\nits chest", fontsize=F(4.6), color=INK2, ha="center", va="top", linespacing=1.1)
    m.plot(0, -6, marker="^", ms=5, color=NETH, zorder=6)
    m.annotate("the one pit\n(0, 59, -6)", xy=(0, -6), xytext=(0, -25), fontsize=F(5), color=INK, ha="center", va="center", linespacing=1.1, fontweight="demibold",
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5), zorder=7)
    colors = {1: END, 2: "#8a7be0", 3: "#b3a9ec", 4: "#3b2f9a"}
    for x, y, z, g in CRYSTALS:
        m.plot([0, x], [-6, z], color="#d9d5f5", lw=0.5, zorder=1.5)
        m.plot(x, z, marker="o", ms=8, mfc="white", mec=colors[g], mew=1.2, zorder=5)
        place_icon(m, "end_crystal", (x, z), zoom=0.26)
        r = math.hypot(x, z)
        m.text(x * (1 + 10 / r), z * (1 + 10 / r), str(y), fontsize=F(4.6), color=INK2, ha="center", va="center")
    ky = -55
    key = [(1, "8:02", "3 lobbed, 26 s"), (2, "8:05", "5 more lobbed"), (3, "8:07", "1 direct peek"), (4, "8:10", "1 caged, lobbed")]
    for j, (g, t, what) in enumerate(key):
        yy = ky + 7.2 * j
        m.plot(52, yy, marker="o", ms=4.5, mfc="white", mec=colors[g], mew=1.1)
        m.text(56.5, yy, f"{t}  {what}", fontsize=F(4.8), color=INK2, va="center")
    m.text(114, 51, "Small numbers:\nthe height of\neach crystal", fontsize=F(4.5), color=MUTED, ha="right", va="bottom", linespacing=1.1)
    m.axis("off")
    b = fig.add_axes([0.5, 0.17, 0.49, 0.72])
    caps(b, 0.0, 1.05, "The dragon's health", transform=b.transAxes)
    pts = [(TEN, 200.0)] + [(x["h"], x["hp"]) for x in D["dragon"] if x["h"] >= TEN]
    b.step([p[0] for p in pts], [p[1] for p in pts], where="post", color=END, lw=1.0, zorder=3)
    b.fill_between([p[0] for p in pts], [p[1] for p in pts], step="post", color="#ece9fb", lw=0, zorder=2)
    for dth in D["deaths"]:
        if dth["h"] >= TEN:
            b.plot([dth["h"]] * 2, [-14, -4], color=RED, lw=0.9, clip_on=False, zorder=4)
    b.text(TEN + 0.005, -9, "deaths", fontsize=F(4.8), color=RED, va="center", ha="left")
    b.annotate("killed at 9:07:38,\n26 HP in one perch, 2 s", xy=(WIN, 12), xytext=(8.72, 25), fontsize=F(5.1), color=INK, ha="left", va="center", linespacing=1.15, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    b.annotate("56 HP in one perch", xy=(8.885, 90), xytext=(8.60, 62), fontsize=F(5.1), color=INK2, ha="center", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    b.annotate("first melee, from the pit", xy=(8.27, 180), xytext=(8.33, 196), fontsize=F(5.1), color=INK2, ha="left", va="center", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    b.set_xlim(TEN, WIN + 0.01); b.set_ylim(-16, 210)
    ticks = [TEN, 8.5, 8.75, 9.0, WIN]
    b.set_xticks(ticks); b.set_xticklabels(["8:10", "8:30", "8:45", "9:00", "9:07"], fontsize=F(5.2))
    b.set_yticks([0, 100, 200]); b.tick_params(axis="y", labelsize=F(5))
    for s in ("top", "right"):
        b.spines[s].set_visible(False)
    b.spines["left"].set_color("#dadce0"); b.spines["bottom"].set_color("#dadce0")
    b.spines["bottom"].set_position(("data", -16))
    b.text(1, -0.14, "Time since the first program", transform=b.transAxes, ha="right", va="top", fontsize=F(5.3), color=MUTED)
    save(fig, "fig7_end")


if __name__ == "__main__":
    (FIG / "preview").mkdir(parents=True, exist_ok=True)
    fig_steps()
    fig_setup()
    fig_run()
    fig_stigmergy()
    fig_targets()
    fig_deaths()
    fig_end()
    print("figures written")
