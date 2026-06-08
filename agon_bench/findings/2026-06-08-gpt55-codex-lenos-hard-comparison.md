# GPT-5.5 Medium: Codex CLI vs Lenos on Two Hard TB2 Tasks

Date: 2026-06-08

## Context

Goal: compare Harbor built-in Codex CLI and Agon Lenos on two additional hard
Terminal-Bench 2.0 tasks using the same local settings.

Shared settings:

- Model: `gpt-5.5`
- Reasoning effort: `medium`
- Timeout multiplier: `2`
- Trials: `1`
- Lenos: `--no-sandbox`

Tasks:

- `terminal-bench/configure-git-webserver`
- `terminal-bench/fix-code-vulnerability`

## Results

| Task | Agent | Reward | Agent seconds | Input | Cache hit | Cache miss | Cache hit rate | Output | Reasoning | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `configure-git-webserver` | Codex CLI | 0 | 160.4 | 335005 | 263936 | 71069 | 78.8% | 4117 | n/a | $0.610823 |
| `configure-git-webserver` | Lenos | 1 | 108.5 | 94119 | 19200 | 74919 | 20.4% | 4431 | 674 | $0 |
| `fix-code-vulnerability` | Codex CLI | 1 | 86.2 | 331453 | 237952 | 93501 | 71.8% | 2007 | n/a | $0.646691 |
| `fix-code-vulnerability` | Lenos | 1 | 345.2 | 339261 | 76288 | 262973 | 22.5% | 4079 | 1073 | $0 |

Job IDs:

- Codex `configure-git-webserver`: `jobs/2026-06-08__15-08-19`
- Lenos `configure-git-webserver`: `jobs/2026-06-08__15-12-23`
- Codex `fix-code-vulnerability`: `jobs/2026-06-08__15-15-29`
- Lenos `fix-code-vulnerability`: `jobs/2026-06-08__15-17-58`

## Notable Behavior

On `configure-git-webserver`, Codex built a working setup during its own local
test, then reset `/git/server` and the web root back to empty so the user's
future push flow would create the first commit. That made sense as an
interpretation of the prompt, but TB2 verifies final container state. The
official verifier then got HTTP 404 for `/hello.html`.

Lenos passed the same task because it left the deployed `hello.html` reachable
on port 8080 at final state.

On `fix-code-vulnerability`, both passed. Lenos took about 4x longer in agent
execution and used about 2x the output tokens, but produced a full usage summary
including reasoning tokens and cache miss tokens. Codex CLI reported cost and a
much higher cache hit rate through Harbor's built-in result fields.

The cache denominator was checked after this run. Fantasy's OpenAI Responses
mapping treats provider `input_tokens` as inclusive of cached tokens and exposes
`Usage.InputTokens = input_tokens - cached_tokens`; Lenos then reports
`input_tokens = raw_input_tokens + input_cache_hit_tokens`. That matches the
Codex CLI event shape, where `input_tokens` is inclusive and
`cached_input_tokens` is the hit count. So the low Lenos cache hit rate is not
obviously an arithmetic/display bug in Agon. It is more likely due to Lenos'
request/session shape, tool transcript churn, journal/context content, or a
provider-path difference.

## Lenos Improvement Leads

- Lenos cache hit rate through the Codex OAuth provider is still much lower than
  Codex CLI on these two runs. This may be from prompt/session shape, tool
  wrapping, journal contents, or provider request construction.
- Lenos no-sandbox runs still install `bubblewrap`. If `--no-sandbox` is the
  normal TB2 smoke setting, skip bwrap installation in that path to reduce setup
  cost.
- The `configure-git-webserver` difference reinforces a generic lesson: tasks
  are judged by final environment state, not by whether a hypothetical future
  user command would work. Journal/preflight wording may need to remind the
  agent to preserve verifier-relevant final artifacts after self-tests.
