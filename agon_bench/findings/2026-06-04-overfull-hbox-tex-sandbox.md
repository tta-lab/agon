# TeX Tools Need Broader System Read/Cache Support

## Run

- Task: `terminal-bench/overfull-hbox`
- Model: `deepseek-v4-flash`
- Job: `2026-06-04__19-40-39`
- Trial: `overfull-hbox__dXEGGsn`
- Official reward: `0.0`
- Local status: `near_pass_95`

## What Happened

The task image already installs `texlive-latex-base`. The agent still spent most
of the run trying to repair the TeX runtime before solving the task:

- rebuilt or searched for `pdflatex.fmt`
- changed `TEXINPUTS`
- created or copied `pdftex.map`
- worked around kpathsea/font-map lookup
- used temporary `FORMATS`, `TEXFONTMAPS`, and font paths

The final artifact compiled and removed the `Overfull \hbox` warnings. The
official verifier failed only because `input.tex` changed `Middle` to `Hub`.
The verifier is case-sensitive and `synonyms.txt` only allows lowercase
`middle`/`hub`.

## Why It Matters

This suggests the current Temenos policy is too narrow for system-tool tasks.
The executable path may be visible, but tools like TeX also need read access to
system data trees and sometimes write access to user cache trees.

Relevant paths for TeX-like workloads include:

- `/usr/share/texlive`
- `/usr/share/texmf`
- `/var/lib/texmf`
- `/etc/texmf`
- `/usr/share/fonts`
- `/var/lib/tex-common`
- `/root/.texlive2023`

The important boundary still holds: do not allow the sandbox to read
`/root/.local/share/lenos`, because that mount contains provider secrets.

## Lenos/Temenos Improvement Lead

Consider a Harbor/task-container sandbox profile that:

- allows read access to normal system install trees needed by task tools
- allows write access to bounded user cache paths such as `/tmp` and selected
  tool cache directories
- keeps provider secrets and host Lenos state outside sandbox read access
- surfaces sandbox denied-path diagnostics clearly in the transcript

## Follow-Up Check

Run another TeX or document-processing task after widening non-secret system
read/cache access. Compare:

- agent time spent before first useful task edit
- number of environment-repair commands
- verifier result
- token/cost usage
