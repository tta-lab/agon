# Journal Template Needs Stronger Verifier-Facing Sections

## Context

- Lenos release reviewed: `v1.6.0+0.74.1`
- Lenos files reviewed:
  - `/home/neil/code/projects/tta-lab/lenos/internal/agent/templates/journal.md`
  - `/home/neil/code/projects/tta-lab/lenos/internal/agent/templates/coder.md`
  - `/home/neil/code/projects/tta-lab/lenos/internal/agent/journal.go`
- Agon run focus: rerun prior TB2 failures with journals enabled.

## What We Verified

Lenos now has the core journal feature:

- per-session journal creation under `.lenos/journals/{session-id}.md`
- `LENOS_JOURNAL` exposure to the agent
- initial journal-fill prompt for task sessions
- periodic self-check hints
- compact/auto-compact handoff hints
- Ctrl+P journal open support

This is the right layer for several TB2 failure modes we observed: unclear final
artifacts, hidden verifier expectations, environment isolation traps, service
lifetime issues, and repeated failed paths.

## Gap

The current `coder.md` periodic self-check asks the agent to reread these
sections:

- `Environment`
- `Deliverables`
- `Potential Delivery Risks`
- `Existing Verification`
- `Failed Paths`
- `Verification`

But the embedded `journal.md` template only has:

- `Task`
- `Context`
- `Environment`
- `Plan`
- `Progress`
- `Verification`
- `Next`

Some concepts exist as bullets inside broader sections, but the section names do
not line up. That weakens the reminder because the agent is told to inspect
headings that are not present.

## Why It Matters

The missing first-class sections map directly to recent TB2 misses:

- `Deliverables`: helps avoid solving most of the task while missing the exact
  final file, output case, service state, or consumer path.
- `Existing Verification`: pushes the agent to find/read tests and verifier
  assertions before editing.
- `Potential Delivery Risks`: makes environment isolation, non-persistent
  state, dependency scope, and background process lifetime explicit early.
- `Failed Paths`: prevents long exploratory loops from repeating the same
  failed approach.

For tasks like `terminal-bench/overfull-hbox`, `kv-store-grpc`, and
`crack-7z-hash`, these sections are not decoration. They are the specific
checks that could change the agent's first plan.

## Recommendation

Update Lenos' embedded `journal.md` to match the prompts it already gives.
Keep the template short, but make these sections first-class:

- `Goal`
- `Existing Verification`
- `Deliverables`
- `Potential Delivery Risks`
- `Failed Paths`

Also add verifier-facing prompts:

- What exact file, output, service, or state will the verifier consume?
- Are any files forbidden or risky to edit?
- Can the official verifier or a close proxy be run?
- If dependencies are installed, will the verifier/runtime see them?
- What fallback applies after an approach fails or takes too long?

This keeps the feature generic. It does not specialize Lenos for Terminal-Bench;
it asks the agent to make normal task delivery assumptions explicit.

## Follow-Up Run Evidence

### `terminal-bench/kv-store-grpc`

- Job: `2026-06-06__20-33-25`
- Trial: `kv-store-grpc__Luvyen5`
- Model: `deepseek-v4-pro`
- Reasoning: `medium`
- Timeout multiplier: `2.0`
- Reward: `0.0`

The journal helped at session start. It recorded the important prior failure
area:

- user/system constraint: `system-wide pip install`
- persistence trap: generated files must be in `/app`
- done means: server on port `5328` responding to `GetVal`/`SetVal`

But after global package installation failed, the agent pivoted to `/app/venv`
without recording the risk or checking whether the verifier would import
packages from that environment. The verifier then failed system-Python `grpc`
imports, server process checks, and expected `server.py` structure.

This confirms the template needs stronger verifier-facing prompts, not just a
generic `Risks` bullet:

- Which Python/runtime will the verifier use?
- If a dependency is installed in a venv or target dir, will the verifier see
  it?
- What exact symbols/classes does the verifier assert in generated files?
- Will a background service remain alive after the command that started it?

The journal should make these checks explicit before the agent treats local
smoke success as completion.

### `terminal-bench/crack-7z-hash`

- Job: `2026-06-06__20-43-18`
- Trial: `crack-7z-hash__GYu4V35`
- Model: `deepseek-v4-pro`
- Reasoning: `medium`
- Timeout multiplier: `2.0`
- Result: `AgentTimeoutError` after `3600s`
- Reward: `0.0`

This run showed a stricter timing failure mode. The journal file was created and
mounted correctly, and the transcript began with:

```sh
cat $LENOS_JOURNAL
```

But the agent did not write any initial task facts back to the journal before
starting work. Several minutes into the run, the journal was still the empty
template. The agent was already exploring tools, installing dependencies, and
trying `7z2john`/CPAN/header-parsing paths without recording goal, constraints,
risks, or failed paths. It later filled the journal, and the filled content was
useful, but it arrived after the broad exploration had already happened.

This suggests the session-start journal fill is currently advisory rather than
reliably enforced at the start of work. For TB-style tasks, the useful behavior
is not just "a journal file eventually contains state"; it is "the agent must
externalize the task model before broad tool use starts."

Recommendation:

- Treat the first journal write as a required task-start step for coding
  agents, not just a suggestion.
- If the journal still contains empty placeholders after the first read, prompt
  again before allowing broad exploration.
- Consider a minimal structured preflight that only requires a few fields:
  `Goal`, `Deliverable`, `Verifier Consumer`, `Known Constraints`, and
  `First Verification`.

The final failure was simple: Harbor killed `lenos run` at the agent timeout,
then the verifier failed because `/app/solution.txt` did not exist. Since the
agent timed out, no `usage-summary.json` was produced, so cost, token, and cache
metrics were missing for this run.

The filled journal did capture useful state later:

- goal: extract `secret_file.txt` from `secrets.7z`
- deliverable: write the recovered word to `/app/solution.txt`
- constraints: no `p7zip`, broken `apt`, no `pip3`, missing Perl LZMA support
- failed paths: Python `lzma`, pip install, apt install, CPAN install

But the agent kept exploring low-probability toolchain paths until timeout
instead of converting the failed-path list into a stop-and-reassess point. This
suggests another generic improvement: journal checks should include a
no-progress budget. After repeated failed dependency/tool paths, the agent
should either choose a simpler final-deliverable attempt, prove that the current
path is still likely to finish inside the remaining time, or mark the blocker
explicitly before Harbor kills the run.
