# Preprint: "Two Claude Opus 5.5 agents and two people beat Minecraft in 4 hours 36 minutes"

The write-up of the official team run `2026-11-07-2154-team` (team mode: two agents, FoxglenOpus and VoidmothOpus, and two people), a companion to `../preprint/`, `../preprint-run2/` and `../preprint-run4/`. Team mode is a separate experiment, so its times can't be compared with the solo runs'. `main.pdf` is the compiled copy.

- `scripts/run_data.py` reads the run's records (and the earlier runs' milestones) into `data/team.json` (system python3). All times use the official clock, from the first agent's spawn, unless the name says otherwise. The people appear only as Human 1 and Human 2: the script replaces their account names everywhere, chat quotes included.
- The dragon's damage sources come from rules applied to the agents' fight logs (`run_data.py` docstring and the paper's appendix), not from a server-side record.
- `scripts/make_figures.py` draws `figures/fig*.pdf` from `data/team.json` (needs matplotlib and pillow; PNG previews go to `figures/preview/`, not in git). It takes its icons from `../preprint/figures/icons/`.
- `figures/frames/` holds six camera frames from this run; the one camera followed FoxglenOpus. The icons are Pixel Perfection (CC BY-SA 4.0), as in the first paper.

Build (TinyTeX): `pdflatex main && bibtex main && pdflatex main && pdflatex main`.

Figures: `uv run --with matplotlib --with pillow python3 scripts/make_figures.py`.

arXiv upload (it compiles from `main.bbl`, no bibtex needed):

    tar czf arxiv.tar.gz main.tex main.bbl refs.bib figures/fig*.pdf figures/frames/*.jpg
