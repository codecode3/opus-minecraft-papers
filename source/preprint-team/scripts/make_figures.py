#!/usr/bin/env python3
"""Draw the team-run preprint's figures from preprint-team/data/team.json.

    <python with matplotlib + pillow> preprint-team/scripts/make_figures.py   -> preprint-team/figures/*.pdf

Same style as the earlier preprints: pastel bands for the stages, small letter-spaced labels, item icons
from the Pixel Perfection texture pack (CC BY-SA 4.0, in ../preprint/figures/icons/). The damage sources'
colours were checked with the dataviz validator in the order they are drawn (Foxglen, Voidmoth, beds,
people's hits); unattributed is a neutral grey, never beside the beds, and every bar is labelled.
Hours are on the official clock, from the agents' first spawn.
"""
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patheffects import withStroke
from PIL import Image

PRE = Path(__file__).resolve().parent.parent
FIG = PRE / "figures"
ICONS = PRE.parent / "preprint" / "figures" / "icons"
D = json.loads((PRE / "data" / "team.json").read_text())
E = D["earlier"]
WIN = D["clock"]["official_h"]
M = {k: v["h"] for k, v in D["milestones"].items()}
BY = {k: v["by"] for k, v in D["milestones"].items()}
LAST = D["crystals"]["last_crystal_h"]
SPAWN = datetime.fromisoformat(D["clock"]["spawn_utc"])
FOX, VOID = "FoxglenOpus", "VoidmothOpus"

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
C4, C2, C1, C3, GREY = "#6250d6", "#0f8fb3", "#c4761c", "#c23b7a", "#7a8087"
SRC = {"FoxglenOpus": C2, "VoidmothOpus": C4, "explosion": C3, "people": C1, "unattributed": GREY}
AG_BAR, PP_BAR = "#6b7178", "#c0c5cb"  # Figure 2's count panels stay neutral: its colours are the dimensions
STAGES = [("OVERWORLD", 0, M["nether_portal"], "#edf6ea", "#3c8a3a"), ("NETHER AND BACK", M["nether_portal"], M["the_end"], "#fcefe9", "#c5462b"),
          ("THE END", M["the_end"], WIN, "#f0effa", "#5b4fc4")]
STEPS = [("stone_tools", "Stone tools", "stone_pickaxe"), ("iron_tools", "Iron tools", "iron_pickaxe"), ("bucket", "Bucket", "bucket"),
         ("flint_and_steel", "Flint and steel", "flint_and_steel"), ("nether_portal", "Nether portal", "obsidian"), ("ender_pearls", "Ender pearls", "ender_pearl"),
         ("fortress", "Nether fortress", "nether_bricks"), ("blaze_rods", "Blaze rods", "blaze_rod"),
         ("eyes_of_ender", "Eyes of Ender", "ender_eye"), ("stronghold", "Stronghold", "end_portal_frame_top"), ("the_end", "The End", "end_stone"),
         ("ten_crystals", "Ten crystals", "end_crystal"), ("dragon", "Ender Dragon", "dragon_egg")]
SHORT = {FOX: "Foxglen", VOID: "Voidmoth"}


def H(iso):
    return (datetime.fromisoformat(iso) - SPAWN).total_seconds() / 3600


def hclock(c):
    h, m, s = map(int, c.split(":"))
    return h + m / 60 + s / 3600


def ms(run, k):
    if run == "this":
        return LAST if k == "ten_crystals" else M.get(k)
    if k == "ten_crystals":
        return E[run].get("ten_crystals_h")
    return E[run]["milestones"].get(k)


def ht(k):
    return E["gemini_team"]["milestones_min"][k] / 60


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
            ax.text(a + 0.03, y, name, ha="left", transform=ax.get_xaxis_transform(), fontsize=F(5.2), color=col, fontweight="demibold", va="bottom")


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


def who_short(k):
    if k == "ten_crystals":
        return "shared"
    b = BY.get(k, "")
    return SHORT.get(b, b)


