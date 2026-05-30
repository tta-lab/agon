# Agon — Agent Guide
Agon is a Terminal-Bench arena for measuring Lenos against real terminal tasks.
It runs containerized benchmarks: Docker image with lenos + temenos + Python
runner, mounted host Lenos config (read-only), JSONL results output.
## Essential Commands
| Command             | What it does                                           |
|---------------------|--------------------------------------------------------|
| `make build-image`  | Build the agon-bench Docker image                      |
| `make run-smoke`    | Run smoke task through Lenos (needs host Lenos config) |
| `make test-solution`| Verify reference solution + tests (no keys needed)     |
| `make results`      | Show pass/fail summary table from results.jsonl        |
| `make shell`        | Interactive bash shell in the container                |
| `make fmt`          | Format Python (ruff) and shell (shfmt)                 |
| `make lint`         | Lint Python with ruff                                  |
| `make clean`        | Remove Docker image and clear results/transcripts      |
| `make help`         | List all available targets                             |
All Makefile targets delegate to `scripts/*.sh`. Run scripts directly as an
alternative to make. The `make` targets are the canonical interface; scripts
should stay compatible but `make` is what CI/docs reference.
## Docker Image Structure
Base: `ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624` (provides tmux,
asciinema). Added on top: Go 1.26+, Python 3.12+, pip deps (pyyaml), lenos
built from source (`git clone` + `go build` — `go install` fails due to
replace directives in lenos go.mod), temenos downloaded from pinned GitHub
release.
Build args for version pinning:
- `LENOS_REF` (git ref, default `main`)
- `TEMENOS_VERSION` (release tag, default `v0.9.0`)
- `GO_VERSION` (default `1.26.2`)
Entrypoint: `/usr/local/bin/agon-run` — starts temenos daemon, then runs
runner.py, then kills daemon.
## Credentials and Secrets
Providers secrets are **never** in the repo, image, or environment variables.
The host Lenos config dir (`~/.local/share/lenos`) is mounted read-only into
the container at `/root/.local/share/lenos`. Lenos reads its `config.json`
from there. The mount is `:ro` — the container can read but not write back.
`LENOS_DISABLE_PROVIDER_AUTO_UPDATE=1` is set in the entrypoint to prevent
lenos from trying to write `providers.json` to the read-only mount.
For CI: Layer 1 jobs (smoke-check, verify-task) run without secrets. Layer 2
(agent benchmark) requires the host config mount and is run locally, not in CI.
## Results and Transcripts
- `agon_bench/results/results.jsonl` — append-only, one JSON object per line
- `agon_bench/transcripts/<run-id>.log` — per-run agent stdout+stderr
- Run ID format: `YYYYMMDDTHHMMSS` UTC
- Both dirs are git-ignored except for `.gitkeep`
- Results accumulate across runs; `make clean` clears them
## Architecture
```
Makefile/scripts  ← developer entry point
       │
       ▼
agon-bench Docker image
  ├── agon-run (entrypoint): starts temenos, calls runner.py, stops temenos
  ├── agon-runner.py: loads task.yaml → extracts instruction → runs lenos
  │   → writes JSONL + transcript
  ├── lenos: CLI agent, reads config from mounted host dir
  └── temenos: sandbox daemon for lenos agent execution
```
The runner (`agon_bench/runner/runner.py`) is a standalone Python script:
- `load_task(task_dir)` — reads task.yaml
- `get_instruction(task)` — supports `description` field or `descriptions` list (returns "base" key)
- `run_lenos(instruction, model, timeout)` — subprocess `lenos run --quiet`
- `build_result_record(task, agent_result, run_id, model)` — assembles JSONL record
- `write_jsonl`, `write_transcript` — persist outputs
The runner exits with the agent's exit code (0 = pass, non-zero = fail).
## Task Structure
Tasks live in `agon_bench/tasks/<task-name>/` and follow Terminal-Bench format:
```
tasks/<name>/
├── task.yaml              # description, difficulty, tags, timeouts, test_scripts
├── Dockerfile             # optional, extends agon-bench by default
├── docker-compose.yaml    # container orchestration (${T_BENCH_*} vars)
├── run-tests.sh           # test entrypoint
├── setup-uv-pytest.sh     # install test deps (pip3 install pytest)
├── run-uv-pytest.sh       # execute pytest
├── solution.sh            # reference solution (the "correct" answer)
└── tests/
    └── test_outputs.py    # pytest verification
```
The smoke task is a minimal example: creates `hello.txt` with "Hello from
Lenos!\n" and verifies via pytest that the file exists with exact content.
## CI Workflow
`.github/workflows/build-image.yml` — three jobs on PRs and pushes:
1. **build-image**: Builds Docker image. On PRs: dry-run (build only, no push).
   On main/tags: pushes to `ghcr.io/tta-lab/agon-runner` with tags for
   branch, SHA, semver, and `latest` on main.
