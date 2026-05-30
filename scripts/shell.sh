#!/usr/bin/env bash
# Open an interactive shell in the benchmark container.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Agon: Interactive Shell ==="
echo "The smoke task is mounted at /tasks/smoke"
echo "Binaries available: lenos, temenos, python3"
echo ""
docker run --rm -it \
  -v "$(pwd)/agon_bench/tasks/smoke:/tasks/smoke" \
  --entrypoint /bin/bash \
  agon-bench