# ---------------------------------------------------------------- Figure 1: the team run and the solo runs, step by step
def fig_steps():
    fig = plt.figure(figsize=(6.4, 2.9))
    ax = fig.add_axes([0.185, 0.095, 0.44, 0.825])
    n = len(STEPS)
    for a, b, col in [(0, 4, "#edf6ea"), (5, 9, "#fcefe9"), (10, 12, "#f0effa")]:
        ax.axhspan(a - 0.5, b + 0.5, color=col, lw=0, zorder=0)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xlim(-0.12, 10.15)
    for run, col, lw, z in (("run2", C2, 1.0, 2), ("run4", C4, 1.0, 3), ("this", INK, 1.6, 4)):
        pts = [(ms(run, k), i) for i, (k, _, _) in enumerate(STEPS) if ms(run, k) is not None]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.plot(xs, ys, color=col, lw=lw, zorder=z, solid_joinstyle="round")
        ax.plot(xs, ys, ls="none", marker="o", ms=2.7 if run == "this" else 2.0, color=col, mew=0, zorder=z + 0.5)
    for run, col, t in (("this", INK, "Team run"), ("run4", C4, "Run 4"), ("run2", C2, "Run 2")):
        ax.text(ms(run, "dragon") + 0.13, 12.0, t, fontsize=F(6), fontweight="demibold", color=col, ha="left", va="center", path_effects=HALO)
    for k, (key, label, ic) in enumerate(STEPS):
        place_icon(ax, ic, (-0.022, k), zoom=0.34, coords=ax.get_yaxis_transform())
        ax.text(-0.05, k, label, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=F(5.8), fontweight="demibold", color=INK)
        cols = ((1.13, hm(ms("this", key)), True, "right"), (1.165, who_short(key), False, "left"), (1.47, hm(ms("run4", key)), False, "right"),
                (1.61, hm(ms("run2", key)), False, "right"), (1.78, hm(ht(key)), False, "right"))
        for x, t, bold, ha in cols:
            ax.text(x, k, t, transform=ax.get_yaxis_transform(), ha=ha, va="center", fontsize=F(5.6), color=INK if bold else INK2, fontweight="demibold" if bold else "normal")
    for x, t, ha in ((1.13, "Team\nrun", "right"), (1.165, "First\nby", "left"), (1.47, "Run\n4", "right"), (1.61, "Run\n2", "right"), (1.78, "Gemini\nteam", "right")):
        ax.text(x, -0.62, t, transform=ax.get_yaxis_transform(), ha=ha, va="bottom", fontsize=F(5.2), color=MUTED, fontweight="demibold", linespacing=1.0)
    caps(ax, 0.0, 1.035, "Step by step", transform=ax.transAxes)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#dadce0")
    ax.set_yticks([])
    ax.set_xticks([0, 2, 4, 6, 8])
    ax.set_xticklabels(["0 h", "2 h", "4 h", "6 h", "8 h"])
    ax.tick_params(axis="x", labelsize=F(5.2), pad=1.5)
    save(fig, "fig1_steps")


