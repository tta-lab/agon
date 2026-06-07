# Ephemeral Shell State Hurts Terminal Tasks

## Runs

- Task: `terminal-bench/headless-terminal`
- Models: `deepseek-v4-flash`, `deepseek-v4-pro`, `gpt-5.4`
- Jobs: multiple smoke runs on 2026-06-04

## What Happened

Earlier runs showed models assuming shell state persisted between command calls.
That is a poor fit for terminal tasks where agents naturally expect `cd`,
exports, shell functions, and temporary state to carry forward.

Newer Lenos releases may have improved this behavior. Keep this finding as a
watch item while running more TB2 cases.

## Why It Matters

If the shell is ephemeral, models waste turns rediscovering paths or silently
run commands in the wrong directory. This can cause:

- false failures on otherwise simple tasks
- longer runtime
- higher token and cost usage
- confusing transcripts

## Lenos Improvement Lead

Make command execution state explicit and predictable:

- persistent shell/session where safe
- clear transcript markers when a new shell is used
- consistent working directory behavior
- optional guardrails that show current directory and relevant env when command
  state resets

## Follow-Up Check

Track whether future failures include repeated `cd`, missing working directory,
or environment setup commands. If not, this can be marked addressed.
