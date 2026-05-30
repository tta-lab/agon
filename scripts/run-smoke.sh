#!/usr/bin/env bash
# Run the smoke task through the benchmark adapter.
# Mounts the host Lenos config read-only — provider credentials stay on the host.
set -euo pipefail
cd "$(dirname "$0")/.."
LENOS_DATA="${LENOS_DATA:-$HOME/.local/share/lenos}"
if [ ! -f "$LENOS_DATA/config.json" ]; then
  echo "ERROR: Lenos config not found at $LENOS_DATA/config.json"
  echo "Run 'lenos' interactively to set up a provider first."
  exit 1
fi
echo "=== Agon: Run Smoke Benchmark ==="
docker run --rm \
  -v "$LENOS_DATA:/root/.local/share/lenos:ro" \
  -v "$(pwd)/agon_bench/tasks/smoke:/tasks/smoke" \
  -v "$(pwd)/agon_bench/results:/results" \
  -v "$(pwd)/agon_bench/transcripts:/transcripts" \
  agon-bench --task smoke
