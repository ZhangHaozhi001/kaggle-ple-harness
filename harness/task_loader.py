"""Task loading with strict spec validation.

Task file format (JSON), modelled on the official problem style:

{
  "id": "beam-001",
  "title": "...",
  "source": "self-made",              // or "official-dev"
  "prompt": "full problem statement ...",
  "inputs": {"length": {"value": 2.0, "unit": "m"}, ...},
  "required_outputs": [
    {"name": "max_deflection", "unit": "mm", "rel_tol": 0.02},
    ...
  ],
  "reference": {"max_deflection": {"value": 3.18, "unit": "mm"}}   // local scoring only
}

The loader refuses malformed tasks: a task whose spec is ambiguous must never
reach the agent, because in the real event an ambiguous spec silently costs
points instead of failing loudly here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .units import parse_unit


class TaskSpecError(ValueError):
    """Raised when a task file violates the required spec format."""


@dataclass
class RequiredOutput:
    name: str
    unit: str
    rel_tol: float = 0.02  # default scoring tolerance (relative)


@dataclass
class Task:
    id: str
    title: str
    prompt: str
    source: str
    inputs: dict = field(default_factory=dict)
    required_outputs: list[RequiredOutput] = field(default_factory=list)
    reference: dict = field(default_factory=dict)  # name -> {"value","unit"}
    solver: str | None = None  # mock-solver key, self-made tasks only

    def output_names(self) -> list[str]:
        return [o.name for o in self.required_outputs]


def _validate_task(raw: dict, where: str) -> Task:
    for key in ("id", "title", "prompt", "required_outputs"):
        if key not in raw:
            raise TaskSpecError(f"{where}: missing required field {key!r}")
    outs: list[RequiredOutput] = []
    seen: set[str] = set()
    for i, o in enumerate(raw["required_outputs"]):
        if "name" not in o or "unit" not in o:
            raise TaskSpecError(
                f"{where}: required_outputs[{i}] must carry 'name' and 'unit'"
            )
        if o["name"] in seen:
            raise TaskSpecError(f"{where}: duplicate output name {o['name']!r}")
        seen.add(o["name"])
        try:
            parse_unit(o["unit"])
        except Exception as e:  # UnitError
            raise TaskSpecError(
                f"{where}: output {o['name']!r} has unparseable unit {o['unit']!r}: {e}"
            ) from e
        outs.append(
            RequiredOutput(
                name=o["name"],
                unit=o["unit"],
                rel_tol=float(o.get("rel_tol", 0.02)),
            )
        )
    if not outs:
        raise TaskSpecError(f"{where}: required_outputs must not be empty")
    for name, ref in (raw.get("reference") or {}).items():
        if name not in seen:
            raise TaskSpecError(
                f"{where}: reference key {name!r} is not a required output"
            )
        if "value" not in ref or "unit" not in ref:
            raise TaskSpecError(
                f"{where}: reference[{name!r}] must carry 'value' and 'unit'"
            )
    return Task(
        id=str(raw["id"]),
        title=str(raw["title"]),
        prompt=str(raw["prompt"]),
        source=str(raw.get("source", "unknown")),
        inputs=raw.get("inputs") or {},
        required_outputs=outs,
        reference=raw.get("reference") or {},
        solver=raw.get("solver"),
    )


def load_task(path: str | Path) -> Task:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    return _validate_task(raw, str(p))


def load_task_dir(path: str | Path) -> list[Task]:
    p = Path(path)
    tasks = [load_task(f) for f in sorted(p.glob("*.json"))]
    ids = [t.id for t in tasks]
    if len(ids) != len(set(ids)):
        raise TaskSpecError(f"{p}: duplicate task ids in directory")
    return tasks
