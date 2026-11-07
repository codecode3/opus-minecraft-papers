# Preprint: "A single Claude Opus 5.5 agent beats Minecraft"

The write-up of run `2026-11-01-1211`, laid out like the original paper (arXiv 2610.22319). `main.pdf` is the compiled copy.

- `scripts/run_data.py` reads the run's records into `data/run.json` (system python3).
- `scripts/make_figures.py` draws `figures/fig*.pdf` from `data/run.json` (needs matplotlib and pillow; PNG previews go to `figures/preview/`, not in git).
- `figures/icons/` and `figures/frames/` are Pixel Perfection icons and camera frames (CC BY-SA 4.0).

Build (TinyTeX): `pdflatex main && bibtex main && pdflatex main && pdflatex main`.

arXiv upload (it compiles from `main.bbl`, no bibtex needed):

    tar czf arxiv.tar.gz main.tex main.bbl refs.bib figures/fig*.pdf figures/frames/*.jpg
