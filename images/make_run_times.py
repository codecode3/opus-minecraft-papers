"""Draw the README chart of official time per run, in a light and a dark version.

Reads each run's official time (first spawn to the win, or to the end of a run
without one), whether it won, and the Gemini team's time from the run 4
paper's data, then writes run-times-light.svg and run-times-dark.svg next to
this script.

    python3 images/make_run_times.py
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "source" / "preprint-run4" / "data" / "run4.json"
TZ = ZoneInfo("America/Chicago")

# Colours: one series, validated against GitHub's page backgrounds.
THEMES = {
    "light": dict(surface="#ffffff", ink="#0b0b0b", ink2="#52514e", muted="#6f6d68",
                  grid="#e1e0d9", axis="#c3c2b7", series="#2a78d6", area=0.10),
    "dark": dict(surface="#0d1117", ink="#f0efec", ink2="#c3c2b7", muted="#9a9890",
                 grid="#2c2c2a", axis="#4a4a46", series="#3987e5", area=0.16),
}
FONT = 'system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif'

W, H = 800, 540
LEFT, RIGHT, TOP, BOTTOM = 64, 776, 110, 440
Y_MAX = 70  # hours at the top of the plot
Y_TICKS = [0, 20, 40, 60]


def hm(hours):
    """6.8478 -> '6 h 51 min'."""
    total = round(hours * 60)
    return f"{total // 60} h {total % 60} min"


def hms(hours):
    """6.8442 -> '6 h 50 min 39 s'."""
    total = round(hours * 3600)
    return f"{total // 3600} h {total % 3600 // 60} min {total % 60} s"


def y_of(hours):
    return BOTTOM - hours / Y_MAX * (BOTTOM - TOP)


def day(utc):
    return datetime.fromisoformat(utc).astimezone(TZ)


def svg(runs, team_h, t):
    names = list(runs)
    step = (RIGHT - LEFT) / len(names)
    x = {r: LEFT + step * (i + 0.5) for i, r in enumerate(names)}
    h = {r: runs[r]["official_h"] for r in names}
    y = {r: y_of(h[r]) for r in names}
    won = [r for r in names if runs[r]["won"]]
    first, record = won[0], min(won, key=h.get)
    start, end = day(runs[names[0]]["spawn_utc"]), day(runs[record]["end_utc"])
    dates = f"{start.day} to {end.day} {end:%B %Y}" if start.month == end.month else \
        f"{start.day} {start:%B} to {end.day} {end:%B %Y}"

    out = []
    add = out.append

    def text(x_, y_, s, size, fill, anchor="start", weight="400", extra=""):
        add(f'<text x="{x_:.1f}" y="{y_:.1f}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}"{extra}>{s}</text>')

    desc = "; ".join(f"run {r[3:]}: {hm(h[r])}" + ("" if runs[r]["won"] else ", ended without a win")
                     for r in names)
    count = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}.get(len(names), str(len(names)))
    title = f"From {hm(h[first])} to {hm(h[record])} in {count} runs"
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family=\'{FONT}\' role="img" aria-labelledby="t d">')
    add(f'<title id="t">{title}</title>')
    add(f'<desc id="d">Official time per run, from first spawn to the win. {desc}. '
        f'A team of four Gemini 4 Argon agents took {hm(team_h)}.</desc>')

    # Title and subtitle.
    text(24, 38, title, 22, t["ink"], weight="600")
    text(24, 64, f"Official time from first spawn to the Ender Dragon's death, {dates}.", 14, t["ink2"])
    text(24, 84, "Each Claude Opus 5.5 player inherited the files of the players before it.", 14, t["ink2"])

    # Gridlines, y labels and the zero baseline.
    for v in Y_TICKS:
        yy = y_of(v)
        add(f'<line x1="{LEFT}" y1="{yy:.1f}" x2="{RIGHT}" y2="{yy:.1f}" '
            f'stroke="{t["axis"] if v == 0 else t["grid"]}" stroke-width="1"/>')
        text(LEFT - 10, yy + 4, f"{v} h", 13, t["muted"], anchor="end",
             extra=' style="font-variant-numeric: tabular-nums"')

    # Run names under the axis.
    for r in names:
        text(x[r], BOTTOM + 28, f"Run {r[3:]}", 14, t["ink2"], anchor="middle")

    # Area and line join the winning runs only; a run without a win has no time to win.
    pts = [(x[r], y[r]) for r in won]
    poly = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    add(f'<polygon points="{poly} {pts[-1][0]:.1f},{BOTTOM} {pts[0][0]:.1f},{BOTTOM}" '
        f'fill="{t["series"]}" fill-opacity="{t["area"]}"/>')

    # Reference: the Gemini team, in the same game setup.
    yr = y_of(team_h)
    add(f'<line x1="{LEFT}" y1="{yr:.1f}" x2="{RIGHT}" y2="{yr:.1f}" stroke="{t["muted"]}" '
        'stroke-width="1.5" stroke-dasharray="6 5"/>')
    text(RIGHT, yr - 8, f"Team of four Gemini 4 Argon agents: {hm(team_h)}", 13, t["ink2"], anchor="end")

    add(f'<polyline points="{poly}" fill="none" stroke="{t["series"]}" stroke-width="2" '
        'stroke-linejoin="round" stroke-linecap="round"/>')

    for r in names:
        tip = f"Run {r[3:]}: {hm(h[r])}" + ("" if runs[r]["won"] else ", no win")
        fill, ring = (t["series"], t["surface"]) if runs[r]["won"] else (t["surface"], t["series"])
        add(f'<g><title>{tip}</title><circle cx="{x[r]:.1f}" cy="{y[r]:.1f}" r="5.5" '
            f'fill="{fill}" stroke="{ring}" stroke-width="2"/></g>')

    # Direct labels. Run 2's goes up and to the right to clear the line from run 1;
    # the record gets two lines.
    for r in names:
        if r == record:
            text(x[r], y[r] - 32, hm(h[r]), 14, t["ink"], anchor="middle", weight="600")
            text(x[r], y[r] - 15, "category record", 14, t["ink2"], anchor="middle")
        elif not runs[r]["won"]:
            text(x[r], y[r] - 14, f"{hm(h[r])}, no win", 14, t["ink2"], anchor="middle")
        elif r == first:
            text(x[r], y[r] - 14, hm(h[r]), 14, t["ink"], anchor="middle")
        else:
            text(x[r] + 9, y[r] - 10, hm(h[r]), 14, t["ink"])

    # Headline factors side by side in the empty upper right: the record against
    # run 1, and against the Gemini team. The team's clock starts at its first
    # program, so the record is put on that clock for the second one.
    vs_first = h[first] / h[record]
    record_from_program = h[record] - runs[record]["spawn_to_first_program_s"] / 3600
    vs_team = team_h / record_from_program
    for xa, factor, sub in ((500, vs_first, f"run {record[3:]} against run {first[3:]}"),
                            (RIGHT, vs_team, f"run {record[3:]} against the Gemini team")):
        text(xa, 200, f"{factor:.1f}× faster", 30, t["ink"], anchor="end", weight="700")
        text(xa, 222, sub, 14, t["ink2"], anchor="end")

    # Source note for the reference line.
    text(24, H - 32, "Gemini team: Faldor et al. (2026), arXiv 2610.22319, timed from its first program "
         "rather than first spawn.", 12, t["muted"])
    text(24, H - 14, f"The {vs_team:.1f}× puts run {record[3:]} on that clock too "
         f"({hms(record_from_program)} from its first program).", 12, t["muted"])

    add("</svg>")
    return "\n".join(out) + "\n"


def main():
    data = json.loads(DATA.read_text())
    for theme, t in THEMES.items():
        (HERE / f"run-times-{theme}.svg").write_text(svg(data["runs"], data["team"]["win_h"], t))
        print("wrote", HERE / f"run-times-{theme}.svg")


if __name__ == "__main__":
    main()
