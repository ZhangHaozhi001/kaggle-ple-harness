"""Agent execution loop.

Per task: build the strict prompt -> call the model -> validate the answer
-> if structurally incomplete, retry with the validator's complaints as
feedback (bounded) -> final answer record. The loop never lets a structurally
incomplete answer pass silently: it is either fixed within the retry budget
or recorded as failed with the exact reasons.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model import ModelClient
from .task_loader import Task
from .validator import validate_answer


@dataclass
class AgentRun:
    task_id: str
    answer: dict | None
    attempts: int
    complete: bool
    problems: list[str] = field(default_factory=list)
    prompt: str = ""


class Agent:
    def __init__(self, model: ModelClient, max_attempts: int = 3) -> None:
        self.model = model
        self.max_attempts = max_attempts

    def run_task(self, task: Task) -> AgentRun:
        from .model import build_prompt

        prompt = build_prompt(task)
        feedback: str | None = None
        last_problems: list[str] = []
        for attempt in range(1, self.max_attempts + 1):
            answer = self.model.solve(task, feedback=feedback)
            result = validate_answer(task, answer)
            if result.complete:
                return AgentRun(
                    task_id=task.id,
                    answer=answer,
                    attempts=attempt,
                    complete=True,
                    prompt=prompt,
                )
            last_problems = result.problems
            feedback = (
                "Your previous answer would score ZERO. Fix every problem "
                "and return the full JSON again:\n"
                + "\n".join(f"- {p}" for p in last_problems)
            )
        return AgentRun(
            task_id=task.id,
            answer=None,
            attempts=self.max_attempts,
            complete=False,
            problems=last_problems,
            prompt=prompt,
        )
