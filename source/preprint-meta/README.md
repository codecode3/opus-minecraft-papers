# Preprint: "Meta-space optimization: reinforcement learning and Bayesian statistics with a human as the outer loop to beat Minecraft with a single agent in a world record time"

A methods paper on the planning conversation of 2026-11-11 behind run 5, written on 2026-11-15 at the owner's request from a second, read-only conversation that named what the owner had been doing ("the things I was doing in meta space"). It is a companion to `../preprint-run5/`, which tells the same day as history. `main.pdf` is the compiled copy. It was published to the public papers repo (`../opus-minecraft-papers`) on 2026-11-15 at the owner's request; publishing goes only through `../github-publish/publish.sh`.

- `scripts/session_data.py` reads the planning session's log into `data/session.json` (system python3): context size per request, compactions, and the time, length and source of each prompt. No prompt text is copied. Its default input is the private copy in `../preprint-run5/private/`, which is not in git.
- `scripts/make_figures.py` draws `figures/fig*.pdf` (needs matplotlib; PNG previews go to `figures/preview/`, not in git). The estimates in `fig2_estimate` are typed in from the plan's text at each commit, as in the run 5 paper, and were checked against `git show <commit>:run-5-plan.md` for the five plan commits of the day.
- `data/posterior.json` is a copy of `../preprint-run5/data/posterior.json`.
- The prompts quoted in the paper were read from the session log; the stage table and the account of each plan edit are from the run 5 paper and the plan's git history.
- This paper is on a planning session, not on an agent's run, so it shows the planning agent's context window through the day. The 5-hour usage window is not drawn: the interactive session's log has no usage share per request.

Build (TinyTeX): `pdflatex main && bibtex main && pdflatex main && pdflatex main`.
