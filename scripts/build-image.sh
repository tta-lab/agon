#!/usr/bin/env bash
# Build the Agon benchmark Docker image.
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -t agon-bench -f agon_bench/runner/Dockerfile .
echo "Image built: agon-bench"
