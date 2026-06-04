# Model Policy Refusal Blocks Security Tasks

## Run

- Task: `terminal-bench/break-filter-js-from-html`
- Model: `gpt-5.4`
- Job: `2026-06-04__18-52-14`
- Trial: `break-filter-js-from-html__bDHFive`
- Official reward: `0.0`
- Local classification: `model_refusal`

## What Happened

The model refused the task before producing the expected artifact. The same task
was later solved by `deepseek-v4-flash`, although that run hit an agent timeout
after producing a passing artifact.

## Why It Matters

Some TB2 security tasks may be unsuitable for models/providers with strict
security refusal behavior. This is useful for suite planning but is not, by
itself, a Lenos bug.

## Lenos Improvement Lead

Low priority for Lenos. Possible product-side work is limited to better
classification and reporting:

- classify refusal cleanly in scoreboard output
- avoid using refusal-prone models for security tasks in local smoke sweeps
- keep official reward unchanged

## Follow-Up Check

Prefer `deepseek-v4-flash` for local security-task smoke runs, and reserve
`gpt-5.4` for non-security tasks while the goal is finding Lenos runtime gaps.
