# Agon — Agent Guide

Agon is a Terminal-Bench 2.0 arena for measuring Lenos against real terminal
tasks, powered by the [Harbor](https://github.com/laude-institute/harbor)
framework.

## Architecture

```
agon_bench/
└── adapters/
    └── lenos.py          # Harbor BaseInstalledAgent for Lenos
```

A single Python file. Harbor handles everything else — container orchestration,
task provisioning, verification, results.

The adapter teaches Harbor how to install and run Lenos inside any TB 2.0
task container. Harbor provisions the container, calls `install()`, then
calls `run(instruction)`, then runs the task's test suite.

## Essential Commands

```bash
# Run Lenos against a single TB 2.0 task
harbor run -d "terminal-bench-2.0==head" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-pro \
  --task-id hello-world \
  -v ./agon_bench/lenos/config.json:/root/.config/lenos/config.json \
  -v ~/.local/share/lenos:/root/.local/share/lenos

# Or use make convenience wrapper
make harbor-run MODEL=deepseek-v4-pro TASK=hello-world

# Format and lint
make fmt
make lint
```

## Adapter — install() lifecycle

1. `apt-get bubblewrap curl` (sandbox deps)
2. Download lenos binary from GitHub releases, extract to `/usr/local/bin/lenos`
3. Write temenos config to `~/.config/temenos/config.toml`
4. Ensure lenos config dirs exist (`~/.config/lenos`, `~/.local/share/lenos`)

## Adapter — run() lifecycle

1. Escape instruction, build model flag from `self.model_name`
2. Execute: `lenos run --quiet -m <model> <instruction>`
3. Output teed to `/logs/agent/lenos.txt`
4. Harbor runs the task's test suite after `run()` completes

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

Never add `/root/.local/share/lenos` to Temenos `allow_read`. That directory is
mounted for the Lenos process so it can load provider credentials, but it
contains host secrets and must not be readable from the task-solving sandbox.
Do not allow provider secret env vars such as `OPENAI_*`, `ANTHROPIC_*`,
`DEEPSEEK_*`, or `GOOGLE_*` in the Temenos sandbox unless there is a reviewed,
explicit need.

## Models

Two primary models for benchmarking:

```bash
harbor run ... -m gpt-5.5       # OpenAI
harbor run ... -m deepseek-v4-pro  # DeepSeek
```

Model name is passed as-is to `lenos run -m <model>`. Lenos resolves it
against its known providers from the mounted config.

## Harbor Integration

The adapter lives in this repo but is used via `--agent-import-path`:

```bash
harbor run -d "terminal-bench-2.0==head" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-pro \
  --task-id hello-world \
  -v ./agon_bench/lenos/config.json:/root/.config/lenos/config.json \
  -v ~/.local/share/lenos:/root/.local/share/lenos
```

Copy just the `agon_bench/adapters/` directory to use the adapter from any project.

## Git Conventions

- Conventional commits: `feat(agon):`, `fix(agon):`, `chore(agon):`, `refactor(agon):`, `docs(agon):`
- Never push to main/master directly — use feature branches and PRs
- `ttal push` for git push (handles auth)
- `ttal pr` for PR operations

## Code Conventions

- **Python**: ruff for format and lint. No type annotations on internal functions.
  Single module per adapter.
- **Shell**: `set -euo pipefail`. `[[ ]]` for conditionals. Lowercase local vars.
