# TB2 Run Findings

This directory records Lenos improvement leads found while running TB2 smoke
tasks through Agon/Harbor.

Scope:

- Record task, model, run/job, observed behavior, and possible Lenos-side work.
- Keep official verifier results separate from local/manual judgement.
- Do not implement fixes here. The near-term goal is to run enough TB2 cases to
  find the largest Lenos improvement areas.

Current findings:

| Finding | Task | Model | Job | Status |
| --- | --- | --- | --- | --- |
| [TeX tools need broader system read/cache support](./2026-06-04-overfull-hbox-tex-sandbox.md) | `terminal-bench/overfull-hbox` | `deepseek-v4-flash` | `2026-06-04__19-40-39` | candidate Lenos/Temenos improvement |
| [Timeout can hide final usage metrics](./2026-06-04-timeout-usage-summary.md) | `terminal-bench/break-filter-js-from-html` | `deepseek-v4-flash` | `2026-06-04__18-54-35` | candidate Lenos/Harbor adapter improvement |
| [Ephemeral shell state hurts terminal tasks](./2026-06-04-ephemeral-shell-state.md) | `terminal-bench/headless-terminal`, others | multiple | multiple | partly addressed by newer Lenos release; keep watching |
| [Model policy refusal blocks security tasks](./2026-06-04-security-task-refusal.md) | `terminal-bench/break-filter-js-from-html` | `gpt-5.4` | `2026-06-04__18-52-14` | model/provider behavior, not a Lenos bug |
| [Journal template needs stronger verifier-facing sections](./2026-06-06-journal-template-alignment.md) | multiple | multiple | n/a | candidate Lenos prompt/template improvement |
| [Source editing needs a clear fallback policy](./2026-06-06-src-edit-fallback-policy.md) | `terminal-bench/overfull-hbox` | `deepseek-v4-pro` | `2026-06-06__20-19-39` | candidate Lenos prompt/tooling improvement |

Related local artifacts:

- Scoreboard: `agon_bench/results/tb2-scoreboard.html`
- Structured scoreboard: `agon_bench/results/tb2-scoreboard.json`
- Manual scoreboard notes: `agon_bench/results/tb2-scoreboard-notes.json`
- Raw Harbor jobs: `jobs/` (gitignored)
