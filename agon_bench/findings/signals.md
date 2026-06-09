# Cross-Task Improvement Signals

This file collects repeated or high-value signals from TB2 smoke runs. These
are not implementation plans. They are prompts for later Lenos work.

## Runtime Goal Control May Be The Breakthrough Layer

Signal source:

- `terminal-bench/overfull-hbox`
- `terminal-bench/chess-best-move`
- `terminal-bench/build-cython-ext`
- `terminal-bench/configure-git-webserver`
- Codex goal implementation in `openai/codex`

Observed pattern:

- The session journal helps the agent record intent, but it is still soft text.
- Agents can keep exploring after the likely delivery path is known.
- Agents can call a task done before checking all acceptance conditions.
- Agents can spend large token budgets on a passing task because nothing says
  "the goal is satisfied; stop now."
- Agents do not have a first-class, model-visible view of remaining time,
  token budget, failed paths, or current delivery status.

Desired direction:

- Add a runtime-owned goal contract for native coder sessions.
- Mirror the useful parts of Codex's goal feature: objective, status, elapsed
  time, token use, optional budget, and runtime-controlled status transitions.
- Keep the model responsible for marking `complete` or `blocked`, but keep
  accounting and budget state system-owned.
- Use the goal as the control plane and the journal as supporting notes.

Why this is high value:

- It can address several current failure classes at once: unbounded search,
  premature completion, missing final deliverables, and high-token passes.
- It is generic. It does not require TB-specific task hints.

## Prefer Mature Domain Libraries

Signal source:

- `terminal-bench/chess-best-move`
- Finding: `2026-06-09-chess-best-move-library-and-vision.md`

Observed pattern:

- The agent identified a standard domain where exact rules matter.
- A mature package would have made verification cheap and reliable.
- The agent instead wrote simplified local logic.
- The simplified logic missed a rule edge case and produced a confident wrong
  answer.

Desired direction:

- Make agents more willing to install or call mature libraries when the domain
  has established tooling.
- Treat hand-rolled validators as suspect unless the agent explicitly states
  unsupported cases and verifies they are irrelevant.
- Make this part of goal/preflight: if the task touches a standard domain,
  record the chosen mature tool or explain why none is practical.
- Keep this generic. Do not add TB-specific solution hints.

## Improve Multimodal Task Support

Signal source:

- `terminal-bench/chess-best-move`
- Earlier paired-token audit noted similar token-heavy behavior on
  `terminal-bench/code-from-image`.

Observed pattern:

- Lenos can solve or nearly solve image-grounded tasks, but often spends many
  tokens converting images into text through ad hoc scripts, ASCII renderings,
  or repeated local inspection.
- This increases token use and makes state transcription errors more likely.

Desired direction:

- Add or expose a better image inspection path for Lenos agent sessions.
- Help the agent create compact structured state from images before reasoning.
- For image tasks in standard domains, pair visual transcription with a domain
  verifier whenever possible.

## Compress Tool Output And Journal Context

Signal source:

- `terminal-bench/build-cython-ext`
- `terminal-bench/fix-code-vulnerability`
- `terminal-bench/overfull-hbox`
- `terminal-bench/break-filter-js-from-html`

Observed pattern:

- Some successful Lenos runs use hundreds of thousands to over one million
  tokens.
- High cache hit rate does not fully solve this. Large command output,
  repeated journal reads, and verbose build/test logs still increase cost.
- Passing tasks can keep accumulating transcript after the key acceptance check
  is already satisfied.

Desired direction:

- Summarize long command output before reinjecting it into the next turn.
- Keep volatile logs away from the stable cached prefix when possible.
- Inject only the journal sections needed for the current checkpoint.
- Let the goal contract encourage stopping once required verification passes.

## Classify Provider And Harness Failures Separately

Signal source:

- `terminal-bench/password-recovery`
- `terminal-bench/prove-plus-comm`
- `terminal-bench/qemu-startup`
- `terminal-bench/sqlite-with-gcov`
- `terminal-bench/tune-mjcf`

Observed pattern:

- Some rows are marked as task failures even though the model never made a real
  attempt, for example provider policy refusal, network EOF, or harness
  exception.
- Mixing these with real task failures makes capability and cost comparison
  noisy.

Desired direction:

- Preserve separate classes for provider refusal, network error, setup failure,
  timeout, harness exception, and verifier failure.
- Keep these visible in the scoreboard and exclude them from task-skill
  conclusions unless the question is harness reliability.
