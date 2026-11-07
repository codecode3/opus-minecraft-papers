# Opus plays Minecraft: three papers

Three preprints by Ben Batsuk on Claude Opus 5.5 agents defeating the Ender Dragon in Minecraft Java Edition 1.20.4, on Easy difficulty, in randomly generated worlds. Each agent plays alone by writing Mineflayer programs, and each one after the first inherits the files of the players before it. The environment copies the one in [Faldor et al. (2026)](https://arxiv.org/abs/2610.22319).

| Attempt | Paper | Official time | Deaths | Programs |
| --- | --- | --- | --- | --- |
| Run 1 | [A single Claude Opus 5.5 agent beats Minecraft](preprint/main.pdf) | 60:50:46 | 115 | 5,879 |
| Run 2 | [A second Claude Opus 5.5 agent, given the first one's files, beats Minecraft in nine hours](preprint-run2/main.pdf) | 9:16:17 | 16 | 780 |
| Run 3 | No paper of its own; described in the run 4 paper | No win, ended at 10:58:17 | 34 | 741 |
| Run 4 | [A Claude Opus 5.5 agent, given three earlier players' files, beats Minecraft in 6 hours 51 minutes and misses its 5-hour plan](preprint-run4/main.pdf) | 6:50:52 | 10 | 671 |

Official times run from the player's first spawn to the win, as recomputed in the run 4 paper. The first two papers report their times from the first program: 60:49 and 9:07.

## What's here

Each folder holds one paper:

- `main.pdf`: the compiled paper
- `main.tex`, `refs.bib`, `main.bbl`: its source
- `data/`: the measurements behind its numbers and figures
- `figures/`: the figures
- `scripts/`: `run_data.py` computes `data/` from the run records, and `make_figures.py` draws the figures from `data/` (run 1's also reads one run record)

To build a paper, run this in its folder: `pdflatex main && bibtex main && pdflatex main && pdflatex main`.

The run records (programs, events, server logs, camera frames and transcripts) are not public, so `run_data.py` and run 1's `make_figures.py` can't be rerun from this repo. The worlds' seeds are withheld.

The item icons and camera renders use the open-source [Pixel Perfection](https://modrinth.com/resourcepack/pixel-perfection-legacy) texture pack by XSSheep and Nova_Wostra (CC BY-SA 4.0), not Minecraft's textures. Minecraft is a registered trademark of Mojang Synergies AB / Microsoft Corporation. This independent research is not approved by or affiliated with Mojang or Microsoft.
