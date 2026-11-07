# Preprint: "A Claude Opus 5.5 agent, given three earlier players' files, beats Minecraft in 6 hours 51 minutes and misses its 5-hour plan"

The write-up of run `2026-11-06-2240`, a companion to `../preprint/` (run `2026-11-01-1211`) and `../preprint-run2/` (run `2026-11-04-1901`). It also describes run `2026-11-06-0651`, which has no paper of its own. `main.pdf` is the compiled copy.

- `scripts/run_data.py` reads the four runs' records into `data/run4.json` (system python3). All times use the official clock, from the first spawn, unless the name says otherwise.
- `scripts/make_figures.py` draws `figures/fig*.pdf` from `data/run4.json` (needs matplotlib and pillow; PNG previews go to `figures/preview/`, not in git). It takes its icons from `../preprint/figures/icons/`.
- `figures/frames/` holds camera frames from this run. The icons are Pixel Perfection (CC BY-SA 4.0), as in the first paper.
- The working and recovering stretches in `run_data.py` are labelled by hand from the player's text and programs, good to about 3 minutes either way.

Build (TinyTeX): `pdflatex main && bibtex main && pdflatex main && pdflatex main`.

arXiv upload (it compiles from `main.bbl`, no bibtex needed):

    tar czf arxiv.tar.gz main.tex main.bbl refs.bib figures/fig*.pdf figures/frames/*.jpg
