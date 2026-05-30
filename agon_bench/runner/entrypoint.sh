#!/usr/bin/env bash
# Agon runner entrypoint — invoked inside the Docker container.
# Starts temenos daemon, runs lenos against a task, captures results.
#
# Usage: agon-run --task <name>
#
# Lenos reads its provider config from the mounted data dir.
# No secrets in env vars or image.
set -euo pipefail
TASK_NAME=""
MODEL=""
RESULTS_DIR="${RESULTS_DIR:-/results}"
TRANSCRIPTS_DIR="${TRANSCRIPTS_DIR:-/transcripts}"
TASK_DIR="${TASK_DIR:-/tasks}"
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
# Prevent lenos from trying to write to the read-only mounted config dir
export LENOS_DISABLE_PROVIDER_AUTO_UPDATE=1
echo "=== Agon Runner ==="
echo "Task:      ${TASK_NAME}"
echo "Task dir:  ${TASK_PATH}"
echo "Timeout:   ${AGENT_TIMEOUT_SEC:-300}s"
echo ""
echo "--- Binary versions ---"
lenos --version 2>&1 || { echo "ERROR: lenos not found"; exit 1; }
temenos --version 2>&1 || { echo "ERROR: temenos not found"; exit 1; }
echo ""
echo "--- Starting temenos daemon ---"
temenos daemon &
TEMENOS_PID=$!
sleep 1
echo "Temenos daemon running (PID: ${TEMENOS_PID})"
echo ""
echo "--- Running task ---"
python3 /usr/local/bin/agon-runner.py \
    --task-dir "${TASK_PATH}" \
    --results-dir "${RESULTS_DIR}" \
    --transcripts-dir "${TRANSCRIPTS_DIR}" \
    ${MODEL:+--model "${MODEL}"}
RUNNER_EXIT=$?
echo ""
echo "--- Runner finished (exit: ${RUNNER_EXIT}) ---"
kill "${TEMENOS_PID}" 2>/dev/null || true
wait "${TEMENOS_PID}" 2>/dev/null || true
exit "${RUNNER_EXIT}"
