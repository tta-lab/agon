# Codex Bootstrap Needs Container-Reachable Proxy

Date: 2026-06-08

## Context

- Adapter: Harbor built-in `codex`
- Tasks hit during investigation:
  - `terminal-bench/configure-git-webserver`
  - `terminal-bench/fix-code-vulnerability`
- Model target: `gpt-5.5`, reasoning `medium`
- Symptom: Harbor failed during Codex setup before model execution or verifier.

## Finding

The host shell proxy includes `HTTP_PROXY=http://127.0.0.1:7890`. Passing that
value into a task container makes npm connect to the container's own loopback,
not the host proxy:

```text
npm error FetchError: request to https://registry.npmjs.org/@openai%2fcodex failed, reason: connect ECONNREFUSED 127.0.0.1:7890
```

From the same task image, `http://host.containers.internal:7890` can reach the
host proxy and `npm install -g @openai/codex@latest` succeeds.

Kosmos already has a host-side installer at
`/home/neil/code/projects/tta-lab/kosmos/modules/common/codex.nix`. It uses
Nix-provided Node, `NPM_CONFIG_PREFIX`, and the WSL proxy helper before running
npm. That script is good for the host, but Harbor task containers need a
container-reachable proxy URL.

## Lenos/Agon Impact

Codex-vs-Lenos comparisons can be invalidated if Codex fails during bootstrap.
The run should be classified as setup failure, not model failure.

## Action Taken

`make codex-run` now passes `CODEX_CONTAINER_PROXY`, defaulting to:

```text
http://host.containers.internal:7890
```

This is passed to both upper- and lower-case proxy env vars so Harbor's Codex
install phase can download nvm, Node, and `@openai/codex`.

