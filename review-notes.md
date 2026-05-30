# Review notes: `feature/terminal-bench-harness`
## Fixed (since initial review)
- `scripts/results.sh` — rewritten as single `python3 << PYEOF` heredoc. Blank-line tolerant. Single pass. No bash arithmetic. Clean.
## Remaining findings
### 1. `agon_bench/STORAGE.md:45` — stale reference to `task`
```
task clean    # removes all results and transcripts
```
`task` (Taskfile) was removed. Should read `make clean`.
### 2. `agon_bench/tasks/smoke/run-tests.sh` and `run-uv-pytest.sh` — identical files, naming confusion
Both files are byte-for-byte identical. CI's verify-task job copies `run-tests.sh` but `task.yaml` references `run-uv-pytest.sh`:
```yaml
test_scripts:
  - setup-uv-pytest.sh
  - run-uv-pytest.sh
```
Works because identical content, but confusing. Pick one name and use it consistently across `task.yaml`, CI workflow, and the filesystem.
### 3. `agon_bench/config/bench.yaml` — dead config
Defines `model`, `agent_timeout_sec`, `results_dir`, etc. Nothing reads it — runner.py takes config from CLI args and env vars. Either wire it up or remove it.
### 4. `scripts/fmt.sh:17` — `globstar` not set
```bash
shfmt -w agon_bench/**/*.sh scripts/*.sh
```
`agon_bench/**/*.sh` requires `shopt -s globstar` which is not enabled. Without it, `**` is literal and won't match nested shell files like `agon_bench/tasks/smoke/run-tests.sh`.
### 5. `agon_bench/runner/temenos-config.toml` — `AGENT_TIMEOUT_SEC` missing from `allow_env`
Entrypoint and runner use `AGENT_TIMEOUT_SEC`. It's not in `allow_env`, so temenos won't pass it to the sandbox. Runner falls back to hardcoded default of 300 in Python, so it doesn't break — but custom timeouts are silently ignored.
