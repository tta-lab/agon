# Agon — Agent Guide

Agon is a Terminal-Bench 2.0 arena for measuring Lenos against real terminal
tasks, powered by the [Harbor](https://github.com/laude-institute/harbor)
framework.

The purpose is not only to produce a leaderboard number. The working goal is to
run TB2 tasks one by one, learn where Lenos wastes time or fails, and keep a
clear trail from task result to model behavior to possible Lenos improvement.
Official verifier results stay official; local judgement and investigation notes
are recorded separately.

## Architecture

```
agon_bench/
├── adapters/
│   └── lenos.py          # Harbor BaseInstalledAgent for Lenos
├── findings/             # Markdown notes for Lenos improvement leads
└── results/
    ├── tb2-scoreboard.html
    ├── tb2-scoreboard.json
    └── tb2-scoreboard-notes.json
```

A single Python file. Harbor handles everything else — container orchestration,
task provisioning, verification, results.

The adapter teaches Harbor how to install and run Lenos inside any TB 2.0
task container. Harbor provisions the container, calls `install()`, then
calls `run(instruction)`, then runs the task's test suite.

## Essential Commands

```bash
# Run Lenos against a single TB 2.0 task
uv run harbor run -d "terminal-bench@2.0" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  -t terminal-bench/hello-world \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y

# Or use make convenience wrapper
make harbor-run MODEL=deepseek-v4-flash TASK=terminal-bench/hello-world

# Local smoke mode used when API tier/speed makes official timing too tight
make harbor-run MODEL=deepseek-v4-flash TASK=terminal-bench/fix-git \
  LENOS_REASONING_EFFORT=medium TIMEOUT_MULTIPLIER=1.5 N_CONCURRENT=1

# Rebuild the local task dashboard from jobs/
make scoreboard

# Format and lint
make fmt
make lint
```

## Local TB2 Cache

Keep downloaded TB2 task definitions under `.agon-cache/tb2/`, which is
gitignored:

```bash
uv run harbor download terminal-bench@2.0 -o .agon-cache/tb2 --export
```

Use this cache to inspect task names, metadata, timeouts, and instructions
without downloading the dataset again. Do not commit downloaded task contents.

## Evaluation Workflow

Use Agon as a task-by-task lab before attempting full-suite or leaderboard runs.

1. Pick a small task or a small batch from `terminal-bench@2.0`.
2. Run with `make harbor-run`, normally `MODEL=deepseek-v4-flash`.
3. Rebuild the local dashboard with `make scoreboard`.
4. Inspect failed or near-passed runs through `jobs/<job>/<trial>/agent/lenos.txt`
   and verifier output.
5. If the run reveals a Lenos-side improvement lead, add a Markdown note under
   `agon_bench/findings/` and link task, model, job, trial, official reward, and
   local judgement.
6. Keep running cases. Implement fixes later from the strongest repeated
   findings.

When increasing paired Lenos/Codex coverage, track coverage at the task level:
a shared task means the same `terminal-bench/<task>` has at least one Lenos run
and at least one Codex CLI run for the same model/effort comparison. Harbor's
`-n/--n-concurrent` controls concurrent trials inside one Harbor job, not
parallelism across different task names. For cross-task batches, use an outer
runner such as `xargs -P2` and keep each single-task Harbor invocation at
`-n 1`. Always pass a unique `--job-name` for each outer-parallel Harbor
invocation; Harbor's default timestamp job name can collide when two jobs start
in the same second.

The local scoreboard is for smoke coverage and triage. It is not an official
leaderboard submission. Manual labels such as `near_pass_95` may appear in
`tb2-scoreboard-notes.json`, but they must not overwrite official `reward`,
`classification`, or verifier data.

Official leaderboard-style runs have stricter constraints:

- use the official dataset and task set
- do not use local timeout/resource relaxations
- run the required number of trials
- treat Harbor verifier reward as the score

## Adapter — install() lifecycle

1. Install `bubblewrap`, `curl`, and `python3`
2. Download Lenos from GitHub releases, extract to `/usr/local/bin/lenos`
3. Write temenos config to `~/.config/temenos/config.toml`
4. Ensure lenos config dirs exist (`~/.config/lenos`, `~/.local/share/lenos`)

## Adapter — run() lifecycle

1. Escape instruction, build model flag from `self.model_name`
2. Execute: `lenos run -m <model> --usage-json /logs/agent/usage-summary.json <instruction>`
3. Output teed to `/logs/agent/lenos.txt`
4. Parse Lenos' usage summary into Harbor context metadata
5. Harbor runs the task's test suite after `run()` completes

## Credentials and Secrets

Provider credentials are **never** in this repo or baked into images. The host
lenos config is mounted into the container at runtime:

```
agon_bench/lenos/config.json → /root/.config/lenos/config.json (non-secret options)
~/.local/share/lenos         → /root/.local/share/lenos        (provider secrets/registry)
```

`LENOS_DISABLE_PROVIDER_AUTO_UPDATE=1` is set to prevent lenos from trying
to write to a potentially read-only mount or unavailable network.

## Temenos Sandbox

Lenos uses the temenos SDK directly (no daemon). The adapter writes a minimal
temenos config that allows read access to binary paths, the workspace, `/tmp`,
and the non-secret `/root/.config/lenos` config. Write access is limited to
`/app`, `/workspace`, and `/tmp`.

For local TB2 smoke runs, `make harbor-run` currently sets
`LENOS_NO_SANDBOX=1`, so the adapter passes `lenos run --no-sandbox`. This is a
run-time choice, not part of `agon_bench/lenos/config.json`. Use
`LENOS_NO_SANDBOX=0` when testing the Temenos policy itself.

Never add `/root/.local/share/lenos` to Temenos `allow_read`. That directory is
mounted for the Lenos process so it can load provider credentials, but it
contains host secrets and must not be readable from the task-solving sandbox.
Do not allow provider secret env vars such as `OPENAI_*`, `ANTHROPIC_*`,
`DEEPSEEK_*`, or `GOOGLE_*` in the Temenos sandbox unless there is a reviewed,
explicit need.

When a task needs system tools such as TeX, compilers, language runtimes, or
package managers, prefer recording missing sandbox paths as a finding before
expanding the policy. The expected direction is broader read access to
non-secret system install trees and narrow write access to task/cache paths, not
secret mounts.

## Models

Common models for local smoke runs:

```bash
make harbor-run MODEL=deepseek-v4-flash TASK=terminal-bench/fix-git
make harbor-run MODEL=gpt-5.4 TASK=terminal-bench/headless-terminal
```

Model name is passed as-is to `lenos run -m <model>`. Lenos resolves it
against its known providers from the mounted config.
Set reasoning through `LENOS_REASONING_EFFORT=<level>` when needed. Use
`medium` for cheaper smoke passes and higher efforts only when diagnosing a
specific failure.

## Harbor Integration

The adapter lives in this repo but is used via `--agent-import-path`:

```bash
uv run harbor run -d "terminal-bench@2.0" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  -t terminal-bench/hello-world \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y
```

Copy just the `agon_bench/adapters/` directory to use the adapter from any project.

## Findings and Scoreboard

`jobs/` contains raw Harbor output and stays gitignored. The committed local
record is split into:

- `agon_bench/results/tb2-scoreboard.html` for the task dashboard
- `agon_bench/results/tb2-scoreboard.json` for structured run data
- `agon_bench/results/tb2-scoreboard-notes.json` for manual labels/notes
- `agon_bench/findings/*.md` for improvement leads

Add a finding when a run teaches something reusable, for example sandbox path
gaps, tool-state issues, timeout behavior, metrics loss, provider/model
compatibility, or repeated model failure patterns.

Do not add secrets, API keys, or host Lenos local-share contents to findings,
scoreboard notes, commits, or PR descriptions.

## Git Conventions

- Conventional commits: `feat(agon):`, `fix(agon):`, `chore(agon):`, `refactor(agon):`, `docs(agon):`
- Never push to main/master directly — use feature branches and PRs
- `ttal push` for git push (handles auth)
- `ttal pr` for PR operations

## Code Conventions

- **Python**: use `uv run python`, `uv run pytest`, and `uv run ruff`.
  No type annotations on internal functions.
  Single module per adapter.
- **Shell**: `set -euo pipefail`. `[[ ]]` for conditionals. Lowercase local vars.
