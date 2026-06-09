#!/usr/bin/env python3
"""Build a local Terminal-Bench smoke scoreboard from Harbor job directories."""

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
RUNS_HTML_PATH = RESULTS_DIR / "tb2-runs.html"
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
TB2_TOTAL_TASKS = 89
PROBLEM_STATUSES = {"benchmark_leakage"}
BENCHMARK_LABELS = {
    "tb2.0": "Terminal-Bench 2.0",
    "tb2.1": "Terminal-Bench 2.1",
    "unknown": "Unknown benchmark",
}
DEFAULT_BENCHMARK = "all"


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


def is_tb2_task(task_name: str | None) -> bool:
    if not task_name:
        return False
    return task_name.startswith("terminal-bench/") or not task_name.startswith("local/")


def benchmark_label(benchmark: str | None) -> str:
    if not benchmark or benchmark == "all":
        return "All Terminal-Bench runs"
    return BENCHMARK_LABELS.get(benchmark, benchmark)


def benchmark_query_suffix(benchmark: str | None) -> str:
    if not benchmark or benchmark == "all":
        return ""
    return f"?benchmark={benchmark}"


def detect_benchmark(job_dir: Path, job_config: dict, trial_config: dict) -> str:
    job_name = str(job_config.get("job_name") or job_dir.name).lower()
    datasets = job_config.get("datasets") or []
    dataset_text = json.dumps(datasets, sort_keys=True).lower()
    tasks = job_config.get("tasks") or []
    trial_task = trial_config.get("task")
    task_text = json.dumps([*tasks, trial_task], sort_keys=True).lower()
    combined = f"{job_name}\n{dataset_text}\n{task_text}"

    if (
        "terminal-bench-2-1" in combined
        or "terminal-bench/terminal-bench-2-1" in combined
        or "tb2.1" in combined
        or "tb21" in combined
    ):
        return "tb2.1"
    if "terminal-bench@2.0" in combined or "tb2.0" in combined or "tb20" in combined:
        return "tb2.0"
    if any(is_tb2_task((task or {}).get("name")) for task in tasks if isinstance(task, dict)):
        return "tb2.0"
    if isinstance(trial_task, dict) and is_tb2_task(trial_task.get("name")):
        return "tb2.0"
    return "unknown"


def filter_entries(entries: list[dict], benchmark: str | None) -> list[dict]:
    if not benchmark or benchmark == "all":
        return entries
    return [entry for entry in entries if entry.get("benchmark") == benchmark]


def filter_payload(payload: dict, benchmark: str | None) -> dict:
    selected = benchmark or DEFAULT_BENCHMARK
    return {
        **payload,
        "benchmark": selected,
        "benchmark_label": benchmark_label(selected),
        "entries": filter_entries(payload.get("entries", []), selected),
    }


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


def index_notes(notes: dict) -> dict[tuple[str, str], dict]:
    index = {}
    for item in notes.get("entries", []):
        job = item.get("job")
        trial = item.get("trial")
        if job and trial:
            index[(job, trial)] = item
    for item in notes.get("tasks", []):
        task = item.get("task") or item.get("task_key")
        task_key = normalize_task_name(task)
        if task_key:
            index[("task", task_key)] = item
    return index


def load_notes() -> dict[tuple[str, str], dict]:
    return index_notes(load_json(NOTES_PATH))


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


