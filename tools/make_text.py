"""Write a Markdown version of each paper next to its LaTeX source.

For every folder under source/ this writes paper.md from main.tex (pandoc,
with the citations resolved from refs.bib) and a PNG of each PDF figure in
figures/png/, so the text and figures render on GitHub and can be read by
tools that can't open a PDF. The PDF stays the version of record.

    python3 tools/make_text.py          # needs pandoc and PyMuPDF (pip install pymupdf)
"""
import re
import subprocess

import pymupdf as fitz  # PyMuPDF
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF_NAMES = {
    "preprint": "Run-1-Opus-5.5-beats-Minecraft-in-60h51m.pdf",
    "preprint-run2": "Run-2-Opus-5.5-beats-Minecraft-in-9h16m.pdf",
    "preprint-run4": "Run-4-Opus-5.5-beats-Minecraft-in-6h51m.pdf",
    "preprint-team": "Team-run-Opus-5.5-agents-and-people-beat-Minecraft-in-4h36m.pdf",
    "preprint-bench": "Benchmark-Opus-5.5-vs-Fable-5.2-stopped-by-usage-limit-at-5h17m.pdf",
    "preprint-run5": "Run-5-Fable-5.2-beats-Minecraft-in-4h40m.pdf",
    "preprint-team2": "Team-run-2-Fable-5.2-agents-and-people-beat-Minecraft-in-1h43m.pdf",
}


def png_of(folder, rel):
    """figures/x.pdf -> figures/png/x.png, drawn if missing or older."""
    src = folder / rel
    out = folder / "figures" / "png" / (Path(rel).stem + ".png")
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        out.parent.mkdir(parents=True, exist_ok=True)
        page = fitz.open(src)[0]
        page.get_pixmap(matrix=fitz.Matrix(1600 / page.rect.width, 1600 / page.rect.width), alpha=False).save(out)
    return out.relative_to(folder).as_posix()


def convert(folder):
    md = subprocess.run(
        ["pandoc", "-f", "latex", "-t", "gfm", "--wrap=none", "--citeproc", "--bibliography", "refs.bib", "main.tex"],
        cwd=folder, check=True, capture_output=True, text=True).stdout

    def figure(m):
        return f'<img src="{png_of(folder, m.group(1))}" alt="" width="100%">'
    md = re.sub(r'<embed src="(figures/[^"]+\.pdf)"[^>]*/>', figure, md)
    md = re.sub(r'!\[([^\]]*)\]\((figures/[^)]+\.pdf)\)', lambda m: f"![{m.group(1)}]({png_of(folder, m.group(2))})", md)

    title = re.match(r"\*\*(.+?)\*\*\n", md, re.S)
    head = f"# {' '.join(title.group(1).split())}\n" if title else ""
    body = md[title.end():] if title else md
    note = (f"> Text version of the paper, made from `main.tex` by `tools/make_text.py`. "
            f"The PDF is the version of record: [{PDF_NAMES[folder.name]}](../../{PDF_NAMES[folder.name]}). "
            f"Source: [main.tex](main.tex), data: [data/](data/).\n")
    (folder / "paper.md").write_text(head + "\n" + note + body)
    return len(md)


if __name__ == "__main__":
    for name in PDF_NAMES:
        print(name, convert(ROOT / "source" / name), "characters")
