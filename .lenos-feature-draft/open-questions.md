# Open Questions

## Resolved

- **Scope**: per-session per-task working document, not per-project long-term
  knowledge base (Codex-style). The journal is task-level state, not
  cross-session aggregated memory.
- **Compaction summary replacement**: journal maintained throughout the session
  makes a separate compaction summary unnecessary. At session end, the agent
  updates `Progress` + `Verification` + `Next` and exits. The next session
  reads the same journal. The `summary.md` template and `Summarize()` codepath
  in Lenos can be deprecated.
- **Harbor instruction delivery**: Harbor passes the TB task description as a
  plain `instruction: str` to the adapter, which `shlex.quote()` wraps and
  places as a positional argument after `--usage-json`. No heredoc, no
  structuring — just raw text.

## Session Identity

- Runtime creates `.lenos/journals/{session-id}.md` once per session.
- Do not create `current.md` as a symlink or pointer.
- Open question: how should users discover the active session id when needed?

## Enforcement

- ~~Should journal maintenance be a system instruction, skill, or runtime feature?~~
  → **System instruction** (MVP). Runtime injects journal instructions into the
    system prompt. A runtime hint is injected after the first user message when
    it looks like a task: "you have received a task, fill the journal before
    proceeding." Only for lenos coder (no --agent flag). Chat Q&A skips the
    journal entirely.
- ~~Should Lenos automatically remind the agent before final response?~~
  → **Prompt-level** (MVP). The exit checklist explicitly requires updating
    Progress, Verification, Next, and Reflection before final response or
    exit. No runtime hook for now.
- ~~Should Lenos enforce the initial fill before the first edit command?~~
  → **Prompt-level** (MVP). "Do not edit, create, or modify files until you
    have filled the journal through the Plan section." No runtime block.
- ~~Should Lenos trigger periodic self-checks after long command sequences or
  meaningful state changes?~~
  → **Prompt + runtime** (MVP). The reread checklist is in prompt.md. The
    runtime additionally injects a reminder hint into the Lenos message queue
    roughly every 50k input tokens (split the typical 200k context window into
    4 chunks).
- ~~Should Agon later pass an internal soft budget to Lenos that is shorter than
  Harbor's hard timeout?~~
  → **No**. Lenos manages its own pacing via the periodic self-check hints
    (configurable threshold, default 30k input tokens). Agon does not need to
    inject a separate timeout signal. Agon's only journal responsibility is
    mounting the journal directory into the container.

## Size Control

- ~~When should old progress entries be summarized?~~
- ~~Should journals have a max token or line budget?~~
  → **No limits, no compaction, no condensing**. The journal grows naturally
    as the agent works. Old entries are never summarized or rewritten. The
    agent can re-read any section as needed. This keeps the full decision
    trail intact. Prompt-level instruction: do not remove or condense past
    entries.

## Privacy

- ~~Should journals be gitignored by default?~~
  → Already covered — `.lenos/` is in `.gitignore`. Journals live under
    `.lenos/journals/` so no additional rule needed.
- What content must never be written to journals?
  → Provider secrets, API keys, tokens, passwords. The journal is plaintext
    and may be mounted into task containers or archived. Never include
    `/root/.local/share/lenos` contents or credential-bearing env var values.

## Product Surface

- ~~Should users see the journal path in CLI output?~~
  → **At exit only**. `lenos run` prints the journal path once when the
    process quits. No startup noise.
- ~~Should there be commands such as `lenos journal show`, `lenos journal summarize`, or `lenos journal continue`?~~
  → **No subcommands for MVP**. But lenos Ctrl+P (interactive command
    palette) should add a binding to open the journal in `$EDITOR`. This is
    a convenience feature, not a new CLI surface.

## Agon/Harbor Artifacts

- ~~Should Agon mount host journal artifact directories into each trial container?~~
  → **Yes, bind mount**. Host: `agon_bench/results/lenos-journals/<job>/<trial>/`,
    container: `/root/.lenos/journals/`. Survives timeout kills.
- ~~Should the mount target be configurable via env var?~~
  → **No**. Hardcoded `/root/.lenos/journals/`. No `LENOS_JOURNAL_DIR` for MVP.
- ~~Should Temenos commands be allowed to read the active journal?~~
  → **No**. Only the Lenos process reads/writes the journal. The journal is
    agent working memory, not sandbox tooling. Temenos `allow_read` stays
    narrow.

All questions in this section resolved. Agon's only journal work: add one bind
mount to `harbor run` args. No Temenos policy changes needed.
