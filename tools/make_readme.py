"""Write the README's paper list from runs.json and each paper's text version.

    python3 tools/make_readme.py            # rewrite the list between the markers
    python3 tools/make_readme.py --check    # change nothing; fail if the README is out of date
    python3 tools/make_readme.py --check --description "..."   # also check a repo description

The check fails when the list is stale, when the README or the description
doesn't name the record time or the number of papers in runs.json, or when a
file the README links to is missing.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- papers:start (written by tools/make_readme.py from runs.json; don't edit by hand) -->", "<!-- papers:end -->"
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]


def abstract(folder):
    text = (ROOT / "source" / folder / "paper.md").read_text()
    title = text.splitlines()[0].lstrip("# ").strip()
    m = re.search(r"\*\*Ben Batsuk\*\*\n\n\*\*(.+?)\*\*\n", text, re.S)
    return title, " ".join(m.group(1).split())


def block(data):
    out = [START, ""]
    for r in data["runs"]:
        if not r["folder"]:
            continue
        title, abst = abstract(r["folder"])
        src = f"source/{r['folder']}"
        links = [f"[PDF]({r['pdf']})", f"[text]({src}/paper.md)", f"[LaTeX]({src}/main.tex)",
                 f"[data]({src}/data/)", f"[figures]({src}/figures/)", f"[scripts]({src}/scripts/)"]
        if r["server_log_excerpt"]:
            links.append(f"[server log excerpt]({r['server_log_excerpt']})")
        inherited = ", ".join(r["inherited"]) or "nothing"
        out += [f"### {r['attempt']}: {title}", "",
                " · ".join(links), "",
                f"- **Result:** {r['official_time']}; deaths: {r['deaths']}; programs: {r['programs']}",
                f"- **Setup:** {r['model']}, effort {r['effort']}; {r['players']}; seed: {r['seed']}; inherited files from: {inherited}",
                f"- **Caveats:** {r['caveats']}", "",
                f"**Abstract.** {abst}", ""]
    out.append(END)
    return "\n".join(out)


def main():
    data = json.loads((ROOT / "runs.json").read_text())
    readme = (ROOT / "README.md").read_text()
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block(data), readme, flags=re.S)
    if "--check" not in sys.argv:
        (ROOT / "README.md").write_text(new)
        return 0
    problems = []
    if new != readme:
        problems.append("the paper list is stale: run python3 tools/make_readme.py")
    papers = sum(1 for r in data["runs"] if r["pdf"])
    texts = {"README.md": readme}
    if "--description" in sys.argv:
        texts["the repo description"] = sys.argv[sys.argv.index("--description") + 1]
    for name, text in texts.items():
        if data["record"]["official_time"] not in text:
            problems.append(f"{name} doesn't name the record time {data['record']['official_time']}")
        if not re.search(rf"\b{WORDS[papers]} (preprints|PDFs)", text, re.I):
            problems.append(f"{name} doesn't say '{WORDS[papers]} preprints'")
    for r in data["runs"]:
        if r["won"] and r["official_time"] not in readme:
            problems.append(f"README.md lacks {r['attempt']}'s time {r['official_time']}")
    for target in re.findall(r"\]\((?!https?:|#)([^)]+)\)", readme):
        if not (ROOT / target).exists():
            problems.append(f"README.md links to a missing file: {target}")
    for p in problems:
        print("FAIL:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
