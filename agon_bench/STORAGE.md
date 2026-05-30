# Result and Transcript Storage
## Directory Layout
```
agon_bench/
├── results/
│   ├── .gitkeep           # tracked, ensures dir exists in fresh clones
│   └── results.jsonl      # append-only JSONL, one record per run
└── transcripts/
    ├── .gitkeep           # tracked, ensures dir exists in fresh clones
    └── <run-id>.log       # per-run agent transcript (stdout + stderr)
```
## JSONL Result Format
Each line in `results.jsonl` is a JSON object:
```json
{
  "run_id": "20260530T123456",
  "timestamp": "2026-05-30T12:34:56.789Z",
  "task": {
    "description": "...",
    "difficulty": "easy",
    "tags": ["smoke-test"]
  },
  "agent": {
    "name": "lenos",
    "model": "claude-sonnet-4",
    "version": "v1.3.0",
    "exit_code": 0,
    "duration_sec": 12.345,
    "timed_out": false
  },
  "provider": {
    "name": "anthropic"
  }
}
```
## Run ID Format
`YYYYMMDDTHHMMSS` — UTC timestamp at run start. Used as the transcript filename.
## Git Policy
- `results/*` and `transcripts/*` are git-ignored
- `.gitkeep` files are tracked to preserve directory structure
- Never commit actual benchmark results or transcripts to the repository
## Rotation
Results accumulate in `results.jsonl` across runs. To start fresh:
```bash
make clean    # removes all results and transcripts
```
