#!/usr/bin/env bash
# Clean up Docker images and results.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Agon: Clean ==="
docker rmi agon-bench 2>/dev/null && echo "Removed agon-bench image" || echo "(image not found)"
rm -rf agon_bench/results/*
rm -rf agon_bench/transcripts/*
touch agon_bench/results/.gitkeep agon_bench/transcripts/.gitkeep
echo "Results and transcripts cleared."
