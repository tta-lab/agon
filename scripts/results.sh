#!/usr/bin/env bash
# Show latest benchmark results.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Agon: Latest Results ==="
if [ -f agon_bench/results/results.jsonl ]; then
  echo "Results file: agon_bench/results/results.jsonl"
  echo ""
  wc -l agon_bench/results/results.jsonl
  echo "run(s) total"
  echo ""
  echo "Last run:"
  tail -1 agon_bench/results/results.jsonl | python3 -m json.tool 2>/dev/null || echo "(parse failed)"
else
  echo "No results yet. Run 'make run-smoke' to execute a benchmark."
fi