def harness_label(agent: dict) -> str:
    raw = agent.get("import_path") or agent.get("name") or ""
    if raw == "codex":
        return "Codex CLI"
    if raw == "agon_bench.adapters.lenos:LenosAgent" or raw == "lenos":
        return "Lenos"
    return raw or "unknown"


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
        if "request transport error" in combined or "backend-api/codex/responses" in combined:
            return "provider_transport_error"
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
    if classification == "provider_transport_error":
        for line in reversed(transcript.splitlines()):
            line = line.strip()
            if "request transport error" in line or "backend-api/codex/responses" in line:
                return line[:240]
        return "provider transport error before the agent could work"

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
    benchmark = detect_benchmark(job_dir, job_config, config)
    if benchmark == "unknown" and is_tb2_task(task_name):
        benchmark = "tb2.0"
    agent_result = as_dict(result.get("agent_result"))
    usage = as_dict(as_dict(agent_result.get("metadata")).get("lenos_usage"))
    execution = as_dict(result.get("agent_execution"))
    classification = classify(result, transcript, verifier)
    note = notes.get((job_dir.name, trial_dir.name)) or notes.get(
        ("task", normalize_task_name(task_name)), {}
    )
    manual_status = note.get("status")
    manual_note = note.get("note")

    entry = {
        "job": job_dir.name,
        "trial": trial_dir.name,
        "task": task_name,
        "task_key": normalize_task_name(task_name),
        "benchmark": benchmark,
        "benchmark_label": benchmark_label(benchmark),
        "difficulty": task_meta.get("difficulty") or "unknown",
        "category": task_meta.get("category"),
        "model": agent.get("model_name"),
        "agent": agent.get("import_path") or agent.get("name"),
        "harness": harness_label(agent),
        "reward": reward_from(result),
        "exception": as_dict(result.get("exception_info")).get("exception_type"),
        "classification": classification,
        "display_status": manual_status or classification,
        "note_status": manual_status,
        "comparison_excluded": manual_status in PROBLEM_STATUSES,
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


def is_problem_entry(entry: dict) -> bool:
    return (entry.get("display_status") or entry.get("note_status")) in PROBLEM_STATUSES


def is_effective_pass(entry: dict) -> bool:
    return entry.get("classification") == "pass" and not is_problem_entry(entry)


def task_status(entries: list[dict]) -> str:
    if any(is_effective_pass(e) for e in entries):
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
        clean_passes = [e for e in completed if is_effective_pass(e)]
        timeout_passes = [
            e for e in completed if e.get("classification") == "pass_after_agent_timeout"
        ]
        models = sorted({e.get("model") or "" for e in task_entries if e.get("model")})
        harnesses = sorted({e.get("harness") or "" for e in task_entries if e.get("harness")})
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
        sorted_entries = sorted(
            task_entries,
            key=lambda entry: (entry.get("job") or "", entry.get("trial") or ""),
            reverse=True,
        )
        task_rows.append(
            {
                "task": display_task,
                "task_key": task_key,
                "difficulty": latest.get("difficulty") or "unknown",
                "category": latest.get("category") or "",
                "status": status,
                "models": models,
                "harnesses": harnesses,
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
                "entries": sorted_entries,
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


def render_task_detail(entries: list[dict]) -> str:
    rows = []
    for entry in entries:
        status = entry.get("display_status") or entry["classification"]
        summary = entry.get("manual_note") or entry.get("summary") or ""
        rows.append(
            "<tr>"
            f"<td><a href=\"../../{escape(entry['job_path'])}/result.json\">{escape(entry['job'])}</a></td>"
            f"<td>{escape(entry.get('harness') or '')}</td>"
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
    return (
        "<table class=\"detail-table\">"
        "<thead><tr>"
        "<th>job</th><th>harness</th><th>model</th><th>status</th><th>reward</th>"
        "<th>agent s</th><th>input</th><th>cache hit</th><th>cache miss</th>"
        "<th>cache %</th><th>output</th><th>reason</th><th>cost</th><th>summary</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def render_run_rows(entries: list[dict]) -> str:
    rows = []
    for entry in reversed(entries):
        status = entry.get("display_status") or entry["classification"]
        summary = entry.get("manual_note") or entry.get("summary") or ""
        rows.append(
            "<tr class=\"run-row\">"
            f"<td><a href=\"../../{escape(entry['job_path'])}/result.json\">{escape(entry['job'])}</a></td>"
            f"<td>{escape(entry.get('task') or '')}</td>"
            f"<td>{escape(entry.get('harness') or '')}</td>"
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
    return "".join(rows)


def render_html(payload: dict) -> str:
    payload = filter_payload(payload, payload.get("benchmark"))
    entries = payload["entries"]
    completed = [e for e in entries if e["reward"] is not None or e["exception"]]
    passed = sum(1 for e in completed if is_effective_pass(e))
    failed = len(completed) - passed
    task_dashboard = build_task_dashboard(entries)
    tb2_task_dashboard = [task for task in task_dashboard if is_tb2_task(task.get("task"))]
    tasks = len(task_dashboard)
    tb2_tasks_touched = min(len(tb2_task_dashboard), TB2_TOTAL_TASKS)
    tb2_clean_passed = sum(1 for task in tb2_task_dashboard if task["status"] == "pass")
    tb2_near_passed = sum(
        1
        for task in tb2_task_dashboard
        if task["status"] in {"near_pass_95", "pass_after_agent_timeout", "pass_with_exception"}
    )
    tb2_failed = sum(1 for task in tb2_task_dashboard if task["status"] == "failed")
    tb2_not_run = max(0, TB2_TOTAL_TASKS - tb2_tasks_touched)
    tb2_done = tb2_clean_passed + tb2_near_passed
    pie_clean = tb2_clean_passed / TB2_TOTAL_TASKS * 100
    pie_near = (tb2_clean_passed + tb2_near_passed) / TB2_TOTAL_TASKS * 100
    pie_failed = (
        tb2_clean_passed + tb2_near_passed + tb2_failed
    ) / TB2_TOTAL_TASKS * 100
    models = len({e["model"] for e in completed})
    harnesses = len({e.get("harness") for e in completed if e.get("harness")})

    task_rows = []
    for index, task in enumerate(task_dashboard):
        status = task["status"]
        task_id = f"task-detail-{index}"
        task_rows.append(
            f"<tr class=\"task-row\" data-detail=\"{task_id}\" tabindex=\"0\">"
            f"<td><span class=\"toggle\" aria-hidden=\"true\">&gt;</span>{escape(task['task'])}</td>"
            f"<td>{escape(task['difficulty'])}</td>"
            f"<td>{escape(task['category'])}</td>"
            f"<td><span class=\"pill {status_class(status)}\">{escape(status)}</span></td>"
            f"<td>{fmt_number(task.get('best_reward'))}</td>"
            f"<td>{fmt_number(task['trials'])}</td>"
            f"<td>{fmt_number(task['clean_passes'])}</td>"
            f"<td>{fmt_number(task['timeout_passes'])}</td>"
            f"<td>{escape(', '.join(task['harnesses']))}</td>"
            f"<td>{escape(', '.join(task['models']))}</td>"
            f"<td><a href=\"../../jobs/{escape(task['latest_job'] or '')}/result.json\">{escape(task['latest_job'] or '')}</a></td>"
            f"<td>{escape(task.get('latest_summary') or '')}</td>"
            "</tr>"
            f"<tr id=\"{task_id}\" class=\"task-detail\" hidden>"
            f"<td colspan=\"12\">{render_task_detail(task['entries'])}</td>"
            "</tr>"
        )

    generated_at = escape(payload["generated_at"])
    selected_benchmark = payload.get("benchmark") or DEFAULT_BENCHMARK
    selected_label = benchmark_label(selected_benchmark)
    query_suffix = benchmark_query_suffix(selected_benchmark)
    data_json = escape(json.dumps(payload, ensure_ascii=False), quote=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agon Terminal-Bench Local Scoreboard</title>
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
      grid-template-columns: repeat(6, minmax(120px, 1fr));
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
    .overview {{
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 24px;
      align-items: center;
      padding: 22px 32px;
      border-bottom: 1px solid var(--line);
      background: #fbfaf7;
    }}
    .pie {{
      width: 190px;
      height: 190px;
      border-radius: 50%;
      background:
        radial-gradient(circle at center, #fbfaf7 0 46%, transparent 47%),
        conic-gradient(
          var(--pass) 0 {pie_clean:.3f}%,
          #a16207 {pie_clean:.3f}% {pie_near:.3f}%,
          var(--fail) {pie_near:.3f}% {pie_failed:.3f}%,
          #d1d5db {pie_failed:.3f}% 100%
        );
      border: 1px solid var(--line);
    }}
    .overview-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 1px;
      background: var(--line);
      border: 1px solid var(--line);
    }}
    .overview-card {{
      background: var(--panel);
      padding: 14px 16px;
    }}
    .overview-card b {{ display: block; font-size: 24px; }}
    .overview-card span {{ color: var(--muted); font-size: 12px; }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 18px;
      margin-top: 14px;
      color: var(--muted);
      font-size: 12px;
    }}
    .key {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .swatch {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
    }}
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
    .task-row {{
      cursor: pointer;
    }}
    .task-row:hover {{
      background: #faf6ed;
    }}
    .toggle {{
      display: inline-block;
      width: 18px;
      color: var(--muted);
    }}
    .task-row.expanded .toggle {{
      color: var(--accent);
    }}
    .task-detail td {{
      padding: 0;
      background: #fbfaf7;
    }}
    .detail-table {{
      border: 0;
      border-top: 1px solid var(--line);
      font-size: 12px;
    }}
    .detail-table th {{
      position: static;
      background: #f1ece3;
    }}
    .detail-table td {{
      padding: 8px 9px;
      background: var(--panel);
    }}
    .nav {{
      display: flex;
      gap: 14px;
      margin-top: 12px;
      flex-wrap: wrap;
    }}
    @media (max-width: 900px) {{
      header, main {{ padding-left: 16px; padding-right: 16px; }}
      .overview {{
        grid-template-columns: 1fr;
        padding-left: 16px;
        padding-right: 16px;
      }}
      .overview-grid {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
      .stats {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
      input {{ min-width: 100%; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
      td:last-child {{ white-space: normal; min-width: 360px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Agon Terminal-Bench Local Scoreboard</h1>
    <div class="sub">Local run ledger for {escape(selected_label)}. This is for smoke coverage and failure triage, not an official leaderboard submission. Generated at {generated_at}.</div>
    <nav class="nav">
      <a href="./tb2-scoreboard.html?benchmark=tb2.1">TB2.1</a>
      <a href="./tb2-scoreboard.html?benchmark=tb2.0">TB2.0</a>
      <a href="./tb2-scoreboard.html">All</a>
      <a href="./tb2-runs.html{query_suffix}">Run log</a>
      <a href="/summary{query_suffix}">Lenos vs Codex summary</a>
      <a href="./tb2-scoreboard.json">JSON</a>
    </nav>
  </header>
  <section class="overview">
    <div class="pie" role="img" aria-label="TB2 task completion pie chart"></div>
    <div>
      <div class="overview-grid">
        <div class="overview-card"><b>{tb2_tasks_touched}/{TB2_TOTAL_TASKS}</b><span>TB2 tasks touched</span></div>
        <div class="overview-card"><b>{tb2_done}</b><span>passed or near-passed tasks</span></div>
        <div class="overview-card"><b>{tb2_failed}</b><span>touched but still failing</span></div>
        <div class="overview-card"><b>{tb2_not_run}</b><span>not run yet</span></div>
      </div>
      <div class="legend">
        <span class="key"><span class="swatch" style="background: var(--pass)"></span>{tb2_clean_passed} clean pass</span>
        <span class="key"><span class="swatch" style="background: #a16207"></span>{tb2_near_passed} near/timeout pass</span>
        <span class="key"><span class="swatch" style="background: var(--fail)"></span>{tb2_failed} failed</span>
        <span class="key"><span class="swatch" style="background: #d1d5db"></span>{tb2_not_run} not run</span>
      </div>
    </div>
  </section>
  <section class="stats">
    <div class="stat"><b>{len(completed)}</b><span>completed trials</span></div>
    <div class="stat"><b>{passed}</b><span>passed</span></div>
    <div class="stat"><b>{failed}</b><span>failed or errored</span></div>
    <div class="stat"><b>{tasks}</b><span>tasks touched</span></div>
    <div class="stat"><b>{models}</b><span>models touched</span></div>
    <div class="stat"><b>{harnesses}</b><span>harnesses touched</span></div>
  </section>
  <main>
    <section class="section">
      <h2>Task Dashboard</h2>
      <div class="toolbar">
        <input id="filter" type="search" placeholder="filter by task, harness, model, status, summary">
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
            <th>harnesses</th>
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
  </main>
  <script type="application/json" id="scoreboard-data">{data_json}</script>
  <script>
    const filter = document.querySelector('#filter');
    const taskRows = Array.from(document.querySelectorAll('#tasks tbody tr.task-row'));
    for (const row of taskRows) {{
      row.addEventListener('click', (event) => {{
        if (event.target.closest('a')) return;
        const detail = document.getElementById(row.dataset.detail);
        const open = detail.hasAttribute('hidden');
        row.classList.toggle('expanded', open);
        applyFilter();
      }});
      row.addEventListener('keydown', (event) => {{
        if (event.key === 'Enter' || event.key === ' ') {{
          event.preventDefault();
          row.click();
        }}
      }});
    }}
    function applyFilter() {{
      const q = filter.value.trim().toLowerCase();
      for (const row of taskRows) {{
        const detail = document.getElementById(row.dataset.detail);
        const matches = !q || row.textContent.toLowerCase().includes(q) || detail.textContent.toLowerCase().includes(q);
        row.hidden = !matches;
        detail.hidden = !matches || !row.classList.contains('expanded');
      }}
    }}
    filter.addEventListener('input', applyFilter);
  </script>
</body>
</html>
"""


def render_runs_html(payload: dict) -> str:
    payload = filter_payload(payload, payload.get("benchmark"))
    entries = payload["entries"]
    generated_at = escape(payload["generated_at"])
    selected_benchmark = payload.get("benchmark") or DEFAULT_BENCHMARK
    selected_label = benchmark_label(selected_benchmark)
    query_suffix = benchmark_query_suffix(selected_benchmark)
    data_json = escape(json.dumps(payload, ensure_ascii=False), quote=False)
    rows = render_run_rows(entries)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agon Terminal-Bench Run Log</title>
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
    h1 {{ margin: 0 0 10px; font-size: 24px; letter-spacing: 0; }}
    .sub {{ color: var(--muted); max-width: 980px; line-height: 1.5; }}
    .nav {{ display: flex; gap: 14px; margin-top: 12px; flex-wrap: wrap; }}
    main {{ padding: 24px 32px 40px; }}
    .toolbar {{ display: flex; gap: 12px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }}
    input {{
      min-width: 360px;
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
    @media (max-width: 900px) {{
      header, main {{ padding-left: 16px; padding-right: 16px; }}
      input {{ min-width: 100%; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
      td:last-child {{ white-space: normal; min-width: 360px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Agon Terminal-Bench Run Log</h1>
    <div class="sub">Raw trial rows for {escape(selected_label)} from jobs/* result files. Generated at {generated_at}.</div>
    <nav class="nav">
      <a href="./tb2-runs.html?benchmark=tb2.1">TB2.1</a>
      <a href="./tb2-runs.html?benchmark=tb2.0">TB2.0</a>
      <a href="./tb2-runs.html">All</a>
      <a href="./tb2-scoreboard.html{query_suffix}">Task dashboard</a>
      <a href="/summary{query_suffix}">Lenos vs Codex summary</a>
      <a href="./tb2-scoreboard.json">JSON</a>
    </nav>
  </header>
  <main>
    <div class="toolbar">
      <input id="filter" type="search" placeholder="filter by task, harness, model, status, summary">
      <span class="hint">{len(entries)} raw runs</span>
    </div>
    <table id="runs">
      <thead>
        <tr>
          <th>job</th>
          <th>task</th>
          <th>harness</th>
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
      <tbody>{rows}</tbody>
    </table>
  </main>
  <script type="application/json" id="scoreboard-data">{data_json}</script>
  <script>
    const filter = document.querySelector('#filter');
    const runRows = Array.from(document.querySelectorAll('#runs tbody tr'));
    function applyFilter() {{
      const q = filter.value.trim().toLowerCase();
      for (const row of runRows) {{
        row.hidden = q && !row.textContent.toLowerCase().includes(q);
      }}
    }}
    filter.addEventListener('input', applyFilter);
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
    RUNS_HTML_PATH.write_text(render_runs_html(payload), encoding="utf-8")
    print(f"wrote {JSON_PATH.relative_to(ROOT)}")
    print(f"wrote {HTML_PATH.relative_to(ROOT)}")
    print(f"wrote {RUNS_HTML_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
