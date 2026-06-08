# Lenos Uses More Tokens Than Codex CLI On The Same Task

## Runs

- Task: `terminal-bench/overfull-hbox`
- Model: `gpt-5.5`
- Codex CLI comparison run:
  - Job: `2026-06-07__16-31-41`
  - Trial: `overfull-hbox__J7cPhd5`
  - Official reward: `1.0`
- Lenos latest no-sandbox run:
  - Job: `2026-06-08__14-32-10`
  - Trial: `overfull-hbox__b7udwJv`
  - Official reward: `0.0`
- Lenos prior pass run:
  - Job: `2026-06-07__21-54-23`
  - Trial: `overfull-hbox__D4h9J4m`
  - Official reward: `1.0`

## What Happened

On the same task and same model, the Lenos run consumed substantially more
tokens than the Codex CLI run and had a much lower cache hit rate.

Codex CLI pass run:

- Input tokens: `214,771`
- Cache hit tokens: `173,312`
- Output tokens: `6,863`
- Approx total tokens: `221,634`
- Cache hit rate: `80.7%`

Lenos latest no-sandbox run:

- Input tokens: `542,419`
- Cache hit tokens: `241,152`
- Output tokens: `12,849`
- Total tokens: `555,268`
- Cache hit rate: `44.5%`

Lenos prior pass run:

- Input tokens: `624,599`
- Cache hit tokens: `272,640`
- Output tokens: `11,276`
- Total tokens: `635,875`
- Cache hit rate: `43.7%`

The latest Lenos run did reach the task's functional objective locally:
`pdflatex` succeeded, no `Overfull \hbox` warnings remained, and `main.tex` plus
`synonyms.txt` were unchanged. The official verifier failed because one
replacement in `input.tex` was not in the allowed synonym family:

```text
unmistakable -> clear
```

## Why It Matters

The gap is not explained only by success versus failure. A prior Lenos pass on
the same task still used about `2.9x` the approximate total tokens of the Codex
CLI pass and had roughly half the cache hit rate.

This makes full TB2 sweeps materially more expensive and slower for Lenos, even
before considering task failures. It also suggests that Lenos' current loop and
context shape may not align well with provider-side prompt caching.

Possible contributors visible in the transcript:

- large repeated command outputs and TeX logs entering later context
- journal content being appended and reread through the run
- repeated whole-paragraph `src edit` attempts
- exploratory brute-force synonym search after several manual edits
- lack of a task-specific checker for the synonym constraint, causing more
  trial-and-error and still missing one verifier rule

## Lenos Improvement Lead

Treat token/cache efficiency as a first-class TB2 metric, not just an accounting
field.

Promising directions:

- keep stable system/tool/journal scaffolding cache-friendly across turns
- keep volatile command output out of the stable cached prefix when possible
- aggressively summarize or mask old low-value observations before the next
  model call
- provide shorter structured command-output summaries for common verification
  loops
- avoid repeatedly injecting the full journal when only a few sections matter
- add explicit final-check affordances for constrained transforms, such as
  "all token replacements must be members of an allowed set"

## Follow-Up Check

For each repeated task, compare Lenos against Codex CLI on:

- official reward
- total tokens
- raw input tokens
- cache hit tokens
- cache hit rate
- output and reasoning tokens
- agent execution time

Track this in the scoreboard so regressions in cache hit rate or token cost are
visible even when a task passes.
