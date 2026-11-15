#!/usr/bin/env python3
"""Draw the second team-run preprint's figures from preprint-team2/data/team2.json.

    <python with matplotlib + pillow> preprint-team2/scripts/make_figures.py   -> preprint-team2/figures/*.pdf

Same style as the earlier preprints. Item icons are from the Pixel Perfection texture pack
(CC BY-SA 4.0, in ../preprint/figures/icons/). Seconds are on the official clock, from the agents' first spawn.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Patch
from matplotlib.patheffects import withStroke
from PIL import Image

PRE = Path(__file__).resolve().parent.parent
FIG = PRE / "figures"
ICONS = PRE.parent / "preprint" / "figures" / "icons"
D = json.loads((PRE / "data" / "team2.json").read_text())
E = D["earlier"]
WIN = D["clock"]["official_s"] / 60  # minutes
M = {k: v["s"] / 60 for k, v in D["milestones"].items()}
BY = {k: v["by"] for k, v in D["milestones"].items()}
LAST = D["dragon"]["crystals"]["all_dead_said_s"] / 60
A1, A2 = "FableFox", "FableFire"

plt.rcParams.update({
    "font.family": "Avenir Next", "font.size": 7, "pdf.fonttype": 42, "axes.linewidth": 0.6,
    "axes.edgecolor": "#c9ccd1", "xtick.color": "#5f6368", "ytick.color": "#5f6368",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.labelcolor": "#5f6368", "text.color": "#1f1f1f",
})
HALO = [withStroke(linewidth=1.6, foreground="white")]
F = lambda size: max(6.0, size * 1.12)
INK, INK2, MUTED = "#1f1f1f", "#5f6368", "#9aa0a6"
RED = "#d93025"
OVER, NETH, END = "#1baf7a", "#eb6834", "#6250d6"
C4, C2, C1, GREY = "#6250d6", "#0f8fb3", "#c4761c", "#7a8087"
AG_BAR, PP_BAR = "#6b7178", "#c0c5cb"
STAGES = [("OVERWORLD", 0, M["nether_portal"], "#edf6ea", "#3c8a3a"), ("NETHER AND BACK", M["nether_portal"], M["the_end"], "#fcefe9", "#c5462b"),
          ("THE END", M["the_end"], WIN, "#f0effa", "#5b4fc4")]
STEPS = [("stone_tools", "Stone tools", "stone_pickaxe"), ("iron_tools", "Iron tools", "iron_pickaxe"), ("bucket", "Bucket", "bucket"),
         ("flint_and_steel", "Flint and steel", "flint_and_steel"), ("nether_portal", "Nether portal", "obsidian"), ("fortress", "Nether fortress", "nether_bricks"),
         ("ender_pearls", "Ender pearls", "ender_pearl"), ("blaze_rods", "Blaze rods", "blaze_rod"),
         ("eyes_of_ender", "Eyes of Ender", "ender_eye"), ("stronghold", "Stronghold", "end_portal_frame_top"), ("the_end", "The End", "end_stone"),
         ("ten_crystals", "Ten crystals", "end_crystal"), ("dragon", "Ender Dragon", "dragon_egg")]


def ms(run, k):
    """Minutes to a step."""
    if run == "this":
        return LAST if k == "ten_crystals" else M.get(k)
    if run == "run5" and k == "ten_crystals":
        return E["run5"]["ten_crystals_s"] / 60
    v = E[run]["milestones"].get(k)
    return None if v is None else v / 60


def hm(m):
    if m is None:
        return "--"
    m = int(m + 1e-6)
    return f"{m // 60}:{m % 60:02d}"


def place_icon(ax, name, xy, zoom=0.55, coords="data"):
    im = Image.open(ICONS / f"{name}.png").convert("RGBA")
    ax.add_artist(AnnotationBbox(OffsetImage(im, zoom=zoom, interpolation="nearest", resample=False), xy, xycoords=coords, frameon=False, pad=0, zorder=6))


def stage_bands(ax, labels=True, y=1.0):
    for name, a, b, band, col in STAGES:
        ax.axvspan(a, b, color=band, zorder=0, lw=0)
        if labels:
            ax.text(a + 0.6, y, name, ha="left", transform=ax.get_xaxis_transform(), fontsize=F(5.2), color=col, fontweight="demibold", va="bottom")


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


def xticks_min(ax, last_label):
    ax.set_xticks([0, 20, 40, 60, 80, WIN])
    ax.set_xticklabels(["0:00", "0:20", "0:40", "1:00", "1:20", last_label], fontsize=F(5.4))
    ax.get_xticklabels()[-1].set_fontweight("demibold")


# ---------------------------------------------------------------- Figure 1: step by step, against the earlier runs
def fig_steps():
    fig = plt.figure(figsize=(6.4, 2.9))
    ax = fig.add_axes([0.185, 0.095, 0.40, 0.825])
    n = len(STEPS)
    for a, b, col in [(0, 4, "#edf6ea"), (5, 9, "#fcefe9"), (10, 12, "#f0effa")]:
        ax.axhspan(a - 0.5, b + 0.5, color=col, lw=0, zorder=0)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xlim(-4, 300)
    for run, col, lw, z in (("run5", C2, 1.0, 2), ("team1", C4, 1.0, 3), ("this", INK, 1.6, 4)):
        pts = [(ms(run, k), i) for i, (k, _, _) in enumerate(STEPS) if ms(run, k) is not None]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.plot(xs, ys, color=col, lw=lw, zorder=z, solid_joinstyle="round")
        ax.plot(xs, ys, ls="none", marker="o", ms=2.7 if run == "this" else 2.0, color=col, mew=0, zorder=z + 0.5)
    ax.text(ms("this", "dragon") + 5, 12.0, "This run", fontsize=F(6), fontweight="demibold", color=INK, ha="left", va="center", path_effects=HALO)
    ax.text(ms("team1", "dragon") - 4, 11.0, "First team run", fontsize=F(6), fontweight="demibold", color=C4, ha="right", va="center", path_effects=HALO)
    ax.text(ms("run5", "the_end") - 6, 9.0, "Run 5 (solo)", fontsize=F(6), fontweight="demibold", color=C2, ha="right", va="center", path_effects=HALO)
    for k, (key, label, ic) in enumerate(STEPS):
        place_icon(ax, ic, (-0.022, k), zoom=0.34, coords=ax.get_yaxis_transform())
        ax.text(-0.05, k, label, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=F(5.8), fontweight="demibold", color=INK)
        by = "both agents*" if key == "ten_crystals" else BY.get(key, "")
        cols = ((1.13, hm(ms("this", key)), True, "right"), (1.165, by, False, "left"), (1.60, hm(ms("team1", key)), False, "right"),
                (1.75, hm(ms("run5", key)), False, "right"), (1.93, hm(ms("gemini_team", key)), False, "right"))
        for x, t, bold, ha in cols:
            ax.text(x, k, t, transform=ax.get_yaxis_transform(), ha=ha, va="center", fontsize=F(5.6), color=INK if bold else INK2, fontweight="demibold" if bold else "normal")
    for x, t, ha in ((1.13, "This\nrun", "right"), (1.165, "First\nby", "left"), (1.60, "First\nteam run", "right"), (1.75, "Run\n5", "right"), (1.93, "Gemini\nteam", "right")):
        ax.text(x, -0.62, t, transform=ax.get_yaxis_transform(), ha=ha, va="bottom", fontsize=F(5.2), color=MUTED, fontweight="demibold", linespacing=1.0)
    caps(ax, 0.0, 1.035, "Step by step", transform=ax.transAxes)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#dadce0")
    ax.set_yticks([])
    ax.set_xticks([0, 60, 120, 180, 240])
    ax.set_xticklabels(["0 h", "1 h", "2 h", "3 h", "4 h"])
    ax.tick_params(axis="x", labelsize=F(5.2), pad=1.5)
    save(fig, "fig1_steps")


# ---------------------------------------------------------------- Figure 2: the whole run, player by player
def halves(pairs, per=2):
    out = {}
    for b, n in pairs:
        out[b // per] = out.get(b // per, 0) + n
    return out


def fig_run():
    fig = plt.figure(figsize=(6.4, 3.9))
    hs = [0.16, 0.085, 0.085, 0.085, 0.085, 0.19, 0.19]
    axs, top = [], 0.97
    for h in hs:
        axs.append(fig.add_axes([0.135, top - h, 0.83, h - 0.016]))
        top -= h
    a0, aF, aV, aP1, aP2, aProg, aChat = axs
    for a in axs:
        stage_bands(a, labels=(a is a0), y=1.04)
        a.set_xlim(-1, WIN + 1)
        clean(a)
        a.set_xticks([])
    a0.set_ylim(0, 1)
    marks = [("iron_tools", "Iron", "iron_pickaxe", 0.72, "left"), ("nether_portal", "Portal", "obsidian", 0.26, "right"), ("blaze_rods", "Rods", "blaze_rod", 0.72, "left"),
             ("eyes_of_ender", "Eyes", "ender_eye", 0.26, "left"), ("stronghold", "Stronghold", "end_portal_frame_top", 0.72, "left"), ("the_end", "End", "end_stone", 0.26, "right")]
    for k, label, ic, y, ha in marks:
        place_icon(a0, ic, (M[k], y), zoom=0.36)
        a0.text(M[k] + (1.6 if ha == "left" else -1.6), y, label, fontsize=F(5.4), fontweight="demibold", va="center", ha=ha)
    place_icon(a0, "end_crystal", (LAST, 0.72), zoom=0.36)
    a0.text(LAST - 1.6, 0.72, "Crystals", fontsize=F(5.4), fontweight="demibold", va="center", ha="right")
    place_icon(a0, "dragon_egg", (WIN, 0.26), zoom=0.36)
    a0.text(WIN - 1.6, 0.26, "Dragon", fontsize=F(5.4), fontweight="demibold", va="center", ha="right")
    dcol = {"overworld": OVER, "the_nether": NETH, "the_end": END}
    for a, name in ((aF, A1), (aV, A2)):
        a.set_ylim(0, 1)
        ch = [c for c in D["dims"][name] if c["s"] / 60 < WIN] + [{"s": WIN * 60, "dim": None}]
        a.barh(0.42, ch[0]["s"] / 60, left=0, height=0.34, color=OVER, lw=0, zorder=3)
        for u, v in zip(ch, ch[1:]):
            a.barh(0.42, v["s"] / 60 - u["s"] / 60, left=u["s"] / 60, height=0.34, color=dcol[u["dim"]], lw=0, zorder=3)
        for x in D["advancements"]:
            if x["by"] == name:
                a.plot(x["s"] / 60, 0.86, marker="D", ms=2.6, color=INK, mew=0, zorder=4)
        for d in D["deaths"]:
            if d["player"] == name:
                a.plot([d["s"] / 60] * 2, [0.18, 0.68], color=RED, lw=1.2, zorder=5)
        for c in D["compactions"]:
            if c["agent"] == name:
                a.plot(c["s"] / 60, 0.08, marker="v", ms=3, color=INK2, mew=0, zorder=4)
        a.text(-2, 0.45, name, fontsize=F(6.2), fontweight="demibold", color=INK, ha="right", va="center")
    for a, lab in ((aP1, "Human 1"), (aP2, "Human 2")):
        a.set_ylim(0, 1)
        for s, e in D["presence"][lab]["spans"]:
            a.barh(0.42, (e - s) / 60, left=s / 60, height=0.34, color="#d7dadf", lw=0, zorder=3)
        for x in D["advancements"]:
            if x["by"] == lab:
                a.plot(x["s"] / 60, 0.86, marker="D", ms=2.6, color=INK, mew=0, zorder=4)
        for d in D["deaths"]:
            if d["player"] == lab:
                a.plot([d["s"] / 60] * 2, [0.18, 0.68], color=RED, lw=0.9, zorder=5)
        a.text(-2, 0.45, lab, fontsize=F(6.2), fontweight="demibold", color=INK2, ha="right", va="center")
    pf, pv = dict(D["programs"][A1]["per_quarter_hour"]), dict(D["programs"][A2]["per_quarter_hour"])
    for b in sorted(set(pf) | set(pv)):
        lo, hi = b * 15 + 0.4, min(b * 15 + 14.6, WIN)
        aProg.bar(lo, pf.get(b, 0) + pv.get(b, 0), width=hi - lo, align="edge", color=AG_BAR, lw=0, zorder=3)
    aProg.set_ylim(0, 48)
    aProg.text(-2, 24, "Programs per\nquarter hour", fontsize=F(5.6), fontweight="demibold", ha="right", va="center", linespacing=1.2)
    cq = D["chat"]["per_quarter_hour"]
    cf, cv, cp1, cp2 = (dict(cq.get(k, [])) for k in (A1, A2, "Human 1", "Human 2"))
    for b in sorted(set(cf) | set(cv) | set(cp1) | set(cp2)):
        lo, hi = b * 15 + 0.4, min(b * 15 + 14.6, WIN)
        g_, p_ = cf.get(b, 0) + cv.get(b, 0), cp1.get(b, 0) + cp2.get(b, 0)
        aChat.bar(lo, g_, width=hi - lo, align="edge", color=AG_BAR, lw=0, zorder=3)
        aChat.bar(lo, p_, bottom=g_ + 0.5, width=hi - lo, align="edge", color=PP_BAR, lw=0, zorder=3)
        if b == 1:
            aChat.text(lo + 0.6, g_ / 2, "agents", fontsize=F(5.2), color="white", fontweight="demibold", va="center", zorder=5)
            aChat.text(lo + 0.6, g_ + 0.5 + p_ / 2, "people", fontsize=F(5.2), color=INK, fontweight="demibold", va="center", zorder=5)
    aChat.set_ylim(0, 48)
    aChat.text(-2, 24, "Chat lines per\nquarter hour", fontsize=F(5.6), fontweight="demibold", ha="right", va="center", linespacing=1.2)
    for a, ticks in ((aProg, (15, 30, 45)), (aChat, (15, 30, 45))):
        a.set_yticks(ticks)
        a.tick_params(axis="y", labelsize=F(5), length=0, pad=1)
        a.yaxis.tick_right()
        for y in ticks:
            a.axhline(y, color="white", lw=0.5, zorder=4)
    aChat.spines["bottom"].set_visible(True)
    aChat.spines["bottom"].set_color("#dadce0")
    xticks_min(aChat, "1:43")
    hd = [Line2D([], [], marker="D", ms=3, color=INK, ls="none", mew=0), Line2D([], [], marker="|", ms=6, color=RED, ls="none", mew=1.2),
          Line2D([], [], marker="v", ms=3.5, color=INK2, ls="none", mew=0)]
    hd += [Patch(color=c, lw=0) for c in (OVER, NETH, END, "#d7dadf")]
    lb = ["advancement", "death", "compaction", "Overworld", "Nether", "End", "person on the server"]
    fig.legend(hd, lb, loc="upper center", bbox_to_anchor=(0.55, 0.005), ncol=7, frameon=False, fontsize=F(5.3), handlelength=1.0, handleheight=0.8,
               handletextpad=0.4, columnspacing=1.1, labelcolor=INK2)
    save(fig, "fig2_run")


# ---------------------------------------------------------------- Figure 3: the dragon's health
def fig_dragon():
    fig = plt.figure(figsize=(6.4, 2.4))
    ax = fig.add_axes([0.075, 0.15, 0.9, 0.72])
    x0 = M["the_end"] - 0.5
    ax.set_xlim(x0, WIN + 0.6)
    ax.set_ylim(-6, 222)
    ax.axvspan(x0, WIN + 0.6, color="#f0effa", lw=0, zorder=0)
    curve = [(s / 60, hp) for s, hp in D["dragon"]["curve"]]
    xs = [x0] + [c[0] for c in curve] + [WIN + 0.3]
    ys = [200.0] + [c[1] for c in curve] + [0]
    ax.step(xs, ys, where="post", color=INK2, lw=0.7, zorder=3)
    prev = 200.0
    for t, hp in curve:
        fox = abs(prev - hp) < 1.6 and 139 < hp < 143
        crystal = abs(prev - hp - 10) < 0.01 and hp == 190
        ax.plot([t, t], [prev, hp], color=C2 if fox else (GREY if crystal else C1), lw=3.0, solid_capstyle="butt", zorder=4)
        prev = hp
    place_icon(ax, "end_crystal", (LAST, 190), zoom=0.3)
    ax.text(LAST + 0.25, 204, "all ten crystals gone", fontsize=F(5.2), color=INK2, ha="left", va="center")
    ax.annotate("FableFox's two sword hits (3.0)", xy=(98.5, 141), xytext=(96.2, 118), fontsize=F(5.2), color=C2, ha="right", va="center",
                arrowprops=dict(arrowstyle="-", color=C2, lw=0.6))
    ax.text(100.8, 112, "drops no agent\nprogram caused", fontsize=F(5.2), color=C1, ha="left", va="center", linespacing=1.1)
    for name, y in ((A1, 216), (A2, 209)):
        t_in = next(c["s"] for c in D["dims"][name] if c["dim"] == "the_end") / 60
        ax.plot([t_in, WIN], [y, y], color=END, lw=2.2, solid_capstyle="butt", zorder=3)
        ax.text(t_in - 0.15, y, name + " in the End", fontsize=F(5.0), color=INK2, ha="right", va="center")
    for d in D["deaths"]:
        if d["s"] / 60 >= x0:
            ax.plot([d["s"] / 60] * 2, [-6, 8], color=RED, lw=1.0, zorder=5)
    ax.text(x0 + 0.15, 14, "red ticks: the people's deaths", fontsize=F(5.0), color=RED, ha="left", va="center")
    place_icon(ax, "dragon_egg", (WIN, 0), zoom=0.3)
    ticks = [85, 90, 95, 100]
    ax.set_xticks(ticks + [WIN])
    ax.set_xticklabels(["1:25", "1:30", "1:35", "1:40", "1:43"], fontsize=F(5.4))
    ax.get_xticklabels()[-1].set_fontweight("demibold")
    ax.set_yticks([0, 50, 100, 150, 200])
    ax.tick_params(axis="y", labelsize=F(5.2), length=0, pad=1)
    for y in (50, 100, 150, 200):
        ax.axhline(y, color="white", lw=0.5, zorder=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#dadce0")
    ax.spines["bottom"].set_color("#dadce0")
    caps(ax, 0.0, 1.06, "The dragon's health, as the agents' programs read it", transform=ax.transAxes)
    save(fig, "fig3_dragon")


# ---------------------------------------------------------------- Figure 4: context size through the run
def fig_context():
    fig, axes = plt.subplots(3, 1, figsize=(6.4, 3.6), sharex=True, gridspec_kw={"height_ratios": [0.22, 0.22, 2.0], "hspace": 0.1})
    for ax, name, col in ((axes[0], A1, C2), (axes[1], A2, C4)):
        for a, b in D["programs"][name]["spans"]:
            ax.axvspan(a / 60, b / 60, color=col, lw=0, alpha=0.85)
        ax.set_yticks([])
        ax.set_ylabel(name + "\nprogram running", rotation=0, ha="right", va="center", fontsize=F(5.4), color=INK2)
        for s in ("top", "right", "left", "bottom"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="x", length=0)
    ax = axes[2]
    for name, col in ((A1, C2), (A2, C4)):
        ctx = [(c / 60, t / 1000) for c, t in D["context"][name] if c <= D["clock"]["official_s"] + 60]
        ax.plot(*zip(*ctx), color=col, lw=1.1, drawstyle="steps-post", label=name)
    ax.axhline(350, color=GREY, lw=0.7, ls="--")
    ax.text(1, 357, "compaction set for the run: 350,000 tokens", fontsize=F(5.4), color=INK2)
    for c, (col, dy) in zip(D["compactions"], ((C2, 150), (C4, 85))):
        ax.axvline(c["s"] / 60, color=col, lw=0.7, ls=":")
        ax.text(c["s"] / 60 - 0.8, dy, f"{c['agent']} compacts at {hm(c['s'] / 60)}\n{c['pre'] / 1000:.0f}k to {c['post'] / 1000:.0f}k tokens", fontsize=F(5.4), color=col, va="top", ha="right")
    ax.axvline(WIN, color=INK, lw=0.9)
    ax.text(WIN - 0.8, 30, "win 1:43:02", ha="right", fontsize=F(5.6), color=INK, fontweight="demibold")
    ax.set_ylim(0, 395)
    ax.set_xlim(0, WIN + 2)
    ax.set_ylabel("Tokens in the model's context\n(thousands, each request)", fontsize=F(5.6))
    ax.set_xlabel("Official clock (h:mm after the first spawn)", fontsize=F(5.6))
    xticks_min(ax, "1:43")
    ax.tick_params(axis="y", labelsize=F(5.2))
    ax.grid(color="#eef0f2", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=F(5.8), bbox_to_anchor=(0.0, 0.9))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "fig4_context")


# ---------------------------------------------------------------- Figure 5: the 5-hour usage window
def fig_usage():
    fig, ax = plt.subplots(figsize=(6.4, 2.5))
    rows = sorted((r for a in (A1, A2) for r in D["limits"][a] if r["five_hour"] is not None), key=lambda r: r["s"])
    pts, top = [], 0
    for r in rows:  # the two sessions report one shared window; keep it non-decreasing
        top = max(top, r["five_hour"])
        pts.append((r["s"] / 60, 100 * top))
    ax.plot(*zip(*pts), color=C4, lw=1.4, drawstyle="steps-post", label="5-hour window (both agents share it)")
    ax.fill_between([p[0] for p in pts], [p[1] for p in pts], step="post", color=C4, alpha=0.08, lw=0)
    wk, top = [], 0
    for r in rows:
        top = max(top, r["seven_day"])
        wk.append((r["s"] / 60, 100 * top))
    ax.plot(*zip(*wk), color=OVER, lw=1.1, drawstyle="steps-post", label="7-day window")
    ax.axhline(100, color=RED, lw=0.8, ls="--")
    ax.text(1, 103, "limit: requests refused", color=RED, fontsize=F(5.6))
    at_win = [p for p in pts if p[0] <= WIN][-1]
    ax.annotate(f"{at_win[1]:.0f}% at the win", xy=(WIN, at_win[1]), xytext=(WIN - 22, at_win[1] + 9), fontsize=F(5.8), color=C4,
                arrowprops=dict(arrowstyle="-", color=C4, lw=0.6))
    ax.text(WIN - 12, wk[-1][1] - 9, f"7-day: {wk[0][1]:.0f}% to {wk[-1][1]:.0f}%", fontsize=F(5.6), color=OVER, ha="right")
    ax.axvline(WIN, color=INK, lw=0.9)
    ax.text(WIN + 0.5, 50, "win\n1:43:02", ha="left", fontsize=F(5.6), color=INK, fontweight="demibold", va="center")
    reset = rows[0]["five_hour_resets_s"] / 60
    ax.text(WIN + 0.5, 20, f"window\nresets\nat {hm(reset)}", ha="left", fontsize=F(5.2), color=INK2, va="center", linespacing=1.1)
    ax.set_ylim(0, 115)
    ax.set_xlim(0, WIN + 9)
    ax.set_ylabel("Share of the usage window (%)", fontsize=F(5.6))
    ax.set_xlabel("Official clock (h:mm after the first spawn)", fontsize=F(5.6))
    xticks_min(ax, "1:43")
    ax.tick_params(axis="y", labelsize=F(5.2))
    ax.grid(color="#eef0f2", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=F(5.8), bbox_to_anchor=(0.0, 0.88))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "fig5_usage")


if __name__ == "__main__":
    (FIG / "preview").mkdir(parents=True, exist_ok=True)
    fig_steps()
    fig_run()
    fig_dragon()
    fig_context()
    fig_usage()
    print("figures written")
