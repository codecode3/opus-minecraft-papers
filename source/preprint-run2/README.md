# Preprint: "A second Claude Opus 5.5 agent, given the first one's files, beats Minecraft in nine hours"

The write-up of run `2026-11-04-1901`, a companion to `../preprint/` (run `2026-11-01-1211`). `main.pdf` is the compiled copy.

- `scripts/run_data.py` reads both runs' records into `data/run2.json` (system python3).
- `scripts/make_figures.py` draws `figures/fig*.pdf` from `data/run2.json` (needs matplotlib and pillow; PNG previews go to `figures/preview/`, not in git). It takes its icons from `../preprint/figures/icons/`.
- `figures/frames/` holds camera frames from this run. The icons are Pixel Perfection (CC BY-SA 4.0), as in the first paper.

Build (TinyTeX): `pdflatex main && bibtex main && pdflatex main && pdflatex main`.

arXiv upload (it compiles from `main.bbl`, no bibtex needed):

    tar czf arxiv.tar.gz main.tex main.bbl refs.bib figures/fig*.pdf figures/frames/*.jpg
