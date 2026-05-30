"""Agon runner — invoke Lenos against Terminal-Bench tasks and write JSONL results."""
import json
import os
import subprocess
import sys
import time
import yaml
from datetime import datetime, timezone
from pathlib import Path
def load_task(task_dir: str) -> dict:
    """Load task.yaml from a task directory."""
    task_yaml = Path(task_dir) / "task.yaml"
    if not task_yaml.exists():
        raise FileNotFoundError(f"task.yaml not found in {task_dir}")
    with open(task_yaml) as f:
        return yaml.safe_load(f)
def get_instruction(task: dict) -> str:
    """Extract the agent instruction from task config.
    Supports both simple 'description' field and multi-description 'descriptions' list.
    Returns the 'base' description when multiple are present.
    """
    if "descriptions" in task:
        for desc in task["descriptions"]:
            if desc.get("key") == "base":
                return desc["description"]
        # fallback: first description
        return task["descriptions"][0]["description"]
    return task.get("description", "")
def run_lenos(instruction: str, model: str | None = None, timeout_sec: int = 300) -> dict:
    """Run lenos non-interactively with the given instruction.
    Returns a dict with: exit_code, stdout, stderr, duration_sec, timed_out.
    """
    cmd = ["lenos", "run", "--quiet"]
    if model:
        cmd.extend(["-m", model])
    cmd.append(instruction)
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env={**os.environ},
        )
        duration = time.monotonic() - start
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_sec": round(duration, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Agent timed out",
            "duration_sec": round(duration, 3),
            "timed_out": True,
        }
def write_jsonl(result: dict, results_dir: str) -> Path:
    """Append a result record to the JSONL file.
    Returns the path to the written file.
    """
    results_path = Path(results_dir)
    results_path.mkdir(parents=True, exist_ok=True)
    jsonl_path = results_path / "results.jsonl"
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(result) + "\n")
    return jsonl_path
def write_transcript(stdout: str, stderr: str, transcripts_dir: str, run_id: str) -> Path:
    """Write agent transcript to a timestamped file."""
    transcripts_path = Path(transcripts_dir)
    transcripts_path.mkdir(parents=True, exist_ok=True)
    transcript_file = transcripts_path / f"{run_id}.log"
    with open(transcript_file, "w") as f:
        f.write("=== STDOUT ===\n")
        f.write(stdout)
        f.write("\n=== STDERR ===\n")
        f.write(stderr)
    return transcript_file
def build_result_record(
    task: dict,
    agent_result: dict,
    run_id: str,
    model: str | None = None,
) -> dict:
    """Build a normalized JSONL result record."""
    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": {
            "description": task.get("description", ""),
            "difficulty": task.get("difficulty", ""),
            "tags": task.get("tags", []),
        },
        "agent": {
            "name": "lenos",
            "model": model or os.environ.get("LENOS_MODEL", "unknown"),
            "version": os.environ.get("LENOS_VERSION", ""),
            "exit_code": agent_result["exit_code"],
            "duration_sec": agent_result["duration_sec"],
            "timed_out": agent_result["timed_out"],
        },
        "provider": {
            "name": os.environ.get("LENOS_PROVIDER", ""),
        },
    }
def run(task_dir: str, results_dir: str, transcripts_dir: str, model: str | None = None):
    """Main entrypoint: load task, run lenos, write results."""
    task = load_task(task_dir)
    instruction = get_instruction(task)
    if not instruction:
        print("ERROR: no instruction found in task.yaml", file=sys.stderr)
        sys.exit(1)
    timeout = int(os.environ.get("AGENT_TIMEOUT_SEC", "300"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    print(f"Running task with instruction ({len(instruction)} chars)...", file=sys.stderr)
    agent_result = run_lenos(instruction, model=model, timeout_sec=timeout)
    record = build_result_record(task, agent_result, run_id, model=model)
    write_jsonl(record, results_dir)
    write_transcript(agent_result["stdout"], agent_result["stderr"], transcripts_dir, run_id)
    print(f"Results written to {results_dir}/results.jsonl", file=sys.stderr)
    print(f"Transcript saved to {transcripts_dir}/{run_id}.log", file=sys.stderr)
    return record
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Agon benchmark runner")
    parser.add_argument("--task-dir", required=True, help="Path to task directory")
    parser.add_argument("--results-dir", default="/results", help="Results output directory")
    parser.add_argument("--transcripts-dir", default="/transcripts", help="Transcripts output directory")
    parser.add_argument("--model", default=None, help="Model override")
    args = parser.parse_args()
    record = run(args.task_dir, args.results_dir, args.transcripts_dir, model=args.model)
    # Exit with agent's exit code
    sys.exit(record["agent"]["exit_code"])
