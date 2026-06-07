# Timeout Can Hide Final Usage Metrics

## Run

- Task: `terminal-bench/break-filter-js-from-html`
- Model: `deepseek-v4-flash`
- Job: `2026-06-04__18-54-35`
- Trial: `break-filter-js-from-html__hZYoq8o`
- Official reward: `1.0`
- Exception: `AgentTimeoutError`
- Local status: `pass_after_agent_timeout`

## What Happened

The artifact passed the verifier, but Harbor recorded an agent timeout. Because
the run was cancelled at timeout, the adapter did not reliably parse final
`--usage-json` output into Harbor metadata.

The scoreboard therefore has no cost/cache/token metrics for this run even
though the task passed.

## Why It Matters

For full-suite runs, timeout-passed trials are still important for task coverage,
but missing usage makes it harder to compare models and reason about cache hit
rate or cost.

## Lenos/Adapter Improvement Lead

Possible approaches:

- make Lenos flush usage summary incrementally or earlier
- have the adapter try to parse `/logs/agent/usage-summary.json` in a post-run
  path even after timeout cancellation, if Harbor allows it
- keep the official exception/reward unchanged while filling best-effort usage
  metadata

## Follow-Up Check

Re-run one known timeout-pass task after any usage-finalization change and check
whether `input_tokens`, `cache_tokens`, `output_tokens`, and `cost_usd` appear
in `tb2-scoreboard.json`.
