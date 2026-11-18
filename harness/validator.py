"""Answer validation and local scoring.

Mirrors the event's hard rule: **a task scores 0 if any required output is
missing, unparseable, unit-less, or in a unit of the wrong dimension.**
Within-tolerance numeric agreement is checked after converting the submitted
value into the required unit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .task_loader import Task
from .units import UnitError, convert, parse_unit


@dataclass
class OutputCheck:
    name: str
    required_unit: str
    ok: bool
    reason: str = ""
    submitted_value: float | None = None
    submitted_unit: str | None = None
    converted_value: float | None = None  # value expressed in required unit


@dataclass
class ValidationResult:
    task_id: str
    complete: bool  # every required output present & structurally valid
    checks: list[OutputCheck] = field(default_factory=list)

    @property
    def problems(self) -> list[str]:
        return [f"{c.name}: {c.reason}" for c in self.checks if not c.ok]


def _coerce_entry(entry) -> tuple[float, str] | None:
    """Accept {'value':..,'unit':..} or a bare number (unit -> None)."""
    if isinstance(entry, dict):
        if "value" not in entry:
            return None
        try:
            return float(entry["value"]), entry.get("unit")
        except (TypeError, ValueError):
            return None
    if isinstance(entry, (int, float)):
        return float(entry), None
    return None


def validate_answer(task: Task, answer: dict) -> ValidationResult:
    """Structural validation: presence, parseability, unit sanity.

    This is the pre-submission self-check. `complete=False` means the answer
    would score ZERO under the event rule, no matter the numbers.
    """
    outputs = (answer or {}).get("outputs") or {}
    checks: list[OutputCheck] = []
    for req in task.required_outputs:
        chk = OutputCheck(name=req.name, required_unit=req.unit, ok=False)
        if req.name not in outputs:
            chk.reason = "MISSING output"
            checks.append(chk)
            continue
        coerced = _coerce_entry(outputs[req.name])
        if coerced is None:
            chk.reason = "unparseable value"
            checks.append(chk)
            continue
        value, unit = coerced
        chk.submitted_value = value
        chk.submitted_unit = unit
        if unit is None or str(unit).strip() == "":
            chk.reason = "MISSING unit"
            checks.append(chk)
            continue
        try:
            su = parse_unit(str(unit))
            ru = parse_unit(req.unit)
        except UnitError as e:
            chk.reason = f"bad unit: {e}"
            checks.append(chk)
            continue
        if su.dimension != ru.dimension:
            chk.reason = (
                f"unit dimension mismatch: submitted {unit!r} ({su.dimension}) "
                f"vs required {req.unit!r} ({ru.dimension})"
            )
            checks.append(chk)
            continue
        chk.converted_value = convert(value, str(unit), req.unit)
        chk.ok = True
        chk.reason = "ok"
        checks.append(chk)
    return ValidationResult(
        task_id=task.id,
        complete=all(c.ok for c in checks),
        checks=checks,
    )


def score_answer(task: Task, answer: dict) -> tuple[float, ValidationResult]:
    """Score one answer: 1.0 iff structurally complete AND every output is
    within its relative tolerance of the reference; otherwise 0.0."""
    result = validate_answer(task, answer)
    if not result.complete:
        return 0.0, result
    for chk in result.checks:
        ref = task.reference.get(chk.name)
        if ref is None:
            chk.ok = False
            chk.reason = "no reference available for scoring"
            continue
        ref_in_req_unit = convert(float(ref["value"]), str(ref["unit"]), chk.required_unit)
        tol = next(
            o.rel_tol for o in task.required_outputs if o.name == chk.name
        )
        denom = abs(ref_in_req_unit) if ref_in_req_unit != 0 else 1.0
        rel_err = abs(chk.converted_value - ref_in_req_unit) / denom
        if rel_err > tol:
            chk.ok = False
            chk.reason = (
                f"value out of tolerance: got {chk.converted_value:.6g} "
                f"{chk.required_unit}, reference {ref_in_req_unit:.6g}, "
                f"rel_err {rel_err:.3%} > tol {tol:.3%}"
            )
    passed = all(c.ok for c in result.checks)
    return (1.0 if passed else 0.0), result
