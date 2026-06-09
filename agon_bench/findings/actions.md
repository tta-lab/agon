# Action Plan From TB2 Signals

Date: 2026-06-09

This file turns the current high-value TB2 signals into actionable Lenos work.
It is not a task-specific playbook. The goal is to improve general terminal
task performance without special-casing Terminal-Bench.

## Priority 1: Runtime Goal Contract

Hypothesis: a runtime-owned goal feature is the best next layer because it can
control convergence, budget awareness, completion, and blocked-state handling
more directly than the journal.

Mirror from Codex:

- `get_goal`: show objective, status, elapsed time, token use, optional budget,
  and remaining budget.
- `create_goal`: create one concrete objective for the session.
- `update_goal`: let the model mark only `complete` or `blocked`.
- System owns accounting, budget-limited state, usage-limited state, elapsed
  time, and active goal lifecycle.

Lenos-specific shape:

```json
{
  "objective": "write all best chess moves to /app/move.txt",
  "deliverables": ["/app/move.txt"],
  "acceptance": [
    "file exists",
    "contains all winning moves, one per line",
    "contains no extra text"
  ],
  "status": "active",
  "tokens_used": 123456,
  "elapsed_seconds": 180,
  "time_budget_seconds": 900,
  "failed_paths": [
    "stockfish not installed",
    "python-chess not installed"
  ],
  "last_verification": "custom generator found only e2e4"
}
```

Actions:

- Add a per-session goal store owned by runtime, not by model text.
- Auto-create a goal for native coder task sessions from the initial user task.
- Expose goal tools to the model: get, create if absent, update status.
- Add prompt guidance: before marking complete, compare deliverables and
  acceptance checks against current files/results.
- Add runtime checkpoint messages when elapsed time or token use crosses
  thresholds.
- Add a no-progress checkpoint when repeated failed paths accumulate.

Expected impact:

- `overfull-hbox`: less unbounded search and better time awareness.
- `chess-best-move`: less premature "done" before all acceptance conditions.
- `build-cython-ext`: stop sooner once required checks pass.
- `configure-git-webserver`: preserve final verifier-relevant state.

## Priority 2: Mature Domain Tool Selection

Hypothesis: tasks in standard domains fail or cost more when the agent writes
partial local validators instead of using known libraries and CLIs.

Actions:

- Add preflight guidance tied to the goal contract: if the task touches a
  standard domain, identify a mature verifier/tool or record why none is
  practical.
- Prefer package install into temporary isolated locations when system install
  is not appropriate.
- Warn when the agent creates a custom validator for a domain with known edge
  cases; require a note of unsupported cases before trusting it.

Expected impact:

- `chess-best-move`: use `python-chess` instead of a partial move generator.
- Compression, parsing, crypto, protobuf, SQL, numerical, and document-format
  tasks should get more reliable verification paths.

## Priority 3: Multimodal Task Support

Hypothesis: image-grounded tasks currently burn tokens and risk transcription
errors because Lenos relies on ad hoc scripts and text renderings.

Actions:

- Add or expose a first-class image inspection path for native coder sessions.
- Encourage image-to-structured-state as an explicit preflight step.
- Pair image transcription with a domain verifier when the domain has exact
  rules.
- Track image-heavy tasks in the scoreboard so token regressions are visible.

Expected impact:

- `chess-best-move`: faster board-to-FEN transcription.
- `code-from-image`: lower token cost and fewer OCR-style mistakes.
- `gcode-to-text`: better handling of geometry/visual output before deciding
  final text.

## Priority 4: Transcript Cost Controls

Hypothesis: some Lenos passes are too expensive because large command output,
repeated journal reads, and verbose verification logs are reinjected too often.

Actions:

- Summarize long command output before adding it to model context.
- Preserve full logs on disk, but pass compact summaries into the next turn.
- Inject only changed or requested journal sections.
- Show elapsed time for commands and background jobs in the transcript.
- Let the goal contract nudge the agent to stop after required verification
  passes.

Expected impact:

- Lower token cost on build/test-heavy tasks such as `build-cython-ext` and
  `fix-code-vulnerability`.
- Better behavior on slow verifier/search tasks such as `overfull-hbox`.

## Priority 5: Failure Classification

Hypothesis: the current scoreboard mixes real task failures with provider,
network, timeout, and harness failures, which hides useful signal.

Actions:

- Add run-level classifications for provider refusal, network error, setup
  failure, timeout, harness exception, verifier failure, benchmark leakage, and
  web-assisted run.
- Keep official reward unchanged.
- Exclude non-attempt failures from task-skill comparisons by default.
- Keep them visible for harness reliability work.

Expected impact:

- Cleaner Lenos-vs-Codex comparisons.
- Easier prioritization between model behavior, runtime behavior, and Harbor
  adapter reliability.

## Next Step

Draft the Lenos goal MVP first. It is the most central action because it can
feed the other improvements:

- mature tool choice becomes part of goal preflight
- multimodal transcription becomes part of goal state
- output compression is guided by goal relevance
- failure classification maps cleanly to goal status and run outcome
