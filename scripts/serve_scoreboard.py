#!/usr/bin/env python3
"""Serve a live TB2 scoreboard rendered from jobs/ on each request."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import update_scoreboard


ROOT = Path(__file__).resolve().parents[1]
HTML_ROUTE = "/agon_bench/results/tb2-scoreboard.html"
JSON_ROUTE = "/agon_bench/results/tb2-scoreboard.json"
SUMMARY_ROUTE = "/summary"
SUMMARY_TEXT_ROUTE = "/summary.txt"
SUMMARY_JSON_ROUTE = "/summary.json"
SUMMARY_MODEL = "gpt-5.5"
SUMMARY_THINKING = "medium"
GPT55_CACHE_MISS_INPUT_USD_PER_TOKEN = 5 / 1_000_000
GPT55_CACHE_HIT_INPUT_USD_PER_TOKEN = 0.5 / 1_000_000
GPT55_OUTPUT_USD_PER_TOKEN = 30 / 1_000_000


def live_payload() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": update_scoreboard.collect_entries(),
    }


def task_keys_with_both_harnesses(entries: list[dict]) -> list[str]:
    harnesses_by_task = {}
    for entry in entries:
        if entry.get("model") != SUMMARY_MODEL:
            continue
        harness = entry.get("harness")
        if harness not in {"Lenos", "Codex CLI"}:
            continue
        harnesses_by_task.setdefault(entry.get("task_key"), set()).add(harness)
    return sorted(
        task
        for task, harnesses in harnesses_by_task.items()
        if task and harnesses == {"Lenos", "Codex CLI"}
    )


def latest_entry(
    entries: list[dict], task: str, harness: str, *, successful: bool = False
) -> dict | None:
    matches = [
        entry
        for entry in entries
        if entry.get("task_key") == task
        and entry.get("harness") == harness
        and entry.get("model") == SUMMARY_MODEL
        and (not successful or entry.get("reward") == 1.0)
    ]
    if not matches:
        return None
    return max(matches, key=lambda entry: entry.get("job") or "")


def mean(values: list[float]) -> float:
    if not values:
        return 0
    return sum(values) / len(values)


def ratio_delta_text(ratio: float) -> tuple[str, str]:
    if ratio < 1:
        return f"{(1 - ratio) * 100:.1f}%", "less"
    if ratio > 1:
        return f"{(ratio - 1) * 100:.1f}%", "more"
    return "0.0%", "the same"


def estimated_gpt55_cost(row: dict, prefix: str) -> float | None:
    cache_hit = row.get(f"{prefix}_cache_tokens")
    cache_miss = row.get(f"{prefix}_cache_miss_tokens")
    output = row.get(f"{prefix}_output_tokens")
    if not all(isinstance(value, int) for value in (cache_hit, cache_miss, output)):
        return None
    return (
        cache_miss * GPT55_CACHE_MISS_INPUT_USD_PER_TOKEN
        + cache_hit * GPT55_CACHE_HIT_INPUT_USD_PER_TOKEN
        + output * GPT55_OUTPUT_USD_PER_TOKEN
    )


def task_row_for(task: str, entries: list[dict]) -> dict:
    lenos_success = latest_entry(entries, task, "Lenos", successful=True)
    codex_success = latest_entry(entries, task, "Codex CLI", successful=True)
    lenos_latest = latest_entry(entries, task, "Lenos")
    codex_latest = latest_entry(entries, task, "Codex CLI")
    lenos_display = lenos_success or lenos_latest or {}
    codex_display = codex_success or codex_latest or {}
    return {
        "task": task,
        "lenos_pass": bool(lenos_success),
        "codex_pass": bool(codex_success),
        "lenos_job": lenos_display.get("job"),
        "codex_job": codex_display.get("job"),
        "lenos_input_tokens": lenos_display.get("input_tokens"),
        "codex_input_tokens": codex_display.get("input_tokens"),
        "lenos_cache_tokens": lenos_display.get("cache_tokens"),
        "codex_cache_tokens": codex_display.get("cache_tokens"),
        "lenos_cache_miss_tokens": lenos_display.get("cache_miss_tokens"),
        "codex_cache_miss_tokens": codex_display.get("cache_miss_tokens"),
        "lenos_output_tokens": lenos_display.get("output_tokens"),
        "codex_output_tokens": codex_display.get("output_tokens"),
        "lenos_agent_seconds": lenos_display.get("agent_seconds"),
        "codex_agent_seconds": codex_display.get("agent_seconds"),
    }


def comparison_summary(payload: dict) -> dict:
    tasks = task_keys_with_both_harnesses(payload["entries"])
    lenos_successes = [
        latest_entry(payload["entries"], task, "Lenos", successful=True)
        for task in tasks
    ]
    codex_successes = [
        latest_entry(payload["entries"], task, "Codex CLI", successful=True)
        for task in tasks
    ]
    lenos_successes = [entry for entry in lenos_successes if entry]
    codex_successes = [entry for entry in codex_successes if entry]
    successful_pairs = []
    for task in tasks:
        lenos = latest_entry(payload["entries"], task, "Lenos", successful=True)
        codex = latest_entry(payload["entries"], task, "Codex CLI", successful=True)
        if lenos and codex:
            successful_pairs.append({"task": task, "lenos": lenos, "codex": codex})

    task_rows = [task_row_for(task, payload["entries"]) for task in tasks]
    lenos_seconds = sum(row.get("lenos_agent_seconds") or 0 for row in task_rows)
    codex_seconds = sum(row.get("codex_agent_seconds") or 0 for row in task_rows)
    lenos_input = sum(row.get("lenos_input_tokens") or 0 for row in task_rows)
    codex_input = sum(row.get("codex_input_tokens") or 0 for row in task_rows)
    time_ratios = [
        row["lenos_agent_seconds"] / row["codex_agent_seconds"]
        for row in task_rows
        if row.get("lenos_agent_seconds") and row.get("codex_agent_seconds")
    ]
    token_ratios = [
        token_total(row, "lenos") / token_total(row, "codex")
        for row in task_rows
        if token_total(row, "lenos") and token_total(row, "codex")
    ]
    mean_time_ratio = mean(time_ratios)
    mean_token_ratio = mean(token_ratios)
    token_delta, token_word = ratio_delta_text(mean_token_ratio)
    lenos_cost = sum(
        cost
        for row in task_rows
        if (cost := estimated_gpt55_cost(row, "lenos")) is not None
    )
    codex_cost = sum(
        cost
        for row in task_rows
        if (cost := estimated_gpt55_cost(row, "codex")) is not None
    )
    cost_ratio = lenos_cost / codex_cost if codex_cost else 0
    cost_delta, cost_word = ratio_delta_text(cost_ratio)

    sentence = (
        f"On the same {SUMMARY_MODEL} model with {SUMMARY_THINKING} thinking, "
        f"Lenos has successful runs on {len(lenos_successes)}/{len(tasks)} shared "
        f"tasks versus Codex CLI's {len(codex_successes)}/{len(tasks)}. Using the "
        f"Codex-observed {SUMMARY_MODEL} rates across all shared tasks, Lenos cost "
        f"${lenos_cost:.2f} versus Codex CLI's ${codex_cost:.2f} "
        f"({cost_delta} {cost_word}); equal-task token ratio was "
        f"{mean_token_ratio:.2f}x."
    )
    max_cost = max(lenos_cost, codex_cost, 1)
    return {
        "sentence": sentence,
        "model": SUMMARY_MODEL,
        "thinking": SUMMARY_THINKING,
        "shared_tasks": tasks,
        "paired_success_tasks": [pair["task"] for pair in successful_pairs],
        "paired_success_count": len(successful_pairs),
        "task_rows": task_rows,
        "lenos": {
            "passes": len(lenos_successes),
            "agent_seconds": round(lenos_seconds, 1),
            "input_tokens": lenos_input,
        },
        "codex_cli": {
            "passes": len(codex_successes),
            "agent_seconds": round(codex_seconds, 1),
            "input_tokens": codex_input,
        },
        "mean_ratios": {
            "agent_seconds": mean_time_ratio,
            "total_tokens": mean_token_ratio,
        },
        "estimated_cost": {
            "pricing": "gpt-5.5 inferred from Codex CLI: $5/M cache-miss input, $0.5/M cache-hit input, $30/M output",
            "lenos": lenos_cost,
            "codex_cli": codex_cost,
            "ratio": cost_ratio,
            "lenos_share": lenos_cost / max_cost,
            "codex_cli_share": codex_cost / max_cost,
            "token_ratio": mean_token_ratio,
        },
    }


def fmt_number(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.1f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def fmt_money(value: object) -> str:
    if not isinstance(value, int | float):
        return ""
    return f"${value:,.3f}"


def token_total(row: dict, prefix: str) -> int:
    return sum(
        value
        for value in (
            row.get(f"{prefix}_input_tokens"),
            row.get(f"{prefix}_output_tokens"),
        )
        if isinstance(value, int)
    )


def stacked_token_bar(row: dict, prefix: str, label: str, max_total: int) -> str:
    cache_hit = row.get(f"{prefix}_cache_tokens")
    cache_miss = row.get(f"{prefix}_cache_miss_tokens")
    output = row.get(f"{prefix}_output_tokens")
    total = token_total(row, prefix)
    if total <= 0:
        return (
            f"<div class=\"mini-bar missing\"><span>{label}</span>"
            "<div class=\"track\"></div><b>no token data</b></div>"
        )

    width = total / max(max_total, 1) * 100
    segments = []
    for name, value in (
        ("hit", cache_hit),
        ("miss", cache_miss),
        ("out", output),
    ):
        if isinstance(value, int) and value > 0:
            segments.append(
                f"<i class=\"seg {name}\" style=\"width:{value / total * 100:.3f}%\"></i>"
            )
    return (
        f"<div class=\"mini-bar\"><span>{label}</span>"
        f"<div class=\"track\"><div class=\"stack\" style=\"width:{width:.3f}%\">"
        f"{''.join(segments)}</div></div><b>{fmt_number(total)}</b></div>"
    )


def token_ratio_badge(row: dict) -> str:
    lenos_total = token_total(row, "lenos")
    codex_total = token_total(row, "codex")
    if lenos_total <= 0 or codex_total <= 0:
        return "<div class=\"ratio neutral\"><b>n/a</b><span>Lenos/Codex</span></div>"

    ratio = lenos_total / codex_total
    if ratio < 1:
        css_class = "good"
        detail = f"{(1 - ratio) * 100:.1f}% less"
    elif ratio > 1:
        css_class = "bad"
        detail = f"{(ratio - 1) * 100:.1f}% more"
    else:
        css_class = "neutral"
        detail = "same"
    return (
        f"<div class=\"ratio {css_class}\">"
        f"<b>{ratio:.2f}x</b><span>{detail}</span></div>"
    )


def render_summary_html(summary: dict) -> str:
    shared_count = len(summary["shared_tasks"])
    lenos_passes = summary["lenos"]["passes"]
    codex_passes = summary["codex_cli"]["passes"]
    paired_count = summary["paired_success_count"]
    lenos_pass_width = lenos_passes / max(shared_count, 1) * 100
    codex_pass_width = codex_passes / max(shared_count, 1) * 100
    lenos_cost_width = summary["estimated_cost"]["lenos_share"] * 100
    codex_cost_width = summary["estimated_cost"]["codex_cli_share"] * 100
    lenos_cost = summary["estimated_cost"]["lenos"]
    codex_cost = summary["estimated_cost"]["codex_cli"]
    cost_ratio = summary["estimated_cost"]["ratio"]

    task_rows = []
    token_chart_rows = []
    for row in summary["task_rows"]:
        lenos_state = "pass" if row["lenos_pass"] else "fail"
        codex_state = "pass" if row["codex_pass"] else "fail"
        max_task_total = max(token_total(row, "lenos"), token_total(row, "codex"), 1)
        lenos_row_cost = estimated_gpt55_cost(row, "lenos")
        codex_row_cost = estimated_gpt55_cost(row, "codex")
        row_cost_ratio = (
            lenos_row_cost / codex_row_cost if lenos_row_cost and codex_row_cost else None
        )
        task_rows.append(
            "<tr>"
            f"<td>{row['task']}</td>"
            f"<td><span class=\"state {lenos_state}\">{lenos_state}</span></td>"
            f"<td>{fmt_number(row.get('lenos_agent_seconds'))}</td>"
            f"<td>{fmt_money(lenos_row_cost)}</td>"
            f"<td>{fmt_number(row.get('lenos_input_tokens'))}</td>"
            f"<td>{fmt_number(row.get('lenos_cache_tokens'))}</td>"
            f"<td>{fmt_number(row.get('lenos_cache_miss_tokens'))}</td>"
            f"<td>{fmt_number(row.get('lenos_output_tokens'))}</td>"
            f"<td><span class=\"state {codex_state}\">{codex_state}</span></td>"
            f"<td>{fmt_number(row.get('codex_agent_seconds'))}</td>"
            f"<td>{fmt_money(codex_row_cost)}</td>"
            f"<td>{fmt_number(row.get('codex_input_tokens'))}</td>"
            f"<td>{fmt_number(row.get('codex_cache_tokens'))}</td>"
            f"<td>{fmt_number(row.get('codex_cache_miss_tokens'))}</td>"
            f"<td>{fmt_number(row.get('codex_output_tokens'))}</td>"
            f"<td>{fmt_number(row_cost_ratio)}</td>"
            "</tr>"
        )
        token_chart_rows.append(
            "<div class=\"task-token-row\">"
            f"<div class=\"task-name\">{row['task']}</div>"
            f"{token_ratio_badge(row)}"
            "<div class=\"token-bars\">"
            f"{stacked_token_bar(row, 'lenos', 'Lenos', max_task_total)}"
            f"{stacked_token_bar(row, 'codex', 'Codex', max_task_total)}"
            "</div>"
            "</div>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lenos vs Codex Summary</title>
  <style>
    :root {{
      --ink: #15130f;
      --muted: #6b6255;
      --paper: #f4efe6;
      --panel: #fffdf8;
      --line: #d9cdbb;
      --lenos: #0f766e;
      --codex: #9a3412;
      --hit: #2a9d8f;
      --miss: #e76f51;
      --out: #264653;
      --fail: #b42318;
      --good: #147a45;
      --bad: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 34px 24px 48px;
    }}
    .topline {{
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 22px;
      align-items: stretch;
    }}
    h1 {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 44px;
      line-height: 1;
      letter-spacing: 0;
    }}
    .lede {{
      margin-top: 18px;
      max-width: 760px;
      color: #302a22;
      font-size: 18px;
      line-height: 1.55;
    }}
    .stamp {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 14px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: 0 18px 48px rgba(56, 42, 24, .08);
    }}
    .scorecard {{
      padding: 24px;
      display: grid;
      gap: 18px;
    }}
    .score {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 14px;
    }}
    .score:last-child {{ border-bottom: 0; padding-bottom: 0; }}
    .score b {{ font-size: 30px; }}
    .score span {{ color: var(--muted); font-size: 13px; }}
    .grid {{
      margin-top: 24px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}
    .chart {{
      padding: 20px;
    }}
    h2 {{
      margin: 0 0 16px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 92px 1fr 90px;
      align-items: center;
      gap: 12px;
      margin: 12px 0;
      font-size: 13px;
    }}
    .track {{
      height: 14px;
      background: #eadfce;
      border: 1px solid var(--line);
      overflow: hidden;
    }}
    .fill {{
      height: 100%;
      min-width: 2px;
    }}
    .fill.lenos {{ background: var(--lenos); }}
    .fill.codex {{ background: var(--codex); }}
    .stack {{
      display: flex;
      height: 100%;
      min-width: 2px;
    }}
    .seg {{ display: block; height: 100%; }}
    .seg.hit {{ background: var(--hit); }}
    .seg.miss {{ background: var(--miss); }}
    .seg.out {{ background: var(--out); }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 16px;
      color: var(--muted);
      font-size: 12px;
      margin: -4px 0 12px;
    }}
    .legend span {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .legend i {{
      display: inline-block;
      width: 18px;
      height: 8px;
      border: 1px solid rgba(0, 0, 0, .12);
    }}
    .legend .hit {{ background: var(--hit); }}
    .legend .miss {{ background: var(--miss); }}
    .legend .out {{ background: var(--out); }}
    .table-card {{
      margin-top: 18px;
      overflow: auto;
    }}
    .wide-chart {{
      margin-top: 18px;
      padding: 20px;
    }}
    .task-token-row {{
      display: grid;
      grid-template-columns: minmax(210px, .38fr) 86px 1fr;
      gap: 14px;
      align-items: center;
      padding: 11px 0;
      border-bottom: 1px solid var(--line);
    }}
    .task-token-row:last-child {{ border-bottom: 0; }}
    .task-name {{
      font-size: 13px;
      color: #2d271f;
      overflow-wrap: anywhere;
    }}
    .token-bars {{
      display: grid;
      gap: 6px;
    }}
    .ratio {{
      display: grid;
      justify-items: end;
      gap: 2px;
      font-variant-numeric: tabular-nums;
    }}
    .ratio b {{
      font-size: 18px;
      line-height: 1;
    }}
    .ratio span {{
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }}
    .ratio.good b {{ color: var(--good); }}
    .ratio.bad b {{ color: var(--bad); }}
    .ratio.neutral b {{ color: var(--muted); }}
    .mini-bar {{
      display: grid;
      grid-template-columns: 52px 1fr 88px;
      align-items: center;
      gap: 10px;
      font-size: 12px;
    }}
    .mini-bar b {{
      text-align: right;
      font-weight: 600;
    }}
    .mini-bar.missing {{
      color: var(--muted);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      font-size: 13px;
    }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
    }}
    th {{
      background: #ebe1d1;
      color: #3a3329;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .06em;
    }}
    .state {{
      display: inline-block;
      min-width: 48px;
      padding: 2px 8px;
      border: 1px solid currentColor;
      border-radius: 999px;
      text-align: center;
      font-size: 12px;
    }}
    .state.pass {{ color: var(--lenos); }}
    .state.fail {{ color: var(--fail); }}
    a {{ color: var(--codex); }}
    @media (max-width: 780px) {{
      main {{ padding: 22px 14px 36px; }}
      .topline, .grid {{ grid-template-columns: 1fr; }}
      .task-token-row {{ grid-template-columns: 1fr; }}
      .ratio {{ justify-items: start; }}
      .mini-bar {{ grid-template-columns: 52px 1fr 78px; }}
      h1 {{ font-size: 34px; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="topline">
      <div>
        <div class="stamp">Agon live summary / same {summary['model']} / {summary['thinking']} thinking</div>
        <h1>Lenos vs Codex CLI</h1>
        <p class="lede">{summary['sentence']}</p>
        <p><a href="/agon_bench/results/tb2-scoreboard.html">Open full scoreboard</a> · <a href="/summary.json">JSON</a> · <a href="/summary.txt">plain text</a></p>
      </div>
      <aside class="panel scorecard">
        <div class="score"><span>Shared tasks</span><b>{shared_count}</b></div>
        <div class="score"><span>Lenos successful</span><b>{lenos_passes}</b></div>
        <div class="score"><span>Codex successful</span><b>{codex_passes}</b></div>
        <div class="score"><span>Both solved</span><b>{paired_count}</b></div>
      </aside>
    </section>

    <section class="grid">
      <div class="panel chart">
        <h2>Successful Run Coverage</h2>
        <div class="bar-row"><span>Lenos</span><div class="track"><div class="fill lenos" style="width:{lenos_pass_width:.3f}%"></div></div><b>{lenos_passes}/{shared_count}</b></div>
        <div class="bar-row"><span>Codex CLI</span><div class="track"><div class="fill codex" style="width:{codex_pass_width:.3f}%"></div></div><b>{codex_passes}/{shared_count}</b></div>
      </div>
      <div class="panel chart">
        <h2>Estimated Dollar Cost</h2>
        <div class="bar-row"><span>Lenos</span><div class="track"><div class="fill lenos" style="width:{lenos_cost_width:.3f}%"></div></div><b>${lenos_cost:.2f}</b></div>
        <div class="bar-row"><span>Codex CLI</span><div class="track"><div class="fill codex" style="width:{codex_cost_width:.3f}%"></div></div><b>${codex_cost:.2f}</b></div>
        <div class="bar-row"><span>Ratio</span><div class="track"><div class="fill lenos" style="width:{min(cost_ratio, 1) * 100:.3f}%"></div></div><b>{cost_ratio:.2f}x</b></div>
      </div>
    </section>

    <section class="panel wide-chart">
      <h2>Token Mix By Task</h2>
      <div class="legend">
        <span><i class="hit"></i>cache hit input</span>
        <span><i class="miss"></i>cache miss input</span>
        <span><i class="out"></i>output</span>
        <span>Each task uses its own scale; right labels show absolute total input + output tokens.</span>
      </div>
      {''.join(token_chart_rows)}
    </section>

    <section class="panel table-card">
      <table>
        <thead>
          <tr>
            <th>task</th>
            <th>Lenos</th>
            <th>Lenos s</th>
            <th>Lenos $</th>
            <th>Lenos input</th>
            <th>Lenos hit</th>
            <th>Lenos miss</th>
            <th>Lenos output</th>
            <th>Codex</th>
            <th>Codex s</th>
            <th>Codex $</th>
            <th>Codex input</th>
            <th>Codex hit</th>
            <th>Codex miss</th>
            <th>Codex output</th>
            <th>$/ratio</th>
          </tr>
        </thead>
        <tbody>{''.join(task_rows)}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


class ScoreboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", HTML_ROUTE)
            self.end_headers()
            return
        if path == HTML_ROUTE:
            self.respond_html()
            return
        if path == JSON_ROUTE:
            self.respond_json()
            return
        if path == SUMMARY_ROUTE:
            self.respond_summary()
            return
        if path == SUMMARY_TEXT_ROUTE:
            self.respond_summary_text()
            return
        if path == SUMMARY_JSON_ROUTE:
            self.respond_summary_json()
            return
        super().do_GET()

    def respond_html(self) -> None:
        body = update_scoreboard.render_html(live_payload()).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def respond_summary(self) -> None:
        body = render_summary_html(comparison_summary(live_payload())).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def respond_summary_text(self) -> None:
        body = (comparison_summary(live_payload())["sentence"] + "\n").encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def respond_summary_json(self) -> None:
        body = (
            json.dumps(comparison_summary(live_payload()), indent=2, ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def respond_json(self) -> None:
        body = (
            json.dumps(live_payload(), indent=2, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class ScoreboardServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main() -> None:
    server = ScoreboardServer(("127.0.0.1", 8766), ScoreboardHandler)
    print("serving live scoreboard at http://127.0.0.1:8766/")
    server.serve_forever()


if __name__ == "__main__":
    main()
