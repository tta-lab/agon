#!/usr/bin/env bash
# Agon runner entrypoint — invoked inside the Docker container.
# This script: starts temenos daemon, runs lenos against a task, captures results.
#
# Usage: agon-run [--task <name>] [--model <model>]
#
# Environment variables:
#   LENOS_MODEL         — model to use (e.g. claude-sonnet-4)
#   LENOS_PROVIDER_KEY  — API key for the provider
#   AGENT_TIMEOUT_SEC   — max agent execution time (default: 300)
#   TEST_TIMEOUT_SEC    — max test execution time (default: 60)
set -euo pipefail
echo "Agon runner starting..."
echo "Lenos: $(lenos --version 2>&1 || echo 'NOT FOUND')"
echo "Temenos: $(temenos --version 2>&1 || echo 'NOT FOUND')"
# Placeholder — full implementation in subtask 3
echo "Runner entrypoint loaded. Full implementation pending."
