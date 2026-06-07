#!/usr/bin/env python3
"""Build a local TB2 smoke scoreboard from Harbor job directories."""

from __future__ import annotations

import json
import tomllib
from datetime import datetime, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JOBS_DIR = ROOT / "jobs"
CACHE_TASKS_DIR = Path.home() / ".cache" / "harbor" / "tasks"
RESULTS_DIR = ROOT / "agon_bench" / "results"
JSON_PATH = RESULTS_DIR / "tb2-scoreboard.json"
HTML_PATH = RESULTS_DIR / "tb2-scoreboard.html"
NOTES_PATH = RESULTS_DIR / "tb2-scoreboard-notes.json"
DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2, "unknown": 3}
STATUS_RANK = {
    "pass": 0,
    "near_pass_95": 1,
    "pass_after_agent_timeout": 1,
    "pass_with_exception": 2,
    "failed": 3,
    "not_run": 4,
}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_text(path: Path, limit: int = 12000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:]


def load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def normalize_task_name(task_name: str | None) -> str:
    if not task_name:
        return ""
    return task_name.split("/", 1)[-1]


def task_metadata_index() -> dict[str, dict]:
    index = {}
    if not CACHE_TASKS_DIR.exists():
        return index

    for path in CACHE_TASKS_DIR.rglob("task.toml"):
        data = load_toml(path)
        if not data:
            continue
        metadata = as_dict(data.get("metadata"))
        task_name = path.parent.name
        if len(task_name) == 64 and path.parent.parent.name != "terminal-bench":
            task_name = path.parent.parent.name
        entry = {
            "difficulty": metadata.get("difficulty") or "unknown",
            "category": metadata.get("category"),
            "tags": metadata.get("tags") or [],
            "expert_time_estimate_min": metadata.get("expert_time_estimate_min"),
            "junior_time_estimate_min": metadata.get("junior_time_estimate_min"),
        }
        index[task_name] = entry
        index[f"terminal-bench/{task_name}"] = entry
    return index


def load_notes() -> dict[tuple[str, str], dict]:
    notes = load_json(NOTES_PATH)
    index = {}
    for item in notes.get("entries", []):
        job = item.get("job")
        trial = item.get("trial")
        if job and trial:
            index[(job, trial)] = item
    return index


