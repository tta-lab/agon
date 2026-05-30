# Agon
Terminal-Bench arena for measuring Lenos on real terminal tasks.
Agon runs [Lenos](https://github.com/tta-lab/lenos) agents against
[Terminal-Bench](https://github.com/harbor-framework/terminal-bench) tasks,
capturing structured results for benchmarking and regression detection.
## Structure
```
agon_bench/
├── config/          # Benchmark configuration (model, timeouts, paths)
├── runner/          # Runner adapter — invokes Lenos, writes JSONL results
├── tasks/           # Terminal-Bench task corpus
│   └── smoke/       # Minimal smoke task for harness validation
├── results/         # JSONL result output (git-ignored)
├── transcripts/     # Per-run transcripts (git-ignored)
└── STORAGE.md       # Result/transcript format docs
Taskfile.yaml        # Build, run, and test commands
```
## Requirements
### Host Tools
- **Docker** — containerized execution
- **Go 1.26+** — building lenos from source inside the Docker image
- **Python 3.12+** — runner and test infrastructure (`python3`, `pip3`)
- `make` (or `bash`) — primary local interface; `task` is optional
- `ruff` (optional) — Python formatting and linting
- `shfmt` (optional) — shell script formatting
### Secrets and Environment Variables
Provider credentials are **never** stored in this repo or baked into Docker images.
Set them at runtime:
```bash
export LENOS_PROVIDER=anthropic
export LENOS_PROVIDER_KEY=sk-ant-...
export LENOS_MODEL=claude-sonnet-4
```
Lenos reads provider config from environment variables automatically.
## Binary Acquisition
The Docker image is based on the [Terminal-Bench base image](https://github.com/laude-institute/terminal-bench/packages) (`ghcr.io/laude-institute/t-bench/ubuntu-24-04`) which provides `tmux` and `asciinema`. On top of that, it bundles:
- **lenos** — built from source via `git clone` + `go build` (avoids replace directive issues with `go install`)
- **temenos** — downloaded from pinned [GitHub releases](https://github.com/tta-lab/temenos/releases)
Build args control versions:
```bash
docker build -t agon-bench \
  --build-arg LENOS_REF=main \
  --build-arg TEMENOS_VERSION=v0.9.0 \
  --build-arg GO_VERSION=1.26.2 \
  -f agon_bench/runner/Dockerfile .
```
To override the lenos binary with a locally built one, mount it at runtime:
```bash
docker run --rm \
  -v $(pwd)/agon_bench/tasks/smoke:/tasks/smoke \
  -v $(pwd)/agon_bench/results:/results \
  -v $(pwd)/agon_bench/transcripts:/transcripts \
  -v $(which lenos):/usr/local/bin/lenos \
  agon-bench --task smoke
```
## CI and Image Publishing
The CI workflow (`.github/workflows/build-image.yml`) runs two verification layers:
### Layer 1: No-key (always runs)
- **Image build** — PRs build-check (no push), main/tags push to GHCR
- **Binary smoke check** — verifies `lenos --version`, `temenos --version`, Python version, and runner scripts are present in the built image
- **Smoke task verifier** — runs `solution.sh` then `pytest` against the smoke task test suite; confirms the task package is intact and tests pass against the reference solution
No provider credentials required for Layer 1.
### Layer 2: Secret-gated (requires provider keys)
- **Agent benchmark** — `lenos run` solves Terminal-Bench tasks with a real model
- Only executes when `LENOS_PROVIDER_KEY` is set in the environment
- Not part of the standard CI pipeline; run manually or via separate workflow
### GHCR Image Tags
Pre-built images are published to **GHCR** on every push to main and on tags:
```
ghcr.io/tta-lab/agon-runner:latest      # main branch
ghcr.io/tta-lab/agon-runner:sha-<sha>   # immutable per-commit
ghcr.io/tta-lab/agon-runner:v1.0.0      # semver tag
```
Pull the pre-built image instead of building locally:
```bash
docker pull ghcr.io/tta-lab/agon-runner:latest
```
## Quickstart
Use **`make`** or **`./scripts/*.sh`** as the primary local interface. `task` is available but optional.
```bash
# 1. Build the benchmark image
make build-image
# 2. Run the smoke task (requires provider env vars)
export LENOS_PROVIDER=anthropic
export LENOS_PROVIDER_KEY=sk-ant-...
export LENOS_MODEL=claude-sonnet-4
make run-smoke
# 3. Verify reference solution (no keys needed)
make test-solution
# 4. View results
make results
# 5. Interactive shell in the container
make shell
# 6. Format and lint
make fmt
make lint
# 7. Clean up
make clean
```
All commands delegate to scripts in `scripts/`. Run `make help` to see all targets.
## Adding New Terminal-Bench Tasks
1. Create a directory under `agon_bench/tasks/<task-name>/`
2. Add the required files:
   ```
   tasks/<task-name>/
   ├── task.yaml              # Task description and config
   ├── Dockerfile             # Environment (extend agon-bench or custom)
   ├── docker-compose.yaml    # Container orchestration
   ├── run-tests.sh           # Test entrypoint
   ├── setup-uv-pytest.sh     # Install test deps
   ├── run-uv-pytest.sh       # Execute tests
   ├── solution.sh            # Reference solution
   └── tests/
       └── test_outputs.py    # Verification tests
   ```
3. See [Terminal-Bench task docs](https://www.tbench.ai/docs/task-overview) for the full format spec
4. Tasks inherit the agon-bench base image by default (lenos + temenos + Python)
5. Custom tasks needing different environments should follow the [Terminal-Bench Docker guidelines](https://www.tbench.ai/docs/task-overview#docker-environment)
## Next Expansion Path
- **More tasks**: Add tasks from Terminal-Bench categories — file manipulation, git operations, system administration, data processing
- **Batch runner**: Run multiple tasks in sequence and aggregate JSONL results
- **Model comparison**: Run the same task set across different models and compare pass rates
- **CI integration**: Run benchmark as a GitHub Actions workflow on Lenos releases for regression detection
- **Leaderboard**: Publish benchmark results to track Lenos improvements over time
