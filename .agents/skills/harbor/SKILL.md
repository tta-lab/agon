---
name: harbor
description: Use when running, documenting, or debugging Harbor jobs, Harbor CLI flags, Terminal-Bench datasets, custom installed agents, Docker task containers, mounts, or Agon/Lenos Harbor adapter workflows.
---

# Harbor

Use the local Harbor CLI first:

```bash
HARBOR=${HARBOR:-.venv/bin/harbor}
[ -x "$HARBOR" ] || HARBOR=harbor
"$HARBOR" run --help
```

Harbor flags move. Check `harbor run --help` before changing docs or scripts.

## Common Run Shape

Single registry task:

```bash
"$HARBOR" run -d "terminal-bench-2.0==head" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  -t terminal-bench/hello-world \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y
```

Dataset subset:

```bash
"$HARBOR" run -d "terminal-bench-2.0==head" \
  --agent-import-path agon_bench.adapters.lenos:LenosAgent \
  -m deepseek-v4-flash \
  --include-task-name "python-*" \
  --n-tasks 3 \
  --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]" \
  -y
```

Use `--config/-c` for complex jobs or multiple plugins.

## Flags To Prefer

- Single registry task: `--task/-t org/name`
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

The Agon adapter uses Python for the post-step usage hook and usage summary. If editing install logic, ensure task containers get `python3` as well as `bubblewrap` and `curl`.

## Verification

Before claiming Harbor docs or scripts are correct:

```bash
"$HARBOR" run --help
make lint
git diff --check
rg -n -- "--task-id|--task-ids| -v |lenos run --quiet" README.md AGENTS.md agon_bench/adapters/lenos.py Makefile
```
