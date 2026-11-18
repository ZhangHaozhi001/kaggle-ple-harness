"""Local scorer + pre-submission self-check.

Scorer: runs the agent over a task directory and reports per-task 0/1 scores
and the mean — the same number the 2026-12-06 checkpoint gate is judged on
(stop if the dev-subset mean is < 0.20).

Self-check: given a directory of answer files, verify every answer is
structurally complete against its task spec (no missing output, no missing
or wrong-dimension unit). This is the gate that must pass before any real
submission.
"""
from __future__ import annotations

import json
from pathlib import Path

from .agent import Agent
from .model import ModelClient
from .task_loader import load_task_dir
from .validator import score_answer, validate_answer

CHECKPOINT_GATE = 0.20  # stop-loss line from the plan (2026-12-06)


def run_scoring(tasks_dir: str | Path, model: ModelClient) -> dict:
    tasks = load_task_dir(tasks_dir)
    agent = Agent(model)
    per_task = []
    for task in tasks:
        run = agent.run_task(task)
        if run.complete and run.answer is not None:
            score, detail = score_answer(task, run.answer)
            problems = detail.problems
        else:
            score, problems = 0.0, run.problems
        per_task.append(
            {
                "task_id": task.id,
                "score": score,
                "attempts": run.attempts,
                "complete": run.complete,
                "problems": problems,
            }
        )
    mean = sum(t["score"] for t in per_task) / len(per_task) if per_task else 0.0
    return {
        "model": model.name,
        "n_tasks": len(per_task),
        "mean_score": mean,
        "checkpoint_gate": CHECKPOINT_GATE,
        "passes_checkpoint_gate": mean >= CHECKPOINT_GATE,
        "per_task": per_task,
    }


def run_self_check(tasks_dir: str | Path, answers_dir: str | Path) -> dict:
    """answers_dir holds <task_id>.json files in answer format."""
    tasks = load_task_dir(tasks_dir)
    report = []
    all_ok = True
    for task in tasks:
        p = Path(answers_dir) / f"{task.id}.json"
        if not p.exists():
            report.append({"task_id": task.id, "ok": False, "problems": ["no answer file"]})
            all_ok = False
            continue
        answer = json.loads(p.read_text(encoding="utf-8"))
        result = validate_answer(task, answer)
        report.append(
            {"task_id": task.id, "ok": result.complete, "problems": result.problems}
        )
        all_ok = all_ok and result.complete
    return {"all_complete": all_ok, "per_task": report}
