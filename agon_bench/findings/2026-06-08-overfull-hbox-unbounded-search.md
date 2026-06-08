# Overfull-Hbox Timeout: Agent Turned A Local Edit Task Into Unbounded Search

Date: 2026-06-08

## Context

- Task: `terminal-bench/overfull-hbox`
- Model: `gpt-5.5`
- Reasoning effort: `medium`
- Harness: Lenos through Agon/Harbor
- Lenos mode: `--no-sandbox`
- Job: `jobs/2026-06-08__18-35-54`
- Trial: `overfull-hbox__gSmNjFm`
- Official reward: `0.0`
- Exception: `AgentTimeoutError`
- Agent timeout: `1500s`

This rerun was started after the Codex OAuth cache identity fix, to see whether
`overfull-hbox` would get a cleaner cache/cost profile than the earlier Lenos
pass.

## What Happened

The agent understood the task constraints during preflight:

- only edit `input.tex`
- only replace words with allowed synonyms from `synonyms.txt`
- run `pdflatex`
- check for `Overfull \hbox` warnings

The journal captured those constraints correctly. The run still timed out.

The transcript shows the agent moved from targeted edits into a broad local
search. It wrote Python that enumerated synonym combinations and ran `pdflatex`
for each candidate:

```python
for combo in itertools.product(*opts):
    ...
    c, o = test(t)  # runs pdflatex in a temp directory
```

That search had no clear budget or timeout. It ran inside the agent command
until Harbor killed the agent phase. Because the process was killed by the
Harbor timeout, Lenos did not write a final usage summary; the run has no
input/cache/output token data.

## Why This Is Not A Simple Tool Failure

This was not primarily a missing-TeX or sandbox issue. The task files were
readable, `pdflatex` was available, and the agent had already performed several
valid `src edit` replacements.

The failure mode is more subtle:

- The agent wrote a correct high-level plan.
- It did not keep the search local and bounded.
- It began editing whole paragraphs rather than only the smallest likely
  overfull causes.
- It used a brute-force verifier loop with an expensive compiler in the inner
  loop.
- It had no stop condition such as "try at most N candidates per paragraph" or
  "if no improvement after K compiles, switch strategy."

This made an easy human task behave like an expensive combinatorial search.

## Comparison To A Prior Pass

Prior Lenos pass:

- Job: `jobs/2026-06-07__21-54-23`
- Reward: `1.0`
- Input tokens: `624,599`
- Cache hit tokens: `272,640`
- Output tokens: `11,276`

The pass run also used many `pdflatex` calls, but it did not use `itertools` or
a broad brute-force script. It followed a more manual loop: edit a paragraph,
compile, inspect warnings, repeat.

The latest timeout run had fewer visible turns but a worse terminal behavior:
one long-running script consumed the remaining agent time.

## Lenos Improvement Lead

This is an improvement lead, not a settled fix.

Possible generic directions:

- Teach the native coder prompt or journal template to record a search budget
  for constrained search tasks before starting scripts.
- Warn or intervene when a command contains an expensive nested verifier loop
  such as `itertools.product(...)` plus repeated compiler/test execution.
- Encourage greedy/local edits before combinatorial search when the verifier is
  expensive.
- Add command runtime visibility to transcripts and summaries, so slow terminal
  loops are easier to diagnose.
- Make timeout handling preserve partial usage data when possible, so timeout
  runs still count toward cost/cache analysis.

Possible non-goals:

- Do not special-case Terminal-Bench or LaTeX.
- Do not forbid scripts; scripts are useful when bounded and observable.
- Do not overfit this into a synonym-task heuristic before seeing the pattern
  repeat.

## Follow-Up

Track whether similar failures appear in other tasks where the agent creates an
unbounded search or verification loop. If repeated, this points toward a generic
"bounded search discipline" improvement in Lenos rather than a task-specific
fix.
