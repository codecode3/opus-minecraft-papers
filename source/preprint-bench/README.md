# Preprint: "Claude Opus 5.5 against Claude Fable 5.2 on one Minecraft seed: a subscription's usage limit stopped both agents at 5 hours 17 minutes, before either beat the game"

The write-up of the model benchmark pair `2026-11-10-1904-bench` (arms `-opus` and `-fable`), a companion to `../preprint-run4/`. Neither arm won: both agents were refused by the shared subscription's 5-hour usage limit at 5:16:50 on the clock, and the owner ended the pair. `main.pdf` is the compiled copy.

- `scripts/run_data.py` reads both arms' records into `data/bench.json` (system python3). All times use the official clock, from the first spawn.
- `scripts/make_figures.py` draws `figures/fig*.pdf` from `data/bench.json` (needs matplotlib; PNG previews go to `figures/preview/`, not in git).
- Each arm's story in the paper is told from its agent's text, programs and `memory/02-lessons.md`, with times from `events.jsonl`.
- The Opus arm's cost is the session's own total, $53.62. `scripts/compare-bench.py` shows $107.24 for it because it counts a repeated result line twice; that bug is not fixed.

Build (TinyTeX): `pdflatex main && bibtex main && pdflatex main && pdflatex main`.