# ---------------------------------------------------------------- Figure 2: the whole run, player by player
def half_hours(pairs):
    out = {}
    for b, n in pairs:
        out[b // 2] = out.get(b // 2, 0) + n
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
        a.set_xlim(-0.05, WIN + 0.05)
        clean(a)
        a.set_xticks([])
    a0.set_ylim(0, 1)
    marks = [("iron_tools", "Iron", "iron_pickaxe", 0.72), ("nether_portal", "Portal", "obsidian", 0.26), ("blaze_rods", "First rods", "blaze_rod", 0.72),
             ("eyes_of_ender", "Eyes", "ender_eye", 0.26), ("the_end", "Stronghold, End", "end_stone", 0.72)]
    for k, label, ic, y in marks:
        place_icon(a0, ic, (M[k], y), zoom=0.36)
        a0.text(M[k] + 0.08, y, label, fontsize=F(5.4), fontweight="demibold", va="center", ha="left")
    place_icon(a0, "blaze_rod", (1.70, 0.26), zoom=0.36)
    a0.text(1.78, 0.26, "7 rods despawn", fontsize=F(5.4), fontweight="demibold", va="center", ha="left", color=RED)
    place_icon(a0, "end_crystal", (LAST, 0.26), zoom=0.36)
    a0.text(LAST + 0.08, 0.26, "Last crystal", fontsize=F(5.4), fontweight="demibold", va="center", ha="left")
    place_icon(a0, "dragon_egg", (WIN, 0.72), zoom=0.36)
    a0.text(WIN - 0.08, 0.72, "Dragon", fontsize=F(5.4), fontweight="demibold", va="center", ha="right")
    dcol = {"overworld": OVER, "the_nether": NETH, "the_end": END}
    deaths = D["deaths"]
    adv = D["advancements"]
    for a, name, lab in ((aF, FOX, "Foxglen"), (aV, VOID, "Voidmoth")):
        a.set_ylim(0, 1)
        ch = [c for c in D["dims"][name] if c["h"] < WIN] + [{"h": WIN, "dim": None}]
        a.barh(0.42, ch[0]["h"], left=0, height=0.34, color=OVER, lw=0, zorder=3)
        for u, v in zip(ch, ch[1:]):
            if u["dim"]:
                a.barh(0.42, min(v["h"], WIN) - u["h"], left=u["h"], height=0.34, color=dcol[u["dim"]], lw=0, zorder=3)
        for x in adv:
            if x["by"] == name:
                a.plot(x["h"], 0.86, marker="D", ms=2.6, color=INK, mew=0, zorder=4)
        for d in deaths:
            if d["player"] == name:
                a.plot([d["h"]] * 2, [0.18, 0.68], color=RED, lw=1.2, zorder=5)
        for c in D["compactions"]:
            if c["agent"] == name:
                a.plot(c["h"], 0.08, marker="v", ms=3, color=INK2, mew=0, zorder=4)
        a.text(-0.1, 0.45, lab, fontsize=F(6.2), fontweight="demibold", color=INK, ha="right", va="center")
    for a, lab in ((aP1, "Human 1"), (aP2, "Human 2")):
        a.set_ylim(0, 1)
        for s, e in D["presence"][lab]["spans"]:
            a.barh(0.42, e - s, left=s, height=0.34, color="#d7dadf", lw=0, zorder=3)
        for x in adv:
            if x["by"] == lab:
                a.plot(x["h"], 0.86, marker="D", ms=2.6, color=INK, mew=0, zorder=4)
        for d in deaths:
            if d["player"] == lab:
                a.plot([d["h"]] * 2, [0.18, 0.68], color=RED, lw=0.9, zorder=5)
        a.text(-0.1, 0.45, lab, fontsize=F(6.2), fontweight="demibold", color=INK2, ha="right", va="center")
    # Programs per half hour, both agents together (they ran 349 and 346); the dimension colours stay the rows' only colours
    pf = half_hours(D["programs"][FOX]["per_quarter_hour"])
    pv = half_hours(D["programs"][VOID]["per_quarter_hour"])
    for b in sorted(set(pf) | set(pv)):
        lo, hi = b / 2 + 0.02, min(b / 2 + 0.48, WIN)
        aProg.bar(lo, pf.get(b, 0) + pv.get(b, 0), width=hi - lo, align="edge", color=AG_BAR, lw=0, zorder=3)
    aProg.set_ylim(0, 110)
    aProg.text(-0.1, 55, "Programs\nper half hour", fontsize=F(5.6), fontweight="demibold", ha="right", va="center", linespacing=1.2)
    # Chat per half hour: agents by name, people together
    cq = D["chat"]["per_quarter_hour"]
    cf, cv = half_hours(cq.get(FOX, [])), half_hours(cq.get(VOID, []))
    cp1, cp2 = half_hours(cq.get("Human 1", [])), half_hours(cq.get("Human 2", []))
    for b in sorted(set(cf) | set(cv) | set(cp1) | set(cp2)):
        lo, hi = b / 2 + 0.02, min(b / 2 + 0.48, WIN)
        g_, p_ = cf.get(b, 0) + cv.get(b, 0), cp1.get(b, 0) + cp2.get(b, 0)
        aChat.bar(lo, g_, width=hi - lo, align="edge", color=AG_BAR, lw=0, zorder=3)
        aChat.bar(lo, p_, bottom=g_ + 0.8, width=hi - lo, align="edge", color=PP_BAR, lw=0, zorder=3)
        if b == 0:
            aChat.text(lo + 0.03, g_ / 2, "agents", fontsize=F(5.2), color="white", fontweight="demibold", va="center", zorder=5)
            aChat.text(lo + 0.03, g_ + 0.8 + p_ / 2, "people", fontsize=F(5.2), color=INK, fontweight="demibold", va="center", zorder=5)
    aChat.set_ylim(0, 75)
    aChat.text(-0.1, 37, "Chat lines\nper half hour", fontsize=F(5.6), fontweight="demibold", ha="right", va="center", linespacing=1.2)
    for a, ticks in ((aProg, (30, 60, 90)), (aChat, (20, 40, 60))):
        a.set_yticks(ticks)
        a.tick_params(axis="y", labelsize=F(5), length=0, pad=1)
        a.yaxis.tick_right()
        for y in ticks:
            a.axhline(y, color="white", lw=0.5, zorder=4)
    aChat.spines["bottom"].set_visible(True)
    aChat.spines["bottom"].set_color("#dadce0")
    aChat.set_xticks([0, 1, 2, 3, 4, WIN])
    aChat.set_xticklabels(["0 h", "1 h", "2 h", "3 h", "4 h", "4 h 36"], fontsize=F(5.4))
    aChat.get_xticklabels()[-1].set_fontweight("demibold")
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    hd = [Line2D([], [], marker="D", ms=3, color=INK, ls="none", mew=0), Line2D([], [], marker="|", ms=6, color=RED, ls="none", mew=1.2),
          Line2D([], [], marker="v", ms=3.5, color=INK2, ls="none", mew=0)]
    hd += [Patch(color=c, lw=0) for c in (OVER, NETH, END, "#d7dadf")]
    lb = ["advancement", "death", "compaction", "Overworld", "Nether", "End", "person on the server"]
    fig.legend(hd, lb, loc="upper center", bbox_to_anchor=(0.55, 0.005), ncol=7, frameon=False, fontsize=F(5.3), handlelength=1.0, handleheight=0.8,
               handletextpad=0.4, columnspacing=1.1, labelcolor=INK2)
    save(fig, "fig2_run")


# ---------------------------------------------------------------- Figure 3: the dragon's health and who took it
def fig_dragon():
    G = D["dragon"]
    fig = plt.figure(figsize=(6.4, 2.75))
    ax = fig.add_axes([0.075, 0.13, 0.6, 0.74])
    bx = fig.add_axes([0.80, 0.13, 0.18, 0.74])
    x0 = M["the_end"] - 0.02
    ax.set_xlim(x0, WIN + 0.02)
    ax.set_ylim(-4, 215)
    ax.axvspan(x0, WIN + 0.02, color="#f0effa", lw=0, zorder=0)
    # When the dragon read phase 1 (strafe) for more than 4 minutes
    for s in G["strafes_over_4_min"]:
        a, b = hclock(s["from"]), hclock(s["to"])
        ax.axvspan(max(a, LAST), b, ymin=0.0, ymax=1.0, color="#e2e0f2", lw=0, zorder=1)
    st = G["strafes_over_4_min"]
    ax.text((LAST + hclock(st[0]["to"])) / 2, 207, "stuck strafing", fontsize=F(5.3), color=INK2, ha="center", va="center")
    ax.text((hclock(st[1]["from"]) + hclock(st[1]["to"])) / 2, 207, "stuck again", fontsize=F(5.3), color=INK2, ha="center", va="center")
    # Every agent left the End: from the second agent's void death to "GO"
    void = sorted(d["h"] for d in D["deaths"] if d["agent"] and d["cause"] == "Void")
    go = hclock("4:12:25")
    ax.axvspan(void[-1], go, color="#ffffff", lw=0, zorder=1.5)
    ax.text((void[-1] + go) / 2, 186, "End\nempty", fontsize=F(5.0), color=INK2, ha="center", va="center", linespacing=1.0)
    # The health line: 200 from the last crystal, then each drop
    rows = [(H(r["t"]), r["from"], r["to"], r["src"]) for r in G["attrib"]]
    gaps = []
    for g in G["gaps"]:
        a = LAST if g["after"] == "last crystal" else hclock(g["after"])
        b = hclock(g["before"])
        gaps.append((a, b, g["from"], g["to"], "people" if g["src"].startswith("people") else "unattributed"))
    steps = [(LAST, 200.0)]
    for t, f_, to, _ in rows:
        steps.append((t, to))
    for a, b, f_, to, _ in gaps:
        steps.append((b, to))
    steps.sort()
    xs, ys = [s[0] for s in steps] + [WIN + 0.005], [s[1] for s in steps] + [0]
    ax.step(xs, ys, where="post", color=INK2, lw=0.6, zorder=3)
    for t, f_, to, src in rows:
        ax.plot([t, t], [f_, to], color=SRC[src], lw=3.0, solid_capstyle="butt", zorder=4)
    for a, b, f_, to, src in gaps:
        ax.plot([b, b], [f_, to], color=SRC[src], lw=3.0, solid_capstyle="butt", zorder=4, alpha=0.55)
    # Agent deaths in the End
    for d in D["deaths"]:
        if d["agent"] and d["h"] >= M["the_end"]:
            ax.plot([d["h"]] * 2, [-4, 6], color=RED, lw=1.2, zorder=5)
    place_icon(ax, "end_crystal", (LAST, 200), zoom=0.3)
    ax.text(LAST - 0.012, 200, "last\ncrystal", fontsize=F(5.0), color=INK2, ha="right", va="center", linespacing=1.0)
    place_icon(ax, "dragon_egg", (WIN, 0), zoom=0.3)
    ax.set_xticks([3.5, 3.75, 4.0, 4.25, 4.5, WIN])
    ax.set_xticklabels(["3:30", "3:45", "4:00", "4:15", "4:30", "4:36"], fontsize=F(5.4))
    ax.get_xticklabels()[-1].set_fontweight("demibold")
    ax.set_yticks([0, 50, 100, 150, 200])
    ax.tick_params(axis="y", labelsize=F(5.2), length=0, pad=1)
    for y in (50, 100, 150, 200):
        ax.axhline(y, color="white", lw=0.5, zorder=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#dadce0")
    ax.spines["bottom"].set_color("#dadce0")
    caps(ax, 0.0, 1.06, "The dragon's health after entry to the End", transform=ax.transAxes)
    ax.text(x0 + 0.01, 100, "health", rotation=90, fontsize=F(5.2), color=INK2, va="center", ha="left")
    # Who took it
    dmg = G["damage"]
    order = [("FoxglenOpus", "Foxglen's sword"), ("VoidmothOpus", "Voidmoth's sword"), ("explosion", "People's beds"), ("people", "People's hits"), ("unattributed", "Unattributed")]
    for i, (k, lab) in enumerate(order):
        v = dmg.get(k, 0)
        bx.barh(i, v, height=0.62, color=SRC[k], lw=0, zorder=3)
        bx.text(v + 2, i, f"{v:.1f}  ({v / 2:.0f}%)", fontsize=F(5.4), color=INK, va="center", ha="left")
        bx.text(-3, i, lab, fontsize=F(5.6), fontweight="demibold", color=INK, va="center", ha="right")
    bx.set_ylim(len(order) - 0.4, -0.6)
    bx.set_xlim(0, 100)
    for s in ("top", "right", "left", "bottom"):
        bx.spines[s].set_visible(False)
    bx.set_xticks([])
    bx.set_yticks([])
    caps(bx, -0.62, 1.06, "Damage by source", transform=bx.transAxes)
    save(fig, "fig3_dragon")


if __name__ == "__main__":
    (FIG / "preview").mkdir(parents=True, exist_ok=True)
    fig_steps()
    fig_run()
    fig_dragon()
