#!/usr/bin/env bash
set -euo pipefail
cd /app
python3 -m pytest "$TEST_DIR/test_outputs.py" -v