2. **smoke-check**: Loads built image, verifies `lenos --version`, `temenos
   --version`, `python3 --version`, and that runner scripts exist.
3. **verify-task**: Copies smoke task into image, runs `solution.sh` then
   `pytest` — confirms the task package is intact without provider keys.
CI uses `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"` to suppress Actions
runtime deprecation warnings.
Pre-built images: `ghcr.io/tta-lab/agon-runner:latest` (pull instead of
building locally).
## Code Conventions
**Python**: No formatter config committed. Uses ruff for both format and lint.
No type annotations on internal functions (runner.py uses basic type hints on
signatures but not throughout). Single-file runner with no package structure
beyond `__init__.py` markers.
**Shell**: All scripts use `set -euo pipefail`. Scripts `cd "$(dirname
"$0")/.."` to run from repo root. Use `[[ ]]` for conditionals, lowercase
variable names for locals, UPPERCASE for env-exposed vars. No shellcheck
config committed — shfmt for formatting, no lint step for shell.
**Docker**: Dockerfile uses multi-stage build args pattern. No `.dockerignore`
committed (context is small). Images tagged as `agon-bench` locally,
`ghcr.io/tta-lab/agon-runner` in registry.
**Git**: Conventional commits (`feat(scope):`, `fix(scope):`, `chore(scope):`,
`refactor(scope):`, `docs(scope):`). Scope is typically the component:
`agon`, `docker`, `ci`, `config`.
## Temenos Sandbox
Temenos config at `/root/.config/temenos/config.toml` inside the container
(`agon_bench/runner/temenos-config.toml` in repo). Sets:
- `allow_env`: `TTAL_*`, `LENOS_*`, `HOME`, `USER`, `SHELL`, `PATH`, `DEBUG`, `CI`, `NO_COLOR`, `FORCE_COLOR`
- `allow_read`: `/usr/local/bin`, `/usr/bin`, `/bin`, `/workspace`
- `allow_write`: `/workspace`, `/tmp`
Note: The lenos config dir (`~/.local/share/lenos`) is intentionally NOT in
`allow_read` — this is a **security boundary**. Adding it would give the
sandboxed agent direct access to API keys stored in the host's Lenos config.
Lenos reads its config before spawning the sandbox; the agent inside the
sandbox should never see credentials. The dir is pre-created in the Dockerfile
to suppress temenos warnings when the host mount isn't present (e.g. CI
smoke-check).
## Gotchas
1. **`go install` doesn't work for lenos**. Lenos has `replace` directives in
   its go.mod. The Dockerfile must `git clone` + `CGO_ENABLED=0 go build`.
2. **Temenos daemon must be running**. The entrypoint starts it before the
   runner and kills it after. If running lenos manually inside the container,
   start `temenos daemon &` first.
3. **bubblewrap required**. Without `bwrap` installed, temenos returns HTTP
   500 on every agent command. The Dockerfile installs it explicitly.
4. **Read-only config mount + lenos auto-update**. Lenos tries to write
   `providers.json` on startup. Without `LENOS_DISABLE_PROVIDER_AUTO_UPDATE=1`,
   it crashes on the read-only mount.
5. **task.yaml `descriptions` field**. The runner supports both a flat
   `description` string and a `descriptions` list (Terminal-Bench
   multi-description format). When `descriptions` is present, it picks the one
   with `key: "base"` or falls back to the first entry.
6. **JSONL results file is append-only**. Multiple runs in the same container
   session accumulate. The `results.sh` script handles blank lines gracefully.
7. **CI tags never contain local-only image names**. Build-image pushes only
   the metadata-generated tags. Smoke-check and verify-task jobs build
   independently with `load:true`/`push:false` and local-only tags.
8. **No .dockerignore**. The Docker context is small (just the repo). If the
   repo grows, add one to speed up builds.
9. **Never add `~/.local/share/lenos` to `allow_read` in temenos config.**
   This would expose the host's API keys to sandboxed agent processes. The
   config dir is mounted read-only for lenos itself (which reads it before
   sandbox spawn), but the sandbox must never have access. If you see
   `allow_read` containing the config path, that's a security bug.
