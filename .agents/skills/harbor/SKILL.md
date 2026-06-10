---
name: harbor
description: Use when running, documenting, or debugging Harbor jobs, Harbor CLI flags, Terminal-Bench datasets, custom installed agents, Docker task containers, mounts, or Agon/Lenos Harbor adapter workflows.
---

# Harbor

Use the local Harbor CLI first:

```bash
HARBOR=${HARBOR:-"uv run harbor"}
$HARBOR run --help
```

Harbor flags move. Check `harbor run --help` before changing docs or scripts.

## Common Run Shape

Single registry task:

```bash
$HARBOR run -d "terminal-bench/terminal-bench-2-1" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  -t terminal-bench/hello-world \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y
```

Dataset subset:

```bash
$HARBOR run -d "terminal-bench/terminal-bench-2-1" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  --include-task-name "python-*" \
  --n-tasks 3 \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y
```

Use `--config/-c` for complex jobs or multiple plugins.

## Local Custom Task Smoke

Use a local task when validating adapter/bootstrap behavior. This avoids
spending time on registry lookup and lets the instruction force the exact tool
path under test.

Minimum task layout:

```text
/tmp/agon-smoke-task/
  instruction.md
  task.toml
  environment/Dockerfile
  tests/test.sh
  solution/solve.sh
```

Minimal `task.toml`:

```toml
schema_version = "1.1"

[task]
name = "local/smoke"
description = "Local Harbor smoke task."

[verifier]
timeout_sec = 120

[agent]
timeout_sec = 300

[environment]
build_timeout_sec = 300
docker_image = "ubuntu:24.04"
allow_internet = true
```

Minimal `environment/Dockerfile`:

```dockerfile
FROM ubuntu:24.04
WORKDIR /app
```

Minimal verifier:

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ -s /app/smoke-output.txt ]]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
  exit 1
fi
```

Run it with `--path`:

```bash
LIBSTDCXX_OUT=$(nix eval --raw nixpkgs#stdenv.cc.cc.lib.outPath 2>/dev/null || true)
LD_LIBRARY_PATH="$LIBSTDCXX_OUT/lib:${LD_LIBRARY_PATH:-}" \
  $HARBOR run --path /tmp/agon-smoke-task \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -n 1 -y
```

For tool-integration smoke, require the agent to persist evidence as an
artifact. Example: ask it to run `ei ask ... > /app/ei-answer.txt`, pass
`--artifact /app/ei-answer.txt`, and verify the artifact is non-empty. A reward
alone proves only the verifier passed; the transcript and artifact prove the
intended tool path ran.

## Flags To Prefer

- Single registry task: `--task/-t org/name`
- Local task or dataset: `--path /path/to/task-or-dataset`
- Dataset filters: `--include-task-name`, `--exclude-task-name`, `--n-tasks`
- Mounts: `--mounts '<json array>'`
- Custom agent: `--agent-import-path module.path:ClassName`
- Model: `--model/-m`
- Non-interactive confirmation: `--yes/-y`

Avoid stale flags in docs and scripts:

- Do not use `--task-id` or `--task-ids`.
- Do not use Docker-style `-v`; use `--mounts`.

## Agon Lenos Notes

Agon mounts two Lenos paths into the task container:

- `/root/.config/lenos/config.json`: non-secret Agon options.
- `/root/.local/share/lenos`: host provider secrets and registry state for the Lenos process.

Never add `/root/.local/share/lenos` to the Temenos sandbox `allow_read`. Do not pass provider secret env vars such as `OPENAI_*`, `ANTHROPIC_*`, `DEEPSEEK_*`, or `GOOGLE_*` into the Temenos sandbox without explicit review.

The Agon adapter installs Lenos and Organon tools, writes the Harbor instruction
to `/tmp/agon-task.md`, passes
`--trajectory-json /logs/agent/trajectory.json` to `lenos run`, and parses ATIF
`final_metrics` into Harbor context metadata. Check `Makefile` and
`agon_bench/adapters/lenos.py` for the current default versions and reasoning
effort; these move during smoke work. Keep `python3` available as a general
task-solving utility, but do not reintroduce a Python `post_step` hook or
Python aggregation path for metrics.

When `ei` support is enabled, the adapter installs the `ei` binary, writes
`/root/.config/einai/config.toml`, starts `ei daemon run` in the background, and
allows `/root/.einai` in the Temenos sandbox so the main agent can connect to
`/root/.einai/daemon.sock`.

## Verification

Before claiming Harbor docs or scripts are correct:

```bash
$HARBOR run --help
make lint
git diff --check
rg -n -- "--task-id|--task-ids| -v |lenos run --quiet|usage-summary" README.md AGENTS.md agon_bench/adapters/lenos.py Makefile
```
