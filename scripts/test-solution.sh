#!/usr/bin/env bash
# Verify the smoke task by running the reference solution + pytest verifier.
# No provider credentials needed.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Agon: Verify Smoke Task Solution ==="
docker run --rm \
  --entrypoint /bin/bash \
  -v "$(pwd)/agon_bench/tasks/smoke:/task" \
  agon-bench -c '
    set -euo pipefail
    cp /task/solution.sh /tmp/
    cp /task/setup-uv-pytest.sh /tmp/
    cp -r /task/tests /tmp/tests
    export TEST_DIR=/tmp/tests
    cd /tmp
    echo "--- Running solution.sh ---"
    bash solution.sh
    echo ""
    echo "--- Solution output ---"
    cat hello.txt
    echo ""
    echo "--- Installing test dependencies ---"
    bash setup-uv-pytest.sh
    echo "--- Running verifier ---"
    python3 -m pytest /tmp/tests/test_outputs.py -v
    echo ""
    echo "All smoke task tests passed."
  '
