# Preprint: "A Claude Fable 5.2 agent at low effort beats Minecraft in 4 hours 40 minutes, a world record for a single AI agent on a random seed, inside a 5-hour plan that was given even odds"

The write-up of run 5, `2026-11-11-2058`: a win at 4:39:54 from first spawn with 4 deaths, a companion to `../preprint-run4/` and `../preprint-bench/`. It opens with a preamble on the planning conversation, at the owner's request (`../run-5-paper-notes.md`). `main.pdf` is the compiled copy.

- `scripts/run_data.py` reads the run's records into `data/run5.json` (system python3). Times use the official clock, from the first spawn. The stage marks and recovery spans in it are set by hand from the player's messages, good to about a minute.
- `scripts/make_figures.py` draws `figures/fig*.pdf` from `data/run5.json` and `data/posterior.json` (needs matplotlib; PNG previews go to `figures/preview/`, not in git). The estimates in figure `fig1_estimate` are typed in from the plan's text at each commit.
- `data/posterior.json` is the output of `python3 bayes/update.py bayes/observations/2026-11-11-2058.json`, and of the same with `data/obs-crossing-with-food.json` (the food work left inside the crossing, no surprise).
- `private/` holds a copy of the planning session's log. It is not in git and must not be published: it has local paths and dashboard links.
- In the paper the steps figure is Figure 1 and the estimate figure is Figure 2; the file names follow the order they were drawn in.

Build (TinyTeX): `pdflatex main && bibtex main && pdflatex main && pdflatex main`.
