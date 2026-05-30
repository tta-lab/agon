#!/usr/bin/env bash
# Agon runner entrypoint — invoked inside the Docker container.
# Starts temenos daemon, runs lenos against a task, captures results.
#
# Usage: agon-run --task <name>
#
# Environment variables:
#   LENOS_MODEL         — model to use (e.g. claude-sonnet-4)
#   LENOS_PROVIDER      — provider name (e.g. anthropic)
#   LENOS_PROVIDER_KEY  — API key for the provider
#   AGENT_TIMEOUT_SEC   — max agent execution time (default: 300)
#   TEST_TIMEOUT_SEC    — max test execution time (default: 60)
#   LENOS_VERSION       — lenos version string (for metadata)
set -euo pipefail
TASK_NAME=""
MODEL="${LENOS_MODEL:-}"
RESULTS_DIR="${RESULTS_DIR:-/results}"
TRANSCRIPTS_DIR="${TRANSCRIPTS_DIR:-/transcripts}"
TASK_DIR="${TASK_DIR:-/tasks}"
# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --task)
            TASK_NAME="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done
if [[ -z "$TASK_NAME" ]]; then
    echo "Usage: agon-run --task <name> [--model <model>]"
    exit 1
fi
TASK_PATH="${TASK_DIR}/${TASK_NAME}"
if [[ ! -d "$TASK_PATH" ]]; then
    echo "ERROR: task directory not found: ${TASK_PATH}"
    exit 1
fi
echo "=== Agon Runner ==="
echo "Task:      ${TASK_NAME}"
echo "Task dir:  ${TASK_PATH}"
echo "Model:     ${MODEL:-default}"
echo "Timeout:   ${AGENT_TIMEOUT_SEC:-300}s"
echo ""
# Verify binaries are available
echo "--- Binary versions ---"
lenos --version 2>&1 || { echo "ERROR: lenos not found"; exit 1; }
temenos --version 2>&1 || { echo "ERROR: temenos not found"; exit 1; }
echo ""
# Start temenos daemon in the background
echo "--- Starting temenos daemon ---"
temenos daemon &
TEMENOS_PID=$!
# Give it a moment to start
sleep 1
echo "Temenos daemon running (PID: ${TEMENOS_PID})"
echo ""
# Run the Python adapter
echo "--- Running task ---"
python3 /usr/local/bin/agon-runner.py \
    --task-dir "${TASK_PATH}" \
    --results-dir "${RESULTS_DIR}" \
    --transcripts-dir "${TRANSCRIPTS_DIR}" \
    ${MODEL:+--model "${MODEL}"}
RUNNER_EXIT=$?
echo ""
echo "--- Runner finished (exit: ${RUNNER_EXIT}) ---"
# Stop temenos daemon
kill "${TEMENOS_PID}" 2>/dev/null || true
wait "${TEMENOS_PID}" 2>/dev/null || true
exit "${RUNNER_EXIT}"