def seconds_between(start: str | None, finish: str | None) -> float | None:
    if not start or not finish:
        return None
    try:
        started = datetime.fromisoformat(start.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finish.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round((finished - started).total_seconds(), 1)


def as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def add_cache_metrics(entry: dict) -> None:
    input_tokens = entry.get("input_tokens")
    cache_tokens = entry.get("cache_tokens")
    if not isinstance(input_tokens, int) or input_tokens <= 0:
        entry["cache_miss_tokens"] = None
        entry["cache_hit_rate"] = None
        return
    if not isinstance(cache_tokens, int):
        entry["cache_miss_tokens"] = None
        entry["cache_hit_rate"] = None
        return

    cache_tokens = max(0, min(cache_tokens, input_tokens))
    entry["cache_miss_tokens"] = input_tokens - cache_tokens
    entry["cache_hit_rate"] = cache_tokens / input_tokens


def reward_from(result: dict) -> object:
    return as_dict(as_dict(result.get("verifier_result")).get("rewards")).get("reward")


def classify(result: dict, transcript: str, verifier: str) -> str:
    reward = reward_from(result)
    exception = as_dict(result.get("exception_info")).get("exception_type")
    combined = f"{transcript}\n{verifier}".lower()

    if reward == 1.0:
        if exception == "AgentTimeoutError":
            return "pass_after_agent_timeout"
        if exception:
            return "pass_with_exception"
        return "pass"
    if exception == "AgentTimeoutError":
        return "agent_timeout"
    if exception:
        if "message content is shorter than read bytes" in combined:
            return "lenos_runtime_error"
        return "agent_exception"
    if "i can’t help" in combined or "i can't help" in combined:
        return "model_refusal"
    if "file /app/out.html does not exist" in combined or "filenotfounderror" in combined:
        return "missing_artifact"
    return "failed_tests"


def summarize_failure(classification: str, transcript: str, verifier: str) -> str:
    if classification == "pass":
        return "passed verifier"
    if classification == "pass_after_agent_timeout":
        return "artifact passed verifier, but agent hit the task timeout before clean exit"
    if classification == "pass_with_exception":
        return "artifact passed verifier, but Harbor recorded an agent exception"
    if classification == "model_refusal":
        return "model refused the task before writing the expected artifact"
    if classification == "missing_artifact":
        return "verifier failed because an expected output file was not created"
    if classification == "agent_timeout":
        return "agent hit the task agent timeout"
    if classification == "lenos_runtime_error":
        return "Lenos exited with a runtime/protocol error"

    for line in reversed(verifier.splitlines()):
        line = line.strip()
        if line.startswith("E       ") or "AssertionError" in line:
            return line[:240]
    for line in reversed(transcript.splitlines()):
        line = line.strip()
        if line:
            return line[:240]
    return classification.replace("_", " ")


def build_entry(
    job_dir: Path, trial_dir: Path, metadata: dict[str, dict], notes: dict
) -> dict | None:
    result_path = trial_dir / "result.json"
    result = load_json(result_path)
    if not result:
        return None

    config = load_json(trial_dir / "config.json")
    job_config = load_json(job_dir / "config.json")
    transcript = read_text(trial_dir / "agent" / "lenos.txt")
    verifier = read_text(trial_dir / "verifier" / "test-stdout.txt")

    agent = config.get("agent") or (job_config.get("agents") or [{}])[0]
    task = config.get("task") or (job_config.get("tasks") or [{}])[0]
    task_name = result.get("task_name") or task.get("name")
    task_meta = metadata.get(task_name) or metadata.get(normalize_task_name(task_name)) or {}
    agent_result = as_dict(result.get("agent_result"))
    usage = as_dict(as_dict(agent_result.get("metadata")).get("lenos_usage"))
    execution = as_dict(result.get("agent_execution"))
    classification = classify(result, transcript, verifier)
    note = notes.get((job_dir.name, trial_dir.name), {})
    manual_status = note.get("status")
    manual_note = note.get("note")

    entry = {
        "job": job_dir.name,
        "trial": trial_dir.name,
        "task": task_name,
        "task_key": normalize_task_name(task_name),
        "difficulty": task_meta.get("difficulty") or "unknown",
        "category": task_meta.get("category"),
        "model": agent.get("model_name"),
        "agent": agent.get("import_path") or agent.get("name"),
        "reward": reward_from(result),
        "exception": as_dict(result.get("exception_info")).get("exception_type"),
        "classification": classification,
        "display_status": manual_status or classification,
        "summary": summarize_failure(classification, transcript, verifier),
        "manual_note": manual_note,
        "agent_seconds": seconds_between(
            execution.get("started_at"), execution.get("finished_at")
        ),
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "reasoning_tokens": usage.get("reasoning_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cost_usd": agent_result.get("cost_usd"),
        "provider": usage.get("provider_id"),
        "reasoning_effort": usage.get("reasoning_effort"),
        "job_path": str(job_dir.relative_to(ROOT)),
    }
    add_cache_metrics(entry)
    return entry


def collect_entries() -> list[dict]:
    entries = []
    if not JOBS_DIR.exists():
        return entries
    metadata = task_metadata_index()
    notes = load_notes()

    for job_dir in sorted(JOBS_DIR.iterdir()):
        if not job_dir.is_dir():
            continue
        for trial_dir in sorted(job_dir.iterdir()):
            if not trial_dir.is_dir():
                continue
            entry = build_entry(job_dir, trial_dir, metadata, notes)
            if entry is not None:
                entries.append(entry)
    return sorted(entries, key=lambda item: (item["job"], item["trial"]))


def fmt_number(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def fmt_percent(value: object) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return f"{value * 100:.1f}%"


def status_class(status: str) -> str:
    if status == "pass":
        return "pass"
    if status.startswith("pass_") or status.startswith("near_pass"):
        return "warn"
    if status == "not_run":
        return "neutral"
    return "fail"


def task_status(entries: list[dict]) -> str:
    if any(e.get("classification") == "pass" for e in entries):
        return "pass"
    if any(e.get("display_status") == "near_pass_95" for e in entries):
        return "near_pass_95"
    if any(e.get("classification") == "pass_after_agent_timeout" for e in entries):
        return "pass_after_agent_timeout"
    if any(e.get("classification") == "pass_with_exception" for e in entries):
        return "pass_with_exception"
    if entries:
        return "failed"
    return "not_run"


def build_task_dashboard(entries: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for entry in entries:
        task_key = entry.get("task_key") or normalize_task_name(entry.get("task")) or "unknown"
        grouped.setdefault(task_key, []).append(entry)

    task_rows = []
    for task_key, task_entries in grouped.items():
        completed = [e for e in task_entries if e.get("reward") is not None or e.get("exception")]
        clean_passes = [e for e in completed if e.get("classification") == "pass"]
        timeout_passes = [
            e for e in completed if e.get("classification") == "pass_after_agent_timeout"
        ]
        models = sorted({e.get("model") or "" for e in task_entries if e.get("model")})
        latest = max(task_entries, key=lambda e: e.get("job") or "")
        noted = next((e for e in reversed(task_entries) if e.get("manual_note")), latest)
        display_task = next(
            (
                e.get("task")
                for e in reversed(task_entries)
                if str(e.get("task") or "").startswith("terminal-bench/")
            ),
            latest.get("task") or task_key,
        )
        status = task_status(completed)
        task_rows.append(
            {
                "task": display_task,
                "task_key": task_key,
                "difficulty": latest.get("difficulty") or "unknown",
                "category": latest.get("category") or "",
                "status": status,
                "models": models,
                "trials": len(completed),
                "clean_passes": len(clean_passes),
                "timeout_passes": len(timeout_passes),
                "failures": len(completed) - len(clean_passes) - len(timeout_passes),
                "best_reward": max(
                    (e.get("reward") for e in completed if e.get("reward") is not None),
                    default=None,
                ),
                "latest_job": latest.get("job"),
                "latest_summary": noted.get("manual_note") or latest.get("summary"),
            }
        )

    return sorted(
        task_rows,
        key=lambda item: (
            DIFFICULTY_RANK.get(item["difficulty"], DIFFICULTY_RANK["unknown"]),
            STATUS_RANK.get(item["status"], STATUS_RANK["not_run"]),
            item["task_key"],
        ),
    )


def render_html(payload: dict) -> str:
    entries = payload["entries"]
    completed = [e for e in entries if e["reward"] is not None or e["exception"]]
    passed = sum(1 for e in completed if e["reward"] == 1.0)
    failed = len(completed) - passed
    task_dashboard = build_task_dashboard(entries)
    tasks = len(task_dashboard)
    models = len({e["model"] for e in completed})

    task_rows = []
    for task in task_dashboard:
        status = task["status"]
        task_rows.append(
            "<tr class=\"task-row\">"
            f"<td>{escape(task['task'])}</td>"
            f"<td>{escape(task['difficulty'])}</td>"
            f"<td>{escape(task['category'])}</td>"
            f"<td><span class=\"pill {status_class(status)}\">{escape(status)}</span></td>"
            f"<td>{fmt_number(task.get('best_reward'))}</td>"
            f"<td>{fmt_number(task['trials'])}</td>"
            f"<td>{fmt_number(task['clean_passes'])}</td>"
            f"<td>{fmt_number(task['timeout_passes'])}</td>"
            f"<td>{escape(', '.join(task['models']))}</td>"
            f"<td><a href=\"../../jobs/{escape(task['latest_job'] or '')}/result.json\">{escape(task['latest_job'] or '')}</a></td>"
            f"<td>{escape(task.get('latest_summary') or '')}</td>"
            "</tr>"
        )

    rows = []
    for entry in reversed(entries):
        status = entry.get("display_status") or entry["classification"]
        summary = entry.get("manual_note") or entry.get("summary") or ""
        rows.append(
            "<tr class=\"run-row\">"
            f"<td><a href=\"../../{escape(entry['job_path'])}/result.json\">{escape(entry['job'])}</a></td>"
            f"<td>{escape(entry.get('task') or '')}</td>"
            f"<td>{escape(entry.get('model') or '')}</td>"
            f"<td><span class=\"pill {status_class(status)}\">{escape(status)}</span></td>"
            f"<td>{fmt_number(entry.get('reward'))}</td>"
            f"<td>{fmt_number(entry.get('agent_seconds'))}</td>"
            f"<td>{fmt_number(entry.get('input_tokens'))}</td>"
            f"<td>{fmt_number(entry.get('cache_tokens'))}</td>"
            f"<td>{fmt_number(entry.get('cache_miss_tokens'))}</td>"
            f"<td>{fmt_percent(entry.get('cache_hit_rate'))}</td>"
            f"<td>{fmt_number(entry.get('output_tokens'))}</td>"
            f"<td>{fmt_number(entry.get('reasoning_tokens'))}</td>"
            f"<td>{fmt_number(entry.get('cost_usd'))}</td>"
            f"<td>{escape(summary)}</td>"
            "</tr>"
        )

    generated_at = escape(payload["generated_at"])
    data_json = escape(json.dumps(payload, ensure_ascii=False), quote=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agon TB2 Local Scoreboard</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #171717;
      --muted: #646464;
      --line: #d8d8d8;
      --paper: #f7f4ee;
      --panel: #ffffff;
      --pass: #0f766e;
      --fail: #b42318;
      --accent: #9a5b13;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 14px;
    }}
    header {{
      padding: 28px 32px 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .sub {{ color: var(--muted); max-width: 980px; line-height: 1.5; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 1px;
      background: var(--line);
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }}
    .stat {{
      background: var(--panel);
      padding: 16px 20px;
    }}
    .stat b {{ display: block; font-size: 22px; }}
    .stat span {{ color: var(--muted); font-size: 12px; }}
    main {{ padding: 24px 32px 40px; }}
    h2 {{
      margin: 0 0 12px;
      font-size: 16px;
      letter-spacing: 0;
    }}
    .section {{
      margin-bottom: 30px;
    }}
    .toolbar {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }}
    input {{
      min-width: 320px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      padding: 9px 10px;
      font: inherit;
    }}
    .hint {{ color: var(--muted); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
    }}
    th, td {{
      padding: 10px 9px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #eee8dd;
      z-index: 1;
      font-size: 12px;
      color: #3f3a34;
    }}
    td:last-child {{ max-width: 520px; line-height: 1.45; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .pill {{
      display: inline-block;
      border: 1px solid currentColor;
      padding: 2px 7px;
      border-radius: 999px;
      font-size: 12px;
      white-space: nowrap;
    }}
    .pass {{ color: var(--pass); }}
    .warn {{ color: #a16207; }}
    .fail {{ color: var(--fail); }}
    .neutral {{ color: var(--muted); }}
    .dashboard th {{
      background: #e8eadf;
    }}
    .runs {{
      margin-top: 8px;
    }}
    @media (max-width: 900px) {{
      header, main {{ padding-left: 16px; padding-right: 16px; }}
      .stats {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
      input {{ min-width: 100%; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
      td:last-child {{ white-space: normal; min-width: 360px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Agon TB2 Local Scoreboard</h1>
    <div class="sub">Local run ledger for Lenos on terminal-bench@2.0. This is for smoke coverage and failure triage, not an official leaderboard submission. Generated at {generated_at}.</div>
  </header>
  <section class="stats">
    <div class="stat"><b>{len(completed)}</b><span>completed trials</span></div>
    <div class="stat"><b>{passed}</b><span>passed</span></div>
    <div class="stat"><b>{failed}</b><span>failed or errored</span></div>
    <div class="stat"><b>{tasks}</b><span>tasks touched</span></div>
    <div class="stat"><b>{models}</b><span>models touched</span></div>
  </section>
  <main>
    <section class="section">
      <h2>Task Dashboard</h2>
      <div class="toolbar">
        <input id="filter" type="search" placeholder="filter by task, model, status, summary">
        <span class="hint">Sorted by cached task difficulty, then pass state</span>
      </div>
      <table id="tasks" class="dashboard">
        <thead>
          <tr>
            <th>task</th>
            <th>difficulty</th>
            <th>category</th>
            <th>best status</th>
            <th>best reward</th>
            <th>trials</th>
            <th>clean pass</th>
            <th>timeout pass</th>
            <th>models</th>
            <th>latest job</th>
            <th>latest note</th>
          </tr>
        </thead>
        <tbody>
          {''.join(task_rows)}
        </tbody>
      </table>
    </section>

    <section class="section runs">
      <h2>Run Log</h2>
      <div class="toolbar">
        <span class="hint">Raw trial rows from jobs/* result files</span>
      </div>
    <table id="runs">
      <thead>
        <tr>
          <th>job</th>
          <th>task</th>
          <th>model</th>
          <th>status</th>
          <th>reward</th>
          <th>agent s</th>
          <th>input</th>
          <th>cache hit</th>
          <th>cache miss</th>
          <th>cache %</th>
          <th>output</th>
          <th>reason</th>
          <th>cost</th>
          <th>summary</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    </section>
  </main>
  <script type="application/json" id="scoreboard-data">{data_json}</script>
  <script>
    const filter = document.querySelector('#filter');
    const rows = Array.from(document.querySelectorAll('#tasks tbody tr, #runs tbody tr'));
    filter.addEventListener('input', () => {{
      const q = filter.value.trim().toLowerCase();
      for (const row of rows) {{
        row.hidden = q && !row.textContent.toLowerCase().includes(q);
      }}
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": collect_entries(),
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    HTML_PATH.write_text(render_html(payload), encoding="utf-8")
    print(f"wrote {JSON_PATH.relative_to(ROOT)}")
    print(f"wrote {HTML_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
