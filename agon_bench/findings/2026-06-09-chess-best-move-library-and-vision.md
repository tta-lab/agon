# Chess-Best-Move: Prefer Mature Domain Libraries Over Hand-Rolled Rules

Date: 2026-06-09

## Context

Task: `terminal-bench/chess-best-move`

Shared local settings:

- Model: `gpt-5.5`
- Timeout multiplier: `2`
- Trials: `1`
- Lenos: `--no-sandbox`

Runs:

| Harness | Job | Trial | Reward | Agent seconds | Input | Cache hit | Cache miss | Cache hit rate | Output | Total tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Lenos | `2026-06-08__20-34-21` | `chess-best-move__EUnbGBZ` | 0 | 187.1 | 516205 | 436736 | 79469 | 84.6% | 7895 | 524100 |
| Codex CLI | `2026-06-08__21-04-20` | `chess-best-move__4GZfXdZ` | 1 | 77.2 | 128368 | 96768 | 31600 | 75.4% | 1626 | about 129994 |

No direct benchmark solution lookup was seen in either transcript.

## What Happened

The task asks the agent to inspect `/app/chess_board.png` and write all best
White moves to `/app/move.txt`, one per line.

The verifier expects both mate-in-one moves:

```text
e2e4
g2g4
```

Codex CLI passed because it:

- transcribed the board into FEN
- installed `python-chess` into `/tmp/chesslib`
- enumerated legal moves with the mature library
- found both `mate1 e2e4` and `mate1 g2g4`
- wrote both moves

Lenos failed because it:

- inspected the image with PIL and ASCII/ANSI renderings
- reconstructed the position correctly enough to find `e2e4`
- did not install `python-chess`
- wrote a custom simplified chess move generator
- missed `g2g4` because the generator did not implement the initial two-square
  pawn move
- wrote only `e2e4`

The verifier failed with:

```text
assert ['e2e4'] == ['e2e4', 'g2g4']
Right contains one more item: 'g2g4'
```

## Interpretation

This is not mainly a cache accounting issue. Lenos had a higher cache hit rate
than Codex CLI on this run, but still spent roughly 4x the total tokens and
failed. The cost came from a longer image/tooling loop and from building a
domain verifier in the transcript instead of using a tested chess library.

The reusable failure pattern is:

1. The agent recognized that a domain-specific verifier would help.
2. It checked whether the tool was installed.
3. After finding no local chess package, it hand-rolled incomplete domain logic.
4. The incomplete logic produced a confident but partial answer.

## Lenos Improvement Leads

- Strengthen the agent's bias toward installing or using mature libraries for
  standard domains such as chess, compression, parsing, serialization,
  cryptography, numerical computing, and document formats.
- When the agent builds a verifier from scratch, require it to list known
  unsupported rules or edge cases before trusting the result.
- Improve multimodal task support. This run spent many tokens turning the chess
  image into text through ad hoc PIL/ASCII renderings. A first-class image view
  or vision path would likely reduce both tokens and error surface.
- For image-to-structured-state tasks, encourage a two-step shape:
  transcribe image to a compact state representation, then validate with a
  domain library.

## Follow-Up

Record this as a cross-task signal rather than a chess-specific prompt hack.
The goal is not to special-case TB2 chess, but to make Lenos better at choosing
reliable external verification paths before writing custom logic.
