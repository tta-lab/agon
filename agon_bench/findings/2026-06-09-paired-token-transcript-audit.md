# Paired Token Transcript Audit

Date: 2026-06-09

## Scope

This note covers the local `gpt-5.5` medium Lenos-vs-Codex CLI TB2 smoke
scoreboard after reaching 50 shared tasks.

- Scoreboard source: `agon_bench/results/tb2-scoreboard.json`
- Job directory range: `jobs/2026-06-07__16-25-43` through the custom
  `jobs/lenos-*` / `jobs/codex*` jobs created around `2026-06-09 00:xx`
  Asia/Taipei.
- Compared sample: 50 shared tasks with at least one Lenos run and one Codex CLI
  run for `gpt-5.5`.
- Pass sample inspected for token asymmetry: 27 `11` tasks, where both Lenos and
  Codex CLI have a passing run and usable token fields.
- Selection rule for comparison rows: latest passing run per harness if present;
  otherwise latest run. For this audit, only `11` rows were used.

This is not an official leaderboard run. It uses local smoke settings and one
trial per task, not official `-k 5` averaging.

## Token Extremes Checked

Lenos much lower token use:

| Task | Lenos tokens | Codex tokens | Lenos/Codex | Audit result |
| --- | ---: | ---: | ---: | --- |
| `terminal-bench/nginx-request-logging` | 21,051 | 190,207 | 0.11 | No external solution lookup seen. Local nginx setup and curl verification. |
| `terminal-bench/git-multibranch` | 57,340 | 421,480 | 0.14 | No external solution lookup seen. Local SSH/Git/Nginx setup and verification. |
| `terminal-bench/multi-source-data-merger` | 21,424 | 156,976 | 0.14 | No external solution lookup seen. Local data inspection and merge script. |

Codex much lower token use:

| Task | Lenos tokens | Codex tokens | Lenos/Codex | Audit result |
| --- | ---: | ---: | ---: | --- |
| `terminal-bench/mteb-leaderboard` | 714,878 | 61,747 | 11.58 | Contaminated. Exclude from cost comparison. |
| `terminal-bench/code-from-image` | 635,309 | 189,653 | 3.35 | No benchmark solution lookup seen. Lenos spent heavily on OCR/image tooling; Codex solved more directly. |
| `terminal-bench/fix-code-vulnerability` | 511,936 | 333,460 | 1.54 | No external solution lookup seen. Local repo/test investigation. |
| `terminal-bench/break-filter-js-from-html` | 587,920 | 446,394 | 1.32 | Web-assisted by Lenos for generic BeautifulSoup/XSS bypass research; not direct benchmark solution lookup. Mark separately if comparing pure local task-solving. |

## Clear Problem Case

### `terminal-bench/mteb-leaderboard`

This task is not safe for cost/capability comparison in the current sample.

Lenos transcript:

- `jobs/lenos-terminal-bench_mteb-leaderboard-20260608230934-27534/mteb-leaderboard__3VYd3Cx/agent/lenos.txt`
- The agent fetched the public task repository path:
  `https://raw.githubusercontent.com/harbor-framework/terminal-bench-2-1/main/tasks/mteb-leaderboard/README.md`
- The journal records: `README verification says /app/result.txt must contain
  exactly GritLM/GritLM-7B`.
- That is effectively using benchmark reference information, not independently
  solving from the task data.

Codex transcript:

- `jobs/codex2-terminal-bench_mteb-leaderboard-20260609001016-30586/mteb-leaderboard__ehsgB2N/agent/codex.txt`
- The agent searched a tbench registry URL:
  `https://www.tbench.ai/registry/terminal-bench-core/head/mteb-leaderboard`
- It then wrote that it found the benchmark's archived August 2025 solution and
  produced `GritLM/GritLM-7B`.

Action: exclude `mteb-leaderboard` from token/cost comparisons unless the
comparison is explicitly about web-accessible benchmark leakage.

## Web-Assisted But Not Direct Solution Lookup

### `terminal-bench/break-filter-js-from-html`

Lenos transcript:

- `jobs/lenos-terminal-bench_break-filter-js-from-html-20260608232020-12108/break-filter-js-from-html__ZzRsx3n/agent/lenos.txt`
- The agent used `web search "BeautifulSoup html.parser XSS bypass onerror
  script tag mXSS"` and fetched a generic mutation-XSS article.
- It did not appear to search for the TB task, registry entry, oracle answer, or
  benchmark solution.

Codex transcript:

- `jobs/codex-terminal-bench_break-filter-js-from-html-20260608235109-28595/break-filter-js-from-html__WvgK7hG/agent/codex.txt`
- No direct benchmark solution lookup seen.

Action: keep this task in the main comparison only if web-assisted generic
research is acceptable. Otherwise tag it separately.

## Current Interpretation

After excluding `mteb-leaderboard`, the most obvious contamination signal is
removed. The remaining inspected extremes support a more modest conclusion:

- Lenos can be much cheaper on some local configuration and data-processing
  tasks.
- Codex can be cheaper on some tasks that require visual/OCR interpretation or
  broader exploratory loops.
- The current evidence does not prove a clear capability gain for Lenos.
- The cost advantage should be described as modest and sample-dependent, not
  decisive.

## Follow-Up

- Update the scoreboard summary to support an exclusion/tag list for
  contaminated or web-assisted tasks.
- Add per-row audit labels such as `clean`, `web_assisted`, and
  `benchmark_leakage`.
- Recompute cost ratios with `mteb-leaderboard` excluded and optionally with
  web-assisted tasks excluded.
