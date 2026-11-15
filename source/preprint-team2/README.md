# Preprint: "Two Claude Fable 5.2 agents and two people beat Minecraft in 1 hour 43 minutes"

The write-up of the second team run, `2026-11-14-2158-team` (team mode: two Fable 5.2 low agents, FableFox and FableFire, and two people). A companion to the first team paper and `../preprint-run5/`. Team mode is a separate experiment, so its time can't be compared with the solo runs'. `main.pdf` is the compiled copy.

- Naming rule (the owner's): the people are only Human 1 and Human 2, and the agents are always written in full, FableFox and FableFire, quotes included.
- `scripts/run_data.py` reads the run's records into `data/team2.json` (system python3). It replaces the people's account names everywhere. The chat log itself is not written to the data file; the paper quotes a few lines, with the agents' names in full.
- `scripts/make_figures.py` draws `figures/fig*.pdf` (needs matplotlib and pillow; PNG previews go to `figures/preview/`, not in git). Icons come from `../preprint/figures/icons/` (Pixel Perfection, CC BY-SA 4.0).
- Section 8, "Usage statistics", has the tokens and cost table, the context-size figure (fig4) and the 5-hour and 7-day usage-window figure (fig5).
- No camera frames are shown: they show the people's account names.

Build (TinyTeX): `pdflatex main && bibtex main && pdflatex main && pdflatex main`.
