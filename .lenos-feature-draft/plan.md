# Session Journal — Implementation Plan

## Decisions Summary

| Question | Decision |
|---|---|
| Scope | Per-session per-task, lenos coder only (no `--agent`). Skip for chat/Q&A. |
| Compaction replacement | Journal replaces `summary.md` + `Summarize()`. Deprecate old codepath. |
| Session identity | Runtime communicates journal path via `JOURNAL=` env var + system message. |
| Enforcement | System instruction (prompt.md + template.md) injected into coder system prompt. |
| Initial fill gate | Prompt-level: "do not edit files until journal filled through Plan." |
| Task detection | Runtime hint after first user message when it looks like a task. |
| Exit reminder | Prompt-level: explicit checklist before final response or exit. |
| Periodic self-check | Prompt-level reread checklist + runtime hint every ~30k input tokens (configurable). |
| Size control | No limits, no compaction, no condensing. Journal grows naturally. |
| Privacy | Already covered: `.lenos/` is in `.gitignore`. Never write secrets to journal. |
| Journal path output | Print once at `lenos run` exit. |
| CLI subcommands | None for MVP. Ctrl+P binding to open in `$EDITOR` as convenience. |
| Agon mount | Bind mount `agon_bench/results/lenos-journals/<job>/<trial>/` → `/root/.lenos/journals/`. |
| Temenos access | Journal excluded from Temenos sandbox. Only Lenos process reads/writes. |

## Files

### In Agon (this repo)

| File | Action |
|---|---|
| `.lenos-feature-draft/template.md` | Updated — structured journal sections |
| `.lenos-feature-draft/prompt.md` | Updated — coder-only scope, task-detection gate, exit/reread rules |
| `.lenos-feature-draft/open-questions.md` | Updated — resolved section, all decisions recorded |
| `.lenos-feature-draft/plan.md` | This file |

### In Lenos (separate repo)

| File | Action |
|---|---|
| `internal/agent/templates/coder.md` | Inject journal prompt + template |
| `internal/agent/templates/summary.md` | Deprecate (or remove once journal is live) |
| `internal/agent/agent_session.go` | Remove `Summarize()` compaction codepath |
| Runtime | Create `.lenos/journals/{session-id}.md` at session start |
| Runtime | Set `JOURNAL=` env var + inject path in first system message |
| Runtime | Inject task-detection hint after first user message (coder only) |
| Runtime | Inject periodic self-check hint every ~30k input tokens |
| Runtime | Print journal path at `lenos run` exit |
| Ctrl+P | Add "open journal" binding (`$EDITOR`) |
| Config | Add `journal_check_interval_tokens` option (default: 30000) |

### In Agon adapter

| File | Action |
|---|---|
| `agon_bench/adapters/lenos.py` | Add journal bind mount to `harbor run` command |
| `Makefile` | Add journal mount to `make harbor-run` |
