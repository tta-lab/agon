#!/usr/bin/env bash
# Show benchmark results summary.
set -euo pipefail
cd "$(dirname "$0")/.."
RESULTS_FILE="agon_bench/results/results.jsonl"
if [ ! -f "$RESULTS_FILE" ]; then
  echo "No results yet. Run 'make run-smoke' to execute a benchmark."
  exit 0
fi
python3 << PYEOF
import json
records = []
with open('$RESULTS_FILE') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
total = len(records)
passed = sum(
    1 for r in records
    if r['agent']['exit_code'] == 0 and not r['agent']['timed_out']
)
failed = total - passed
print("=== Agon Results ===")
print(f"Total runs: {total}")
print(f"Passed:     {passed}")
print(f"Failed:     {failed}")
print()
header = f"{'RUN ID':<18} {'STATUS':<8} {'DURATION':>10} {'MODEL':<20}"
print(header)
print('-' * len(header))
for r in records:
    status = 'PASS' if r['agent']['exit_code'] == 0 and not r['agent']['timed_out'] else 'FAIL'
    dur = f"{r['agent']['duration_sec']:.1f}s"
    model = r['agent'].get('model', '') or '-'
    print(f"{r['run_id']:<18} {status:<8} {dur:>10} {model:<20}")
PYEOF
