# Handoff: Lenos Metrics Before Full TB2

## Current State

Agon now runs Lenos through Harbor and captures token metrics from Lenos
`hooks.post_step`.

Implemented in Agon:

- `agon_bench/lenos/config.json` configures:
  - `hooks.post_step = "python3 /usr/local/bin/agon-lenos-post-step"`
  - notifications/provider auto-update/metrics disabled for benchmark runs
- `agon_bench/adapters/lenos.py` installs the hook script in the task container.
- The hook writes per-step usage events to `/logs/agent/usage.jsonl`.
- The adapter aggregates those events into `/logs/agent/usage-summary.json`.
- Harbor `AgentContext` gets:
  - `n_input_tokens`
  - `n_cache_tokens`
  - `n_output_tokens`
  - metadata with cache hit/miss details

Validated smoke:

- `deepseek-v4-flash` on `terminal-bench/headless-terminal`
- Reward: `1.0`
- Latest metrics smoke job: `jobs/2026-06-04__12-31-01`
- Observed Harbor stats:
  - `n_input_tokens = 40928`
  - `n_cache_tokens = 39296`
  - `n_output_tokens = 3972`
  - `cost_usd = null`

## Metrics Covered

Already covered for DeepSeek official provider:

- Total token count
- Input token count, including cached input for Harbor's `n_input_tokens`
- Input cache hit tokens
- Input cache miss tokens
- Output token count
- Job/trial timing via Harbor timestamps and phase timings

DeepSeek official provider appears compatible with this token accounting path:

- Catwalk config defines DeepSeek as `type: "openai-compat"`.
- Actual smoke runs produced nonzero `cache_read_tokens`.
- Current cache hit rate can be computed as:

```text
input_cache_hit_tokens / (input_cache_hit_tokens + input_cache_miss_tokens)
```

For the latest smoke:

```text
39296 / (39296 + 1632) = 96.0%
```

## Missing

### Dollar Cost

Harbor `cost_usd` is still null.

Lenos already computes session cost internally, but the current post-step hook
envelope does not expose cost. Agon should not reimplement pricing from provider
config because that duplicates Lenos logic and risks drifting from the source of
truth.

Needed Lenos-side change:

- Add cost to a machine-readable usage export.

Recommended shape:

```json
{
  "version": 1,
  "event": "post_step",
  "input_tokens": 123,
  "output_tokens": 45,
  "cache_read_tokens": 100,
  "cache_creation_tokens": 0,
  "cache_miss_tokens": 123,
  "cost_usd": 0.00123
}
```

Better long-term shape:

- Keep `post_step` for per-step events.
- Add a final `run_summary` hook/event or `--usage-json <path>` flag emitted
  after `lenos run` completes.
- Include:
  - `cost_usd`
  - `input_tokens`
  - `input_cache_hit_tokens`
  - `input_cache_miss_tokens`
  - `cache_creation_tokens`
  - `cache_read_tokens`
  - `output_tokens`
  - `reasoning_tokens`
  - `total_tokens`
  - `model_id`
  - `provider_id`
  - `session_id`

Reason to prefer a final summary:

- Agon only needs final aggregate metrics for Harbor.
- It avoids races with async post-step hook execution.
- It lets Lenos define the exact cost/token semantics once.

### Cost Formula Review

Before exposing `cost_usd`, review Lenos' internal cost formula for cache tokens.
Current code appears to price:

```go
CostPer1MInCached  * CacheCreationTokens
CostPer1MOutCached * CacheReadTokens
```

For DeepSeek official provider, cached input hits should likely use
`cost_per_1m_in_cached`, not `cost_per_1m_out_cached`. DeepSeek's current
Catwalk config has `cost_per_1m_out_cached = 0`, so using that for cache reads
would undercount cost.

Recommended Lenos-side fix:

- Clarify Catwalk pricing semantics.
- Add unit tests for:
  - normal uncached input
  - cached input read/hit
  - cache creation/write if supported
  - output tokens
  - DeepSeek official model prices

### Cache Miss in Hook Envelope

Agon currently computes:

```text
input_cache_miss_tokens = input_tokens + cache_creation_tokens
```

That matches Lenos session storage today. Still, Lenos should expose
`cache_miss_tokens` directly so benchmark adapters do not need to know Lenos'
internal definition.

## Recommended Next Steps

1. Lenos: add a final run usage summary.

   Preferred interface:

   ```bash
   lenos run --usage-json /logs/agent/usage-summary.json -m deepseek-v4-flash ...
   ```

   The file should be written only after the run is complete and should include
   `cost_usd`.

2. Lenos: fix or confirm cache-cost pricing.

   Specifically validate DeepSeek official cached input hits use
   `cost_per_1m_in_cached`.

3. Agon: switch from post-step aggregation to Lenos' final usage summary once
   available.

   Keep post-step JSONL as optional debug output if useful, but Harbor metrics
   should come from the final summary.

4. Agon: run a small multi-task smoke before full TB2.

   Suggested first pass:

   ```bash
   make harbor-run DATASET=terminal-bench/terminal-bench-2 MODEL=deepseek-v4-flash TASK=terminal-bench/headless-terminal
   ```

   Then run 3-5 tasks with different profiles:

   - tiny shell task
   - file editing task
   - package/install task
   - longer coding task
   - task expected to fail or timeout, to confirm metrics still land

5. Agon: run full TB2 with one model first.

   Recommended first full run:

   ```bash
   MODEL=deepseek-v4-flash
   ```

   Rationale:

   - Cheaper and faster than pro.
   - Already smoke-tested.
   - Good enough to validate scaffold, metrics, timeouts, and result upload.

6. After first full run, review aggregate metrics before trying pro.

   Check:

   - pass rate
   - exception rate
   - timeout rate
   - total runtime
   - total input/output/cache tokens
   - total cost
   - tasks with missing metrics
   - tasks with suspicious cache hit/miss ratios

7. Then run `deepseek-v4-pro` or the chosen first serious model.

## Open Questions

- Should benchmark cost use provider-billed cost from the API when available,
  or Lenos' model price table?
- Should `total_tokens` include cached input tokens?
- Should cache creation tokens count as miss tokens in benchmark reports?
- Do we want per-step usage retained in final artifacts for debugging, or only
  aggregate usage?

Recommended defaults:

- Use Lenos-computed cost as source of truth.
- For Harbor `n_input_tokens`, include cached input tokens.
- For metadata, expose both:
  - `raw_input_tokens`
  - `input_cache_hit_tokens`
  - `input_cache_miss_tokens`
- Keep per-step `usage.jsonl` for now; remove later if it becomes noisy.
