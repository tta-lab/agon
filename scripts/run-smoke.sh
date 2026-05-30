#!/usr/bin/env bash
# Run the smoke task through the benchmark adapter.
# Requires provider env vars: LENOS_PROVIDER_KEY, LENOS_PROVIDER, LENOS_MODEL
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Agon: Run Smoke Benchmark ==="
docker run --rm \
  -e LENOS_PROVIDER_KEY \
  -e LENOS_PROVIDER \
  -e LENOS_MODEL \
  -v "$(pwd)/agon_bench/tasks/smoke:/tasks/smoke" \
  -v "$(pwd)/agon_bench/results:/results" \
  -v "$(pwd)/agon_bench/transcripts:/transcripts" \
  agon-bench --task smoke
