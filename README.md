# Agon

Terminal-Bench 2.0 arena for measuring [Lenos](https://github.com/tta-lab/lenos)
on real terminal tasks, powered by the [Harbor](https://github.com/laude-institute/harbor)
framework.

## What this repo contains

A single Harbor **agent adapter** (`agon_bench/adapters/lenos.py`) that teaches
Harbor how to install and run Lenos inside any TB 2.0 task container.

Harbor handles everything else: container orchestration, task provisioning,
verification, and result collection.

## Requirements

- **Python 3.12+** with [Harbor](https://pypi.org/project/harbor/) installed:
  ```bash
  uv tool install harbor
  # or: pip install harbor
  ```
- **Docker** — Harbor uses Docker for task containers
- **Lenos config** — Agon supplies minimal non-secret options from
  `agon_bench/lenos/config.json`; provider secrets/registry come from
  `~/.local/share/lenos/`

## Quickstart

```bash
# Run Lenos against a single TB 2.0 task
harbor run -d "terminal-bench-2.0==head" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-pro \
  --task-id hello-world \
  -v ./agon_bench/lenos/config.json:/root/.config/lenos/config.json \
  -v ~/.local/share/lenos:/root/.local/share/lenos

# Or use make (convenience wrapper)
make harbor-run MODEL=deepseek-v4-pro TASK=hello-world
```

## How it works

1. Harbor provisions a Docker container for the task
2. The adapter **installs** Lenos: downloads the binary from GitHub releases,
   writes temenos config, ensures config dirs exist
3. Agon's minimal config and host provider state are **mounted** into the
   container — API keys stay out of the repo and are never baked into images
   or env vars
4. Harbor passes the task instruction to the adapter's `run()` method
5. `lenos run --quiet -m <model> <instruction>` executes inside the container
6. Harbor runs the task's test script and records the result

## Adding the adapter to your project

```bash
# Copy just the adapter directory
cp -r agon_bench/adapters /path/to/your/project/

# Then run from your project directory
harbor run -d "terminal-bench-2.0==head" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-pro \
  --task-id hello-world \
  -v ./agon_bench/lenos/config.json:/root/.config/lenos/config.json \
  -v ~/.local/share/lenos:/root/.local/share/lenos
```

## Harbor integration for CI

```bash
# Run against multiple tasks
harbor run -d "terminal-bench-2.0==head" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-pro \
  --task-ids task1,task2,task3 \
  -v ./agon_bench/lenos/config.json:/root/.config/lenos/config.json \
  -v ~/.local/share/lenos:/root/.local/share/lenos

# Run the full dataset
harbor run -d "terminal-bench-2.0==head" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-pro \
  -v ./agon_bench/lenos/config.json:/root/.config/lenos/config.json \
  -v ~/.local/share/lenos:/root/.local/share/lenos
```

## Code conventions

- **Python**: ruff for format and lint (`make fmt`, `make lint`)
- **Git**: conventional commits — `feat(agon):`, `fix(agon):`, `chore(agon):`
