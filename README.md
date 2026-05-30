# Agon
Terminal-Bench arena for measuring Lenos on real terminal tasks.
Agon runs Lenos agents against [Terminal-Bench](https://github.com/harbor-framework/terminal-bench) tasks, capturing structured results for benchmarking and regression detection.
## Structure
```
agon_bench/
├── config/          # Benchmark configuration (model, timeouts, paths)
├── runner/          # Runner adapter — invokes Lenos, writes JSONL results
├── tasks/           # Terminal-Bench task corpus
│   └── smoke/       # Minimal smoke task for harness validation
├── results/         # JSONL result output (git-ignored)
└── transcripts/     # Per-run transcripts (git-ignored)
Taskfile.yaml        # Build, run, and test commands
```
## Requirements
- [Task](https://taskfile.dev) — task runner
- Docker — containerized execution
- Python 3.12+ — runner and test infrastructure
- `lenos` binary — the agent under test
- `temenos` binary — sandbox daemon
## Quickstart
```bash
# Install Python deps
pip install -r agon_bench/runner/requirements.txt
# Build the benchmark image
task build-image
# Run the smoke task
task run-smoke
# Run tests
task test
# View results
task results
```
## Adding Tasks
Terminal-Bench tasks live under `agon_bench/tasks/<task-name>/`. Each task needs:
- `task.yaml` — task description and config
- `Dockerfile` — environment definition
- `docker-compose.yaml` — container orchestration
- `run-tests.sh` — test entrypoint
- `solution.sh` or `solution.yaml` — reference solution
- `tests/test_outputs.py` — verification tests
See the Terminal-Bench [task format docs](https://www.tbench.ai/docs/task-overview) for details.
