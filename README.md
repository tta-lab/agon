# Agon

Terminal-Bench 2.1 arena for measuring [Lenos](https://github.com/tta-lab/lenos)
on real terminal tasks, powered by the [Harbor](https://github.com/laude-institute/harbor)
framework.

## What this repo contains

A single Harbor **agent adapter** (`agon_bench/adapters/lenos.py`) that teaches
Harbor how to install and run Lenos inside any Terminal-Bench task container.

Harbor handles everything else: container orchestration, task provisioning,
verification, and result collection.

## Requirements

- **uv** with Python 3.12+ dependencies synced:
  ```bash
  uv sync
  ```
- **Docker** — Harbor uses Docker for task containers
- **Lenos config** — Agon supplies minimal non-secret options from
  `agon_bench/lenos/config.json`; provider secrets/registry come from
  `~/.local/share/lenos/`

## Quickstart

```bash
# Run Lenos against a single TB 2.1 task
uv run harbor run -d "terminal-bench/terminal-bench-2-1" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  -t terminal-bench/hello-world \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y

# Or use make (convenience wrapper)
make harbor-run MODEL=deepseek-v4-flash TASK=terminal-bench/hello-world

# Validate a Lenos ATIF trajectory artifact
make validate-trajectory TRAJECTORY=/path/to/trajectory.json
```

`make harbor-run` and `make codex-run` default to `BENCHMARK=tb2.1` and
`DATASET=terminal-bench/terminal-bench-2-1`. To run TB2.0 explicitly, pass
`BENCHMARK=tb2.0 DATASET=terminal-bench@2.0`.

## How it works

1. Harbor provisions a Docker container for the task
2. The adapter **installs** Lenos from GitHub releases, writes temenos config,
   and ensures config dirs exist
3. Agon's minimal config and host provider state are **mounted** into the
   container — API keys stay out of the repo and are never baked into images
   or env vars
4. Harbor passes the task instruction to the adapter's `run()` method
5. The adapter writes the Harbor instruction to `/tmp/agon-task.md`, then runs
   `lenos run -m <model> --context-file /tmp/agon-task.md --trajectory-json /logs/agent/trajectory.json Start.`
   inside the container. Set reasoning with `LENOS_REASONING_EFFORT=<level>`
   when needed. The Makefile passes `--no-sandbox` by default for TB2 smoke
   runs; override with `LENOS_NO_SANDBOX=0` to test the Temenos sandbox path.
6. Harbor runs the task's test script and records the result

## Adding the adapter to your project

```bash
# Copy just the adapter directory
cp -r agon_bench/adapters /path/to/your/project/

# Then run from your project directory
uv run harbor run -d "terminal-bench/terminal-bench-2-1" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  -t terminal-bench/hello-world \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y
```

## Harbor integration for CI

```bash
# Run matching tasks from the dataset
uv run harbor run -d "terminal-bench/terminal-bench-2-1" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  --include-task-name "python-*" \
  --n-tasks 3 \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y

# Run the full dataset
uv run harbor run -d "terminal-bench/terminal-bench-2-1" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y
```

## Code conventions

- **Python**: `uv run pytest`, `uv run ruff`, or the `make` wrappers
- **Git**: conventional commits — `feat(agon):`, `fix(agon):`, `chore(agon):`
