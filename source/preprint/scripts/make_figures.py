#!/usr/bin/env python3
"""Draw the preprint's figures from preprint/data/run.json.

    <python with matplotlib + pillow> preprint/scripts/make_figures.py   -> preprint/figures/*.pdf

Style follows arXiv 2610.22319's figures: pastel bands for the four stages, small
letter-spaced labels, item icons from the Pixel Perfection texture pack (CC BY-SA 4.0,
in figures/icons/). Hours are hours since the first program.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.patheffects import withStroke
from PIL import Image

PRE = Path(__file__).resolve().parent.parent
FIG = PRE / "figures"
D = json.loads((PRE / "data" / "run.json").read_text())
T0 = datetime.fromisoformat(D["t0_utc"])
WIN = D["win_h"]

plt.rcParams.update({
    "font.family": "Avenir Next", "font.size": 7, "pdf.fonttype": 42, "axes.linewidth": 0.6,
    "axes.edgecolor": "#c9ccd1", "xtick.color": "#5f6368", "ytick.color": "#5f6368",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.labelcolor": "#5f6368", "text.color": "#1f1f1f",
})
HALO = [withStroke(linewidth=1.6, foreground="white")]
INK, INK2, MUTED, GRID = "#1f1f1f", "#5f6368", "#9aa0a6", "#e8eaed"
RED = "#d93025"
# Places (validated: dataviz validate_palette.js, light, all pairs).
OVER, NETH, END = "#1baf7a", "#eb6834", "#6250d6"
STAGES = [  # name, start, end, band, label colour
    ("OVERWORLD", 0, D["milestones"]["nether_portal"], "#edf6ea", "#3c8a3a"),
    ("NETHER", D["milestones"]["nether_portal"], D["milestones"]["stronghold"], "#fcefe9", "#c5462b"),
    ("STRONGHOLD", D["milestones"]["stronghold"], D["milestones"]["the_end"], "#eef0f4", "#6b7280"),
    ("THE END", D["milestones"]["the_end"], WIN, "#f0effa", "#5b4fc4"),
]
TEN_CRYSTALS = 59 + 48 / 60  # workspace commit "all crystals destroyed"; the dashboard step never fired
PAPER = {"stone_tools": 6, "iron_tools": 14, "bucket": 14, "flint_and_steel": 64, "nether_portal": 102, "fortress": 177,
         "ender_pearls": 186, "blaze_rods": 257, "eyes_of_ender": 643, "stronghold": 797, "the_end": 813,
         "ten_crystals": 1594, "dragon": 1634}  # minutes, the paper's Figure 1
STEPS = [("bare", "Bare hands", None), ("stone_tools", "Stone tools", "stone_pickaxe"), ("iron_tools", "Iron tools", "iron_pickaxe"),
         ("bucket", "Bucket", "bucket"), ("flint_and_steel", "Flint and steel", "flint_and_steel"),
         ("nether_portal", "Nether portal", "obsidian"), ("fortress", "Nether fortress", "nether_bricks"),
         ("blaze_rods", "Blaze rods", "blaze_rod"), ("ender_pearls", "Ender pearls", "ender_pearl"),
         ("eyes_of_ender", "Eyes of Ender", "ender_eye"), ("stronghold", "Stronghold", "end_portal_frame_top"),
         ("the_end", "The End", "end_stone"), ("ten_crystals", "Ten crystals", "end_crystal"), ("dragon", "Ender Dragon", "dragon_egg")]
# Researcher actions during the run (README "Changes during the run").
INTERVENTIONS = [(6.93, "compaction at 350k"), (16.14, "Pause fix, bot host restart"), (58.97, "effort: xhigh")]
SLEEP = (9.41, 15.82)  # Mac asleep, 2026-11-01 21:37 to 2026-11-02 04:02 CST


def step_h(key):
    return 0.0 if key == "bare" else TEN_CRYSTALS if key == "ten_crystals" else D["milestones"][key]


def hm(h):
    m = int(h * 60)  # floor, as verify-run.py and the README report it
    return f"+{m // 60}h{m % 60:02d}"


def icon(name, zoom):
    im = Image.open(FIG / "icons" / f"{name}.png").convert("RGBA")
    return OffsetImage(im, zoom=zoom, interpolation="nearest", resample=False)


def place_icon(ax, name, xy, zoom=0.55, frame=None, coords="data"):
    ab = AnnotationBbox(icon(name, zoom), xy, xycoords=coords, frameon=frame is not None, pad=0.15, zorder=6,
                        bboxprops=dict(boxstyle="circle,pad=0.25", fc="white", ec=frame or "none", lw=0.9))
    ax.add_artist(ab)


def stage_bands(ax, top_labels=True, y=1.0):
    for name, a, b, band, col in STAGES:
        ax.axvspan(a, b, color=band, zorder=0, lw=0)
        if top_labels:
            narrow = b - a < 2  # the Overworld lasts 54 min: label it to the left of its band
            ax.text(b - 0.3 if narrow else a + 0.25, y, name, ha="right" if narrow else "left", transform=ax.get_xaxis_transform(), fontsize=5.2, color=col,
                    fontweight="demibold", va="bottom")


def hour_axis(ax, label=True):
    ticks = list(range(0, 61, 6))
    ax.set_xticks(ticks + [WIN])
    ax.set_xticklabels([f"{t} h" for t in ticks[:-1]] + ["", "60 h 49 min"])
    ax.get_xticklabels()[-1].set_fontweight("demibold")
    ax.set_xlim(-0.6, WIN + 0.6)
    if label:
        ax.text(1, -0.2, "Hours since the first program", transform=ax.transAxes, ha="right", va="top", fontsize=5.5, color=MUTED)


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
    ax.text(x, y, " ".join(text.upper()).replace("   ", "  "), fontsize=5, color=MUTED, fontweight="demibold", **kw)


# ---------------------------------------------------------------- Figure 1: steps
def fig_steps():
    fig = plt.figure(figsize=(6.4, 2.6))
    ax = fig.add_axes([0.13, 0.18, 0.86, 0.72])
    card = fig.add_axes([0.545, 0.27, 0.42, 0.33]); card.axis("off"); card.set_xlim(0, 1); card.set_ylim(0, 1)
    for x0, head, name, col, lines, stats, dashed in (
            (0.0, "This run", "opus", END, "Claude Opus 5.5 in Claude Code.\nEvery step; the only player.", "5,879 programs · 0 messages", False),
            (0.52, "The paper's team", "4 Gemini 4 Argon agents", INK2, "janesick, gyldenia, auratian\nand bulicame.", "2,783 programs · 229 messages", True)):
        caps(card, x0, 0.97, head, va="top")
        card.add_patch(FancyBboxPatch((x0, 0.02), 0.47, 0.78, boxstyle="round,pad=0,rounding_size=0.04", fc="#f6f7f9", ec="#e3e5e8", lw=0.6))
        if dashed:
            card.plot([x0 + 0.04, x0 + 0.1], [0.66, 0.66], color=MUTED, lw=0.9, ls=(0, (2, 1.5)))
        else:
            card.plot([x0 + 0.04, x0 + 0.1], [0.66, 0.66], color=END, lw=1.1)
        card.text(x0 + 0.125, 0.66, name, fontsize=6.6 if not dashed else 5.8, fontweight="demibold", color=col, va="center")
        card.text(x0 + 0.04, 0.5, lines, fontsize=5.2, color=INK2, va="top", linespacing=1.35)
        card.text(x0 + 0.04, 0.14, stats, fontsize=5, color=MUTED, va="center")
    caps(ax, 0.0, 1.11, "The run, step by step", transform=ax.transAxes)
    stage_bands(ax, y=1.01)
    xs = [step_h(k) for k, _, _ in STEPS]
    ys = list(range(len(STEPS)))
    px = [0] + [PAPER[k] / 60 for k, _, _ in STEPS[1:]]
    ax.step(px, ys, where="post", color=MUTED, lw=0.8, ls=(0, (2, 1.5)), zorder=2)
    ax.step(xs, ys, where="post", color=END, lw=1.1, zorder=3)
    # Limits first: an annotation whose point lies outside the axes measures as an empty box.
    ax.set_ylim(-1.8, len(STEPS) - 0.4); ax.set_xlim(-0.6, WIN + 0.6)
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    rend = FigureCanvasAgg(fig).get_renderer()  # to measure the time labels, in pixels at fig.dpi
    for (k, label, ic), x, y in zip(STEPS, xs, ys):
        if ic:
            place_icon(ax, ic, (x, y), zoom=0.42, frame=END)
            t = ax.annotate(hm(x), (x, y), xytext=(-7.5, 0), textcoords="offset points", ha="right", va="center", fontsize=5,
                            color=INK2, path_effects=HALO)
            w = t.get_window_extent(rend).width * 72 / fig.dpi
            ax.annotate(label, (x, y), xytext=(-7.5 - w - 2.5, 0), textcoords="offset points", ha="right", va="center",
                        fontsize=5.6, fontweight="demibold", color=INK, path_effects=HALO)
        else:
            ax.plot([x], [y], "o", ms=4.5, mfc="white", mec=INK, mew=0.9, zorder=5)
            ax.text(x + 1.0, y, label, ha="left", va="center", fontsize=5.6, fontweight="demibold", color=INK)
    ax.text(PAPER["dragon"] / 60 + 0.8, len(STEPS) - 1, "paper +27h14", fontsize=5, color=MUTED, va="center")
    # deaths strip
    for dth in D["deaths"]:
        ax.plot([dth["h"]] * 2, [-1.55, -1.0], color=RED, lw=0.5, solid_capstyle="butt", zorder=3)
    ax.text(-0.9, -1.27, f"{len(D['deaths'])} deaths", ha="right", va="center", fontsize=5.3, color=RED, fontweight="demibold")
    ax.set_ylim(-1.8, len(STEPS) - 0.4)
    clean(ax)
    ax.spines["bottom"].set_color("#dadce0")
    hour_axis(ax)
    ax.text(0, -0.2, "Solid: this run. Dashed: the paper's team (its Figure 1).", transform=ax.transAxes, ha="left", va="top", fontsize=5.5, color=MUTED)
    save(fig, "fig1_steps")


# ---------------------------------------------------------------- Figure 2: how the agent plays
def box(ax, x, y, w, h, title, body, ic=None, title_col=INK, fc="white", ec="#e3e5e8", dashed=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.018", fc=fc, ec=ec, lw=0.7,
                                ls=(0, (3, 2)) if dashed else "-"))
    tx = x + 0.018
    if ic:
        place_icon(ax, ic, (x + 0.03, y + h - 0.042), zoom=0.5)
        tx = x + 0.06
    ax.text(tx, y + h - 0.042, title, fontsize=6.3, fontweight="demibold", color=title_col, va="center")
    ax.text(x + 0.018, y + h - 0.072, body, fontsize=5.1, color=INK2, va="top", linespacing=1.4)


def arrow(ax, a, b, text=None, dashed=False, col="#9aa0a6"):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=col, lw=0.8, mutation_scale=7,
                                                    ls=(0, (3, 2)) if dashed else "-", shrinkA=0, shrinkB=0))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.03, text, fontsize=4.8, color=MUTED, ha="center")


def fig_loop():
    fig = plt.figure(figsize=(6.4, 2.35))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 0.62)
    box(ax, 0.005, 0.17, 0.215, 0.2, "One Claude Opus 5.5 agent",
        "A general-purpose coding agent in\nClaude Code. Nothing specific to\nMinecraft. Plays the player opus.", title_col=END, fc="#f6f5fd", ec="#d9d5f5")
    box(ax, 0.29, 0.19, 0.2, 0.16, "A JavaScript program", "Seconds to minutes of actions:\nwalk, mine, craft, fight.", ic="wooden_pickaxe")
    box(ax, 0.545, 0.19, 0.2, 0.16, "A Mineflayer bot", "An open-source library that\ncontrols one player in the game.", ic="crafting_table_front")
    box(ax, 0.8, 0.19, 0.195, 0.16, "A Minecraft server", "Java 1.20.4, survival on Easy,\nfrom a random seed.", ic="grass_block_side")
    box(ax, 0.29, 0.42, 0.455, 0.15, "Its workspace",
        "Notes in memory/, 51 helper files in lib/ that it wrote itself, git history (121 commits),\nand, from the start, the earlier paper and strategy guides drawn from it.", ic="writable_book")
    box(ax, 0.8, 0.42, 0.195, 0.15, "A camera", "Researchers only: a frame every\n10 s. The agent never sees it.", ic="spyglass", dashed=True)
    arrow(ax, (0.22, 0.27), (0.29, 0.27), "writes")
    arrow(ax, (0.49, 0.27), (0.545, 0.27))
    arrow(ax, (0.745, 0.27), (0.8, 0.27))
    arrow(ax, (0.17, 0.37), (0.29, 0.495))
    ax.text(0.2, 0.45, "reads, edits", fontsize=4.8, color=MUTED, ha="center")
    arrow(ax, (0.897, 0.42), (0.897, 0.35), dashed=True)
    ax.text(0.905, 0.385, "reads the world", fontsize=4.6, color=MUTED, va="center")
    # text back
    ax.plot([0.897, 0.897, 0.11], [0.19, 0.1, 0.1], color="#4c8bf5", lw=0.8, ls=(0, (3, 2)))
    arrow(ax, (0.11, 0.1), (0.11, 0.17), dashed=True, col="#4c8bf5")
    ax.text(0.5, 0.065, "Text back: position, health, inventory, what it found, or the error", fontsize=5.4, color="#1a73e8", ha="center", va="center")
    ax.text(0.5, 0.025, "No pixels, no keyboard, no mouse", fontsize=4.8, color=MUTED, ha="center", va="center")
    save(fig, "fig2_loop")


# ---------------------------------------------------------------- Figure 3: the whole run
def fig_run():
    fig = plt.figure(figsize=(6.4, 3.4))
    hs = [0.2, 0.17, 0.25, 0.25]
    axs, top = [], 0.97
    for i, h in enumerate(hs):
        axs.append(fig.add_axes([0.11, top - h, 0.87, h - 0.02]))
        top -= h
    a0, a1, a2, a3 = axs
    for a in axs:
        stage_bands(a, top_labels=(a is a0), y=1.04)
        a.axvspan(*SLEEP, color="white", alpha=0.55, zorder=0.5, lw=0, hatch="////", ec="#d5d7db")
        a.set_xlim(-0.6, WIN + 0.6)
        for x, _ in INTERVENTIONS:
            a.axvline(x, color="#f29900", lw=0.7, ls=(0, (2.5, 1.5)), zorder=1)
        clean(a)
        a.set_xticks([])
    # milestones row
    a0.set_ylim(0, 1)
    marks = [("nether_portal", "Nether portal", "obsidian", 0.62, "left"), ("fortress", "Fortress", "nether_bricks", 0.25, "left"),
             ("stronghold", "Stronghold located", "end_portal_frame_top", 0.62, "left"), ("the_end", "Into the End", "end_stone", 0.25, "left"),
             ("ten_crystals", "Last crystal", "end_crystal", 0.62, "right"), ("dragon", "Dragon defeated", "dragon_egg", 0.25, "right")]
    for k, label, ic, y, side in marks:
        x = step_h(k)
        place_icon(a0, ic, (x, y), zoom=0.36)
        a0.text(x + (1.0 if side == "left" else -1.0), y, label, fontsize=5.4, fontweight="demibold", va="center",
                ha="left" if side == "left" else "right")
    a0.text((SLEEP[0] + SLEEP[1]) / 2, 0.25, "Mac asleep", fontsize=5, color=MUTED, ha="center", va="center")
    # lane: advancements, deaths, compactions
    a1.set_ylim(-0.1, 1.1)
    a1.text(-1.2, 0.5, "opus", fontsize=6.5, fontweight="demibold", color=END, ha="right", va="center")
    for adv in D["advancements"]:
        a1.plot(adv["h"], 0.78, marker="D", ms=2.8, color=INK, mew=0, zorder=4)
    for dth in D["deaths"]:
        a1.plot([dth["h"]] * 2, [0.32, 0.6], color=RED, lw=0.6, zorder=4)
    for c in D["compactions"]:
        a1.plot(c["h"], 0.12, marker="v", ms=3, color=INK2, mew=0, zorder=4)
    # programs per half hour
    pph = D["programs"]["per_half_hour"]
    a2.bar([b / 2 + 0.25 for b, _ in pph], [n for _, n in pph], width=0.42, color="#a8c7fa", lw=0, zorder=3)
    a2.set_ylim(0, 125)
    a2.text(-1.2, 62, "Programs\nper half hour", fontsize=5.6, fontweight="demibold", ha="right", va="center", linespacing=1.2)
    a2.set_yticks([0, 60, 120]); a2.tick_params(axis="y", labelsize=5, length=0, pad=1)
    a2.yaxis.tick_right()
    for y in (60, 120):
        a2.axhline(y, color=GRID, lw=0.5, zorder=1)
    # context
    cx = [c[0] for c in D["ctx"] if c[0] <= WIN]
    cy = [c[1] / 1000 for c in D["ctx"] if c[0] <= WIN]
    a3.plot(cx, cy, color=END, lw=0.7, zorder=3)
    a3.axhline(350, color=INK2, lw=0.5, ls=(0, (2, 2)), zorder=2)
    a3.text(WIN + 0.4, 350, "350k", fontsize=5, color=INK2, va="bottom", ha="right")
    a3.set_ylim(0, 520)
    a3.set_yticks([0, 250, 500]); a3.set_yticklabels(["0", "250k", "500k"]); a3.tick_params(axis="y", labelsize=5, length=0, pad=1)
    a3.yaxis.tick_right()
    for x, t in INTERVENTIONS:
        a3.text(x + (0.4 if x < 50 else -0.4), 470, t, fontsize=4.8, color="#b06000", ha="left" if x < 50 else "right", va="center")
    a3.text(-1.2, 260, "Context\n(tokens)", fontsize=5.6, fontweight="demibold", ha="right", va="center", linespacing=1.2)
    a3.spines["bottom"].set_visible(True); a3.spines["bottom"].set_color("#dadce0")
    hour_axis(a3, label=False)
    # legend row
    ly = 0.035
    lg = fig.add_axes([0.11, -0.04, 0.87, 0.05]); lg.axis("off"); lg.set_xlim(0, 1); lg.set_ylim(0, 1)
    items = [("D", INK, "advancement"), ("|", RED, "death"), ("v", INK2, "compaction"), ("-", "#f29900", "researcher change"),
             ("/", "#d5d7db", "Mac asleep")]
    x = 0.0
    for m, c, t in items:
        if m == "-":
            lg.plot([x, x + 0.025], [0.35, 0.35], color=c, lw=0.8, ls=(0, (2.5, 1.5)))
            x += 0.032
        elif m == "/":
            lg.add_patch(Rectangle((x, 0.12), 0.022, 0.46, fc="white", ec=c, hatch="////", lw=0.5))
            x += 0.03
        else:
            lg.plot(x + 0.006, 0.35, marker=m, ms=3 if m != "|" else 5, color=c, mew=0.8 if m == "|" else 0)
            x += 0.016
        lg.text(x, 0.35, t, fontsize=5.3, color=INK2, va="center")
        x += 0.012 * len(t) * 0.55 + 0.03
    lg.text(1, 0.35, "Hours since the first program", fontsize=5.5, color=MUTED, ha="right", va="center")
    save(fig, "fig3_run")


# ---------------------------------------------------------------- Figure 5: deaths
def death_places():
    frames = []
    for line in (PRE.parent / "runs" / "2026-11-01-1211" / "server" / "camera" / "frames.jsonl").read_text().splitlines():
        f = json.loads(line)
        frames.append(((datetime.fromisoformat(f["t"].replace("Z", "+00:00")) - T0).total_seconds() / 3600, f["dim"]))
    out = []
    for dth in D["deaths"]:
        h = dth["h"]
        prior = [dim for fh, dim in frames if h - 300 / 3600 <= fh <= h - 1 / 3600]
        if "out of the world" in dth["text"] or "same world as" in dth["text"] or "Ender Dragon" in dth["text"]:
            place = "the_end"
        elif prior:
            place = prior[-1]
        elif h < D["milestones"]["nether_portal"]:
            place = "overworld"
        else:
            place = "unknown"
        out.append(place)
    return out


def fig_deaths():
    places = death_places()
    groups = {"Silverfish": "Other mobs", "Spiders": "Other mobs", "Blazes": "Other mobs", "Hoglins": "Other mobs",
              "Dragon (fall, contact)": "Dragon (knocked off, hit)", "Suffocation": "Suffocation"}
    rows = {}
    for dth, pl in zip(D["deaths"], places):
        c = groups.get(dth["cause"], dth["cause"])
        rows.setdefault(c, {"overworld": 0, "the_nether": 0, "the_end": 0, "unknown": 0})[pl] += 1
    order = sorted(rows, key=lambda c: (c == "Other mobs", -sum(rows[c].values())))
    fig = plt.figure(figsize=(6.4, 2.45))
    ax = fig.add_axes([0.16, 0.12, 0.38, 0.8])
    caps(ax, -0.36, 1.11, "Deaths by cause and place", transform=ax.transAxes)
    for i, c in enumerate(order):
        x = 0
        for pl, col in (("overworld", OVER), ("the_nether", NETH), ("the_end", END)):
            n = rows[c][pl]
            if n:
                ax.barh(i, n - 0.12, left=x, height=0.62, color=col, lw=0, zorder=3)
                x += n
        ax.text(x + 0.4, i, str(x), va="center", fontsize=5.4, color=INK2)
        ax.text(-0.5, i, c, va="center", ha="right", fontsize=5.8, color=INK)
    ax.set_ylim(len(order) - 0.4, -0.7); ax.set_xlim(0, 19)
    clean(ax)
    ax.spines["bottom"].set_color("#dadce0")
    ax.set_xticks([0, 5, 10, 15]); ax.tick_params(axis="x", labelsize=5)
    for x in (5, 10, 15):
        ax.axvline(x, color=GRID, lw=0.5, zorder=1)
    n = {pl: places.count(pl) for pl in ("overworld", "the_nether", "the_end")}
    lx = 6.2
    for pl, col, label in (("overworld", OVER, "Overworld"), ("the_nether", NETH, "Nether"), ("the_end", END, "End")):
        ax.add_patch(Rectangle((lx, len(order) - 2.75), 0.55, 0.5, color=col, lw=0, zorder=4))
        ax.text(lx + 0.8, len(order) - 2.5, f"{label} {n[pl]}", fontsize=5.4, color=INK2, va="center")
        lx += 5.3 if pl == "overworld" else 4.4
    # cumulative deaths
    b = fig.add_axes([0.63, 0.2, 0.36, 0.72])
    caps(b, 0.0, 1.11, "Cumulative deaths", transform=b.transAxes)
    stage_bands(b, y=0.995)
    hs = [dth["h"] for dth in D["deaths"]]
    b.step([0] + hs + [WIN], list(range(0, len(hs) + 1)) + [len(hs)], where="post", color=INK, lw=0.9, zorder=3)
    for x, _ in INTERVENTIONS[2:]:
        b.axvline(x, color="#f29900", lw=0.7, ls=(0, (2.5, 1.5)), zorder=2)
    b.text(58.4, 8, "xhigh", fontsize=5, color="#b06000", ha="right")
    b.set_ylim(0, 122); b.set_xlim(-0.6, WIN + 0.6)
    for s in ("top", "right"):
        b.spines[s].set_visible(False)
    b.spines["left"].set_color("#dadce0"); b.spines["bottom"].set_color("#dadce0")
    b.set_yticks([0, 50, 100]); b.tick_params(labelsize=5)
    b.set_xticks([0, 12, 24, 36, 48, 60]); b.set_xticklabels(["0 h", "12 h", "24 h", "36 h", "48 h", "60 h"])
    end_n = sum(1 for h in hs if h >= D["milestones"]["the_end"])
    b.annotate(f"{end_n} after entering the End", xy=(D["milestones"]["the_end"], len(hs) - end_n), xytext=(13, 92),
               fontsize=5.2, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    b.text(1, -0.16, "Hours since the first program", transform=b.transAxes, ha="right", va="top", fontsize=5.5, color=MUTED)
    save(fig, "fig5_deaths")
    return n, rows


# ---------------------------------------------------------------- Figure 6: the End
CRYSTALS = [  # x, z, y, kill hour, method; positions from the agent's notes
    (42, 0, 86, 41.02, "punch"), (33, 24, 77, 41.69, "punch"), (12, -40, 92, 42.11, "punch"),
    (-13, 39, 104, 59.52, "bow"), (-34, 24, 95, 59.52, "bow"), (-34, -25, 89, 59.52, "bow"),
    (33, -25, 98, 59.69, "lob"), (12, 39, 101, 59.69, "lob"), (-13, -40, 83, 59.81, "lob, caged"), (-42, -1, 80, 59.81, "lob, caged"),
]


def clock(h):
    return (T0 + timedelta(hours=h) - timedelta(hours=6)).strftime("%H:%M")


def fig_end():
    fig = plt.figure(figsize=(6.4, 2.7))
    m = fig.add_axes([0.0, 0.08, 0.4, 0.84])
    caps(m, 0.03, 1.02, "The ten crystals, from above", transform=m.transAxes)
    m.set_aspect("equal"); m.set_xlim(-58, 110); m.set_ylim(56, -62)
    m.add_patch(plt.Circle((0, 0), 43, fc="none", ec="#e1def7", lw=4, zorder=1))
    m.add_patch(FancyBboxPatch((-56, -61), 165, 115, boxstyle="round,pad=0,rounding_size=6", fc="#f6f5fd", ec="none", zorder=0))
    m.plot(0, 0, marker="s", ms=4.5, color="#3c4043", zorder=4)
    m.text(0, 6.5, "exit portal", fontsize=4.8, color=INK2, ha="center", va="top")
    m.plot([84, 97], [0, 0], color="#8d6e63", lw=1.6, zorder=3, solid_capstyle="butt")
    m.plot(100, 0, marker="s", ms=4.2, color="#202124", zorder=4)
    m.text(100, 5, "arrival\nplatform", fontsize=4.6, color=INK2, ha="center", va="top", linespacing=1.1)
    m.text(84, 5, "its bridge", fontsize=4.6, color=INK2, ha="right", va="top")
    m.plot(38, 18, marker="^", ms=4, color="#f29900", zorder=4); m.text(42, 19.5, "mortar pit", fontsize=4.6, color="#b06000", va="center")
    m.plot(0, -4, marker="^", ms=4, color="#f29900", zorder=4); m.text(-4, -9, "melee pit", fontsize=4.6, color="#b06000", ha="right")
    import math
    for i, (x, z, y, h, how) in enumerate(CRYSTALS, 1):
        med = h < 50
        col = "#8ab4f8" if med else END
        m.plot(x, z, marker="o", ms=8.5, mfc="white", mec=col, mew=1.3, zorder=5)
        place_icon(m, "end_crystal", (x, z), zoom=0.27)
        r = math.hypot(x, z)
        m.text(x * (1 + 10.5 / r), z * (1 + 10.5 / r), str(i), fontsize=5.6, fontweight="demibold",
               color="#4a7fd4" if med else END, ha="center", va="center")
    m.axis("off")
    key = [("1", "05:14", "punched from a column", True), ("2", "05:54", "punched", True), ("3", "06:19", "punched", True),
           ("4-6", "23:44", "bow, from a peek hole", False), ("7-8", "23:54", "lobbed from a pit", False),
           ("9-10", "00:01", "lobbed into the cages", False)]
    ky = -55
    m.plot(54, ky, marker="o", ms=5.5, mfc="white", mec="#8ab4f8", mew=1.2)
    m.text(58, ky, "medium", fontsize=4.9, va="center", color=INK2)
    m.plot(82, ky, marker="o", ms=5.5, mfc="white", mec=END, mew=1.2)
    m.text(86, ky, "xhigh", fontsize=4.9, va="center", color=INK2)
    for j, (n, t, what, med) in enumerate(key):
        yy = ky + 7.2 * (j + 1)
        m.text(52, yy, n, fontsize=4.9, fontweight="demibold", color="#4a7fd4" if med else END, va="center")
        m.text(63, yy, f"{t}  {what}", fontsize=4.9, color=INK2, va="center")
    # dragon health
    b = fig.add_axes([0.5, 0.2, 0.49, 0.68])
    caps(b, 0.0, 1.06, "The dragon's health in the last hour", transform=b.transAxes)
    pts = [(x["h"], x["hp"]) for x in D["dragon"] if x["h"] >= 59.7]
    pts = [(59.7, 200)] + pts
    b.step([p[0] for p in pts], [p[1] for p in pts], where="post", color=END, lw=1.0, zorder=3)
    b.fill_between([p[0] for p in pts], [p[1] for p in pts], step="post", color="#ece9fb", lw=0, zorder=2)
    for dth in D["deaths"]:
        if dth["h"] >= 59.7:
            b.plot([dth["h"]] * 2, [-14, -4], color=RED, lw=0.8, clip_on=False, zorder=4)
    b.text(59.705, -9, "deaths", fontsize=4.8, color=RED, va="center", ha="left")
    b.axvline(TEN_CRYSTALS, color=INK2, lw=0.6, ls=(0, (2, 2)))
    b.text(TEN_CRYSTALS + 0.008, 188, "last crystal", fontsize=5, color=INK2, va="top")
    b.annotate("killed with a stone sword\n01:02:54", xy=(WIN, 0), xytext=(60.52, 75), fontsize=5.1, color=INK, ha="left",
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    b.annotate("8 HP for 28 min", xy=(60.55, 8), xytext=(60.4, 40), fontsize=5.1, color=INK2,
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    b.set_xlim(59.7, WIN + 0.02); b.set_ylim(-16, 210)
    ticks = [59.7 + i * 0.25 for i in range(5)]
    b.set_xticks(ticks); b.set_xticklabels([clock(t) for t in ticks])
    b.set_yticks([0, 100, 200]); b.tick_params(labelsize=5)
    for s in ("top", "right"):
        b.spines[s].set_visible(False)
    b.spines["left"].set_color("#dadce0"); b.spines["bottom"].set_color("#dadce0")
    b.spines["bottom"].set_position(("data", -16))
    b.text(1, -0.17, "Time (CST), 2026-11-03 to 11-04", transform=b.transAxes, ha="right", va="top", fontsize=5.5, color=MUTED)
    save(fig, "fig6_end")


if __name__ == "__main__":
    (FIG / "preview").mkdir(parents=True, exist_ok=True)
    fig_steps()
    fig_loop()
    fig_run()
    n, rows = fig_deaths()
    fig_end()
    print("death places", n, "unknown", sum(r["unknown"] for r in rows.values()))
