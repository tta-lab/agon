# Agent Session Journal Feature Draft

## Purpose

Explore a lightweight session journal for Lenos agents.

The journal is a per-session working memory and handoff file, not a full command transcript.

## Proposed Path

```text
.lenos/journals/{session-id}.md
```

## Core Idea

At session start, the Lenos runtime creates the per-session journal from a
standard template before the agent begins work. The agent reads and fills the
initial sections before planning or editing.

The journal should capture:

- task
- goal
- constraints
- environment and available tools
- existing tests and verification entry points
- potential delivery risks
- possible approaches
- decisions
- progress
- verification
- next step

## Design Bias

Keep it short.

Record durable state, not narration.

The first write matters. The journal should push the agent to inspect the
workspace and environment early, especially:

- what tools are available
- what package managers or runtimes exist
- what tests or verifiers already exist
- what final artifacts or service states the task likely requires
- what could prevent delivery even if exploration succeeds

## TB/Harbor Reality

For Terminal-Bench through Harbor, near-timeout closure is hard to make reliable.
Harbor owns the outer agent timeout and may terminate the agent phase directly.
Unless Harbor exposes a soft deadline, or Agon passes Lenos a shorter internal
budget, Lenos cannot count on getting a final cleanup window.

That means the journal MVP should focus on starting better, not rescuing a run
at the last second:

- initial fill before planning or editing
- periodic self-checks during long work
- exit-time final check when the agent chooses to finish normally

The journal is still useful for TB because many failures start early: missing
tool discovery, unclear deliverables, hidden verifier assumptions, environment
state that will not persist, and repeated failed paths.

## Agon/Harbor Integration

In Harbor runs, the journal lives inside a task container that may be deleted at
the end of the trial. Agon should preserve journals as run artifacts.

Prefer a host bind mount over a post-run copy:

- host path: `agon_bench/results/lenos-journals/<job>/<trial>/`
- container path: `/root/.lenos/journals/` or another Lenos-owned journal path
- mount mode: read/write for the Lenos process

This is more reliable than copying at teardown because timeout failures and hard
container cleanup are exactly when the journal is most useful. With a bind
mount, partial journal writes survive even if Harbor kills the agent phase.

Keep the journal artifact path separate from provider secrets. Do not mix it
with `/root/.local/share/lenos`, and do not add secret-bearing paths to the
Temenos sandbox read allowlist.
