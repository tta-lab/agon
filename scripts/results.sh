#!/usr/bin/env bash
# Show benchmark results summary.
set -euo pipefail
cd "$(dirname "$0")/.."
RESULTS_FILE="agon_bench/results/results.jsonl"
if [ ! -f "$RESULTS_FILE" ]; then
  echo "No results yet. Run 'make run-smoke' to execute a benchmark."
  exit 0
fi
TOTAL=$(wc -l < "$RESULTS_FILE")
PASSED=$(python3 -c "
import json, sys
count = 0
for line in open('$RESULTS_FILE'):
    r = json.loads(line)
    if r['agent']['exit_code'] == 0 and not r['agent']['timed_out']:
        count += 1
print(count)
" 2>/dev/null || echo "?")
echo "=== Agon Results ==="
echo "Total runs: $TOTAL"
echo "Passed:     $PASSED"
echo "Failed:     $((TOTAL - PASSED))"
echo ""
python3 << PYEOF
import json
header = f"{'RUN ID':<18} {'STATUS':<8} {'DURATION':>10} {'MODEL':<20}"
print(header)
print('-' * len(header))
for line in open('$RESULTS_FILE'):
    r = json.loads(line)
    status = 'PASS' if r['agent']['exit_code'] == 0 and not r['agent']['timed_out'] else 'FAIL'
    dur = f"{r['agent']['duration_sec']:.1f}s"
    model = r['agent'].get('model', '') or '-'
    print(f"{r['run_id']:<18} {status:<8} {dur:>10} {model:<20}")
PYEOF
