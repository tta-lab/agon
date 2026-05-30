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
- [Task](https://taskfile.dev) — task runner (`task` CLI)
- Docker — containerized execution
- Python 3.12+ — runner and test infrastructure (`python3`, `pip3`)
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
The Docker image can acquire `lenos` and `temenos` in two ways:
### 1. Pinned Release Download (default)
Build args control versions:
```bash
docker build -t agon-bench \
  --build-arg LENOS_VERSION=v1.3.0 \
  --build-arg TEMENOS_VERSION=v0.9.0 \
  -f agon_bench/runner/Dockerfile .
```
### 2. Local Binary Mount
Override the baked-in lenos binary with a locally built one:
```bash
docker run --rm \
  -v $(pwd)/agon_bench/tasks/smoke:/tasks/smoke \
  -v $(pwd)/agon_bench/results:/results \
  -v $(pwd)/agon_bench/transcripts:/transcripts \
  -v $(which lenos):/usr/local/bin/lenos \
  agon-bench --task smoke
```
## CI and Image Publishing
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
The CI workflow (`.github/workflows/build-image.yml`) builds on PRs (dry-run, no push) and publishes on main/tags with smoke verification of the published image.
## Quickstart
```bash
# 1. Install Python deps (inside Docker this is automatic)
pip3 install --break-system-packages pyyaml
# 2. Build the benchmark image
task build-image
# 3. Run the smoke task (requires provider env vars)
task run-smoke
# 4. Run smoke task tests independently
task test
# 5. Verify solution + tests (no agent needed)
task test-solution
# 6. View results
task results
# 7. Interactive shell in container
task shell
```
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
