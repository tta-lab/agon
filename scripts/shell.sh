#!/usr/bin/env bash
# Open an interactive shell in the benchmark container.
# Mounts the host Lenos config read-only so lenos works inside the container.
set -euo pipefail
cd "$(dirname "$0")/.."
LENOS_DATA="${LENOS_DATA:-$HOME/.local/share/lenos}"
echo "=== Agon: Interactive Shell ==="
echo "The smoke task is mounted at /tasks/smoke"
echo "Lenos config mounted from $LENOS_DATA"
echo "Binaries available: lenos, temenos, python3"
echo ""
docker run --rm -it \
  -v "$LENOS_DATA:/root/.local/share/lenos:ro" \
  -v "$(pwd)/agon_bench/tasks/smoke:/tasks/smoke" \
  --entrypoint /bin/bash \
  agon-bench
