"""Draw the README chart of official time per run, in a light and a dark version.

Reads each run's official time (first spawn to the win, or to the end of a run
without one) and whether it won from the run 4 paper's data, then writes
run-times-light.svg and run-times-dark.svg next to this script.

    python3 images/make_run_times.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "source" / "preprint-run4" / "data" / "run4.json"

# Colours: one series, validated against GitHub's page backgrounds.
THEMES = {
    "light": dict(surface="#ffffff", ink="#0b0b0b", ink2="#52514e", muted="#6f6d68",
                  grid="#e1e0d9", axis="#c3c2b7", series="#2a78d6"),
    "dark": dict(surface="#0d1117", ink="#f0efec", ink2="#c3c2b7", muted="#9a9890",
                 grid="#2c2c2a", axis="#4a4a46", series="#3987e5"),
}
FONT = 'system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif'

W, H = 800, 440
LEFT, RIGHT, TOP, BOTTOM = 64, 776, 96, 384
Y_MAX = 70  # hours at the top of the plot
Y_TICKS = [0, 20, 40, 60]

# Where each run's label sits relative to its point. Run 2's goes up and to
# the right so it clears the line coming down from run 1.
LABEL_PLACE = {"run1": "above", "run2": "above-right", "run3": "above", "run4": "above"}


def hm(hours):
    """6.8478 -> '6 h 51 min'."""
    total = round(hours * 60)
    return f"{total // 60} h {total % 60} min"


def y_of(hours):
    return BOTTOM - hours / Y_MAX * (BOTTOM - TOP)


def svg(runs, t):
    names = list(runs)
    step = (RIGHT - LEFT) / len(names)
    x = {r: LEFT + step * (i + 0.5) for i, r in enumerate(names)}
    y = {r: y_of(runs[r]["official_h"]) for r in names}
    won = [r for r in names if runs[r]["won"]]
    record = min(won, key=lambda r: runs[r]["official_h"])

    out = []
    add = out.append
    desc = "; ".join(
        f"run {r[3:]}: {hm(runs[r]['official_h'])}" + ("" if runs[r]["won"] else ", ended without a win")
        for r in names)
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family=\'{FONT}\' role="img" aria-labelledby="t d">')
    add('<title id="t">Time to beat Minecraft, run by run</title>')
    add(f'<desc id="d">Official time per run, from first spawn to the win. {desc}.</desc>')

    # Title and subtitle.
    add(f'<text x="24" y="36" font-size="20" font-weight="600" fill="{t["ink"]}">'
        'Time to beat Minecraft, run by run</text>')
    add(f'<text x="24" y="60" font-size="13" fill="{t["ink2"]}">'
        "Official time from first spawn to the Ender Dragon's death. "
        "Each run inherited the earlier players' files.</text>")

    # Gridlines, y labels and the zero baseline.
    for v in Y_TICKS:
        yy = y_of(v)
        colour = t["axis"] if v == 0 else t["grid"]
        add(f'<line x1="{LEFT}" y1="{yy:.1f}" x2="{RIGHT}" y2="{yy:.1f}" stroke="{colour}" stroke-width="1"/>')
        add(f'<text x="{LEFT - 10}" y="{yy + 4:.1f}" font-size="12" text-anchor="end" '
            f'fill="{t["muted"]}" style="font-variant-numeric: tabular-nums">{v} h</text>')

    # Run names under the axis.
    for r in names:
        add(f'<text x="{x[r]:.1f}" y="{BOTTOM + 26}" font-size="13" text-anchor="middle" '
            f'fill="{t["ink2"]}">Run {r[3:]}</text>')

    # The line joins the winning runs only; a run without a win has no time to win.
    pts = " ".join(f"{x[r]:.1f},{y[r]:.1f}" for r in won)
    add(f'<polyline points="{pts}" fill="none" stroke="{t["series"]}" stroke-width="2" '
        'stroke-linejoin="round" stroke-linecap="round"/>')

    for r in names:
        if runs[r]["won"]:
            add(f'<circle cx="{x[r]:.1f}" cy="{y[r]:.1f}" r="5" fill="{t["series"]}" '
                f'stroke="{t["surface"]}" stroke-width="2"/>')
        else:
            add(f'<circle cx="{x[r]:.1f}" cy="{y[r]:.1f}" r="5" fill="{t["surface"]}" '
                f'stroke="{t["series"]}" stroke-width="2"/>')

    # Direct labels.
    for r in names:
        text = hm(runs[r]["official_h"])
        weight, colour = "400", t["ink"]
        if not runs[r]["won"]:
            text, colour = f"{text}, no win", t["ink2"]
        if r == record:
            text, weight = f"{text}, category record", "600"
        if LABEL_PLACE[r] == "above-right":
            lx, ly, anchor = x[r] + 8, y[r] - 10, "start"
        else:
            lx, ly, anchor = x[r], y[r] - 14, "middle"
        add(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="13" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{colour}">{text}</text>')

    add("</svg>")
    return "\n".join(out) + "\n"


def main():
    runs = json.loads(DATA.read_text())["runs"]
    for theme, t in THEMES.items():
        (HERE / f"run-times-{theme}.svg").write_text(svg(runs, t))
        print("wrote", HERE / f"run-times-{theme}.svg")


if __name__ == "__main__":
    main()
