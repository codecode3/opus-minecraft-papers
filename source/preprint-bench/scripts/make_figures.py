#!/usr/bin/env python3
"""Draw the benchmark preprint's figures from preprint-bench/data/bench.json.

    <python with matplotlib> preprint-bench/scripts/make_figures.py   -> preprint-bench/figures/fig*.pdf

Hours are on the official clock, from each player's first spawn.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

PRE = Path(__file__).resolve().parent.parent
FIG = PRE / "figures"
(FIG / "preview").mkdir(parents=True, exist_ok=True)
D = json.loads((PRE / "data" / "bench.json").read_text())
OPUS, FABLE = D["arms"]
STOP = OPUS["last_model_message"] / 3600

plt.rcParams.update({
    "font.family": "Avenir Next", "font.size": 8, "pdf.fonttype": 42, "axes.linewidth": 0.6,
    "axes.edgecolor": "#c9ccd1", "xtick.color": "#5f6368", "ytick.color": "#5f6368",
    "axes.labelcolor": "#5f6368", "text.color": "#1f1f1f",
})
COL = {"opus": "#5b3fd6", "fable": "#0f8f7c"}
NAME = {"opus": "Opus 5.5, xhigh", "fable": "Fable 5.2, low"}
DIM = {"overworld": "#cfe8c8", "the_nether": "#f3c9c0", "the_end": "#e9e3b4"}
DIMNAME = {"overworld": "Overworld", "the_nether": "Nether", "the_end": "The End"}
hm = lambda h, _=None: f"{int(h)}:{int(round((h % 1) * 60)):02d}"


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / "preview" / f"{name}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


# Figure 1: the eleven steps both arms reached.
keys = [m["key"] for m in OPUS["milestones"]]
labels = {m["key"]: m["label"] for m in OPUS["milestones"]}
keys.sort(key=lambda k: min(next(m["clock"] for m in a["milestones"] if m["key"] == k) for a in (OPUS, FABLE)))
fig, ax = plt.subplots(figsize=(6.9, 3.5))
for i, k in enumerate(keys):
    y = len(keys) - 1 - i
    t = {a["name"]: next(m["clock"] for m in a["milestones"] if m["key"] == k) / 3600 for a in (OPUS, FABLE)}
    ax.plot([t["opus"], t["fable"]], [y, y], color="#c9ccd1", lw=1.4, zorder=1)
    for n in ("opus", "fable"):
        ax.scatter(t[n], y, s=34, color=COL[n], zorder=3, edgecolor="white", linewidth=0.7)
    first = min(t, key=t.get)
    gap = abs(t["opus"] - t["fable"]) * 60
    txt = f"{NAME[first].split(',')[0]} first by {gap:.0f} min" if gap >= 1 else f"{NAME[first].split(',')[0]} first by {gap * 60:.0f} s"
    ax.text(max(t.values()) + 0.06, y, txt, va="center", fontsize=7, color=COL[first])
ax.set_yticks(range(len(keys)))
ax.set_yticklabels([labels[k] for k in reversed(keys)])
ax.set_xlim(0, 4.6)
ax.xaxis.set_major_formatter(hm)
ax.set_xlabel("Official clock (h:mm after first spawn)")
ax.grid(axis="x", color="#e8eaed", lw=0.6)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.legend(handles=[Line2D([], [], marker="o", ls="", color=COL[n], label=NAME[n]) for n in ("opus", "fable")],
          loc="upper right", frameon=False)
save(fig, "fig1_steps")

# Figure 2: where each player was, when it died, and the shared usage window.
fig, axes = plt.subplots(3, 1, figsize=(6.9, 4.3), sharex=True, gridspec_kw={"height_ratios": [1, 1, 1.5], "hspace": 0.16})
for ax, a in zip(axes[:2], (OPUS, FABLE)):
    spans = a["dims"] + [[a["last_model_message"], None]]
    for (t0, d), (t1, _) in zip(spans, spans[1:]):
        ax.axvspan(t0 / 3600, t1 / 3600, color=DIM[d], lw=0)
    played = [x["clock"] / 3600 for x in a["deaths"] if x["clock"] <= a["last_model_message"]]
    idle = [x["clock"] / 3600 for x in a["deaths"] if x["clock"] > a["last_model_message"]]
    ax.scatter(played, [0.5] * len(played), marker="x", s=30, color="#1f1f1f", lw=1.3, zorder=3)
    ax.scatter(idle, [0.5] * len(idle), marker="x", s=30, color="#9aa0a6", lw=1.3, zorder=3)
    for m in a["milestones"]:
        if m["key"] in ("nether_portal", "the_end"):
            ax.axvline(m["clock"] / 3600, color=COL[a["name"]], lw=1.1)
    ax.axvspan(STOP, 6.6, color="#f1f3f4", lw=0, zorder=0)
    ax.set_yticks([])
    ax.set_ylim(0, 1)
    ax.set_ylabel(NAME[a["name"]].replace(", ", "\n"), rotation=0, ha="right", va="center", color=COL[a["name"]], fontsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
axes[0].text(STOP + 0.05, 0.5, "agent stopped: usage limit", va="center", fontsize=7, color="#5f6368")
axes[1].text(STOP + 0.05, 0.14, "3 deaths with no agent playing", va="center", fontsize=7, color="#5f6368")
axes[0].legend(handles=[Patch(color=DIM[k], label=DIMNAME[k]) for k in DIM] + [Line2D([], [], marker="x", ls="", color="#1f1f1f", label="death")],
               loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=4, frameon=False, fontsize=7)
ax = axes[2]
for a in (OPUS, FABLE):
    seen = {}
    for x in a["limits"]:
        if x["utilization"] is not None:
            seen.setdefault(x["resetsAt"], []).append((x["clock"] / 3600, 100 * x["utilization"]))
    for pts in seen.values():
        ax.plot(*zip(*pts), color=COL[a["name"]], lw=1.3, alpha=0.9)
ax.axhline(100, color="#c5221f", lw=0.8, ls="--")
ax.text(0.05, 103, "limit", color="#c5221f", fontsize=7)
reset = OPUS["limits"][0]["resetsAt"]
t0 = __import__("datetime").datetime.fromisoformat(OPUS["t0"]).timestamp()
ax.axvline((reset - t0) / 3600, color="#9aa0a6", lw=0.8, ls=":")
ax.text((reset - t0) / 3600 + 0.05, 8, "window resets", fontsize=7, color="#5f6368")
ax.axvline(STOP, color="#c5221f", lw=0.8)
ax.text(STOP + 0.05, 55, f"both agents refused\nat {hm(STOP)}", fontsize=7, color="#c5221f")
ax.set_ylim(0, 115)
ax.set_xlim(0, 6.6)
ax.set_ylabel("Share of the 5-hour\nusage window (%)")
ax.set_xlabel("Official clock (h:mm after first spawn)")
ax.xaxis.set_major_formatter(hm)
ax.grid(color="#e8eaed", lw=0.6)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
save(fig, "fig2_timeline")
print("figures written")
