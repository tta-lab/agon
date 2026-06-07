# `src edit` Needs a Clear Raw-Text Recovery Path

## Run

- Task: `terminal-bench/overfull-hbox`
- Model: `deepseek-v4-pro`
- Lenos: `v1.6.0+0.74.1`
- Reasoning: `medium`
- Job: `2026-06-06__20-19-39`
- Trial: `overfull-hbox__ZfUiGnx`
- Official reward: `0.0`

## What Happened

The journal feature worked at session start. The agent recorded the key task
constraints:

- only edit `input.tex`
- do not edit `main.tex` or `synonyms.txt`
- only replace words with synonyms from `synonyms.txt`

It also updated the journal after it found the TeX workaround and identified
the overfull hbox lines.

The run failed later because the agent could not complete the file edits through
the expected `src edit` path. It first used a malformed command shape:

```sh
cd /app/src edit input.tex --section 5
```

Then it tried raw `src edit /app/input.tex`, but concluded that `src` could not
handle `.tex` files after exact text replacements failed. At that point it
stopped and asked whether it could use `sed -i` or Python, instead of continuing
with a correct `src edit` raw-text strategy for the planned synonym
substitutions.

The verifier failed only the overfull hbox check. The file integrity checks for
`main.tex` and `synonyms.txt` passed.

## Why It Matters

Lenos' coder prompt strongly teaches the agent to use `src` for editing. That
is the expected path. But Terminal-Bench includes many non-code or
weakly-structured files: TeX, markdown, JSONL, CSV, logs, config fragments, and
plain text.

For these files, the agent needs a clear `src edit` raw-text mental model. If
that path is unclear, it can turn into a local dead end:

- the agent keeps retrying the same edit tool
- it treats a raw-text matching issue as a policy block
- it asks for permission to use a different editor even though the expected
  editor is still `src edit`
- it loses time after already finding the correct semantic fix

This is not a Terminal-Bench-specific issue. It is a generic `src edit` usage
problem for any agent that must edit both symbol-aware code and plain-text
artifacts.

## Recommendation

Keep `src edit` as the required/default editing path, but make the raw-text
recovery path explicit in the Lenos coder prompt and/or `src edit` guidance:

- Use `src` first for supported code files and symbol-aware edits.
- For unsupported file types, use `src edit` raw text mode when it works.
- If raw `src edit` fails after a small number of exact-match attempts, inspect
  nearby text, reduce the replacement span, and retry with a smaller stable
  match.
- Do not treat unsupported file type as a user-permission block when the user
  already asked you to edit that file with `src edit`.
- After a recovered raw-text edit, run the same verification checks and record
  the recovery in the journal.

The important guardrail is not "find any editor that works." It is "use the
agent's intended editing tool in the way that fits the file, then verify the
requested change."
