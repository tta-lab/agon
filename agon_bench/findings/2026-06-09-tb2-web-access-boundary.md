# TB2 Web Access Boundary

Date: 2026-06-09

## Summary

Terminal-Bench 2.0 does not appear to ban internet access in general. The
published paper explicitly says agents may use the internet to install packages
and query relevant web information.

The leaderboard submission rules draw a narrower boundary: agents must not
access Terminal-Bench's own website or GitHub repository, because that can expose
task metadata, tests, reference answers, or oracle solutions.

## Evidence

TB2 paper, Section 5:

> Terminal-Bench is designed to test agents in a realistic environment;
> therefore, we allow agents to access the internet to install packages and query
> the web for relevant information. In theory, an agent could locate our dataset
> and cheat by reading the oracle solutions.

Leaderboard submission validation rules:

> Agents cannot access the Terminal-Bench website or GitHub repository (reward
> hacking)

The same leaderboard rules require official-style submissions to use
`timeout_multiplier = 1.0`, no agent/verifier timeout overrides, no resource
overrides, and at least five trials per task.

## Sites And Patterns To Block Or Flag

These should be treated as benchmark-leakage targets for TB2 leaderboard-style
runs:

- `https://www.tbench.ai/*`
- `https://tbench.ai/*`
- `https://terminal-bench.org/*`
- `https://github.com/harbor-framework/terminal-bench*`
- `https://github.com/harbor-framework/terminal-bench-2*`
- `https://github.com/laude-institute/terminal-bench*`
- `https://raw.githubusercontent.com/harbor-framework/terminal-bench*`
- `https://raw.githubusercontent.com/laude-institute/terminal-bench*`
- `https://huggingface.co/datasets/harborframework/terminal-bench*`
- `https://huggingface.co/datasets/*terminal-bench*`

The Hugging Face patterns are included because TB2 task mirrors and leaderboard
submission repos can expose task contents or trajectory artifacts. They may not
be named in the official one-line rule, but they are equivalent benchmark-data
sources in practice.

## Allowed In Principle

These should not be automatically considered cheating:

- package registries such as PyPI, npm, apt, crates.io, Maven, Conda
- upstream project docs unrelated to Terminal-Bench
- general technical references
- public datasets or leaderboards that are the subject of a task, if the task
  asks for current external information and the source is not a Terminal-Bench
  task/solution mirror

Example: generic BeautifulSoup or XSS articles are web-assisted but not direct
TB2 reward hacking.

## Current Local Impact

The paired token transcript audit found one clear contaminated task:

- `terminal-bench/mteb-leaderboard`

Both Lenos and Codex accessed Terminal-Bench-specific pages or repositories for
that task. It should be excluded from cost/capability comparisons unless the
analysis explicitly studies benchmark-leakage behavior.

The audit also found a web-assisted but not clearly prohibited task:

- `terminal-bench/break-filter-js-from-html`

Lenos searched/fetched generic XSS material. No direct TB2 task or solution
lookup was seen.

## Possible Future Controls

- Add a Harbor/Agon network denylist for known TB2 benchmark-data hosts during
  leaderboard-style runs.
- Add transcript scanning that flags Terminal-Bench URL patterns after each run.
- Add scoreboard note statuses:
  - `benchmark_leakage`
  - `web_assisted_generic`
  - `clean_local`
- Add an adapter/runtime prompt warning: general web access is allowed, but
  Terminal-Bench websites, repositories, task mirrors, oracle solutions, and
  trajectory datasets are not allowed.
- Prefer network-layer enforcement over prompt-only rules when possible.
