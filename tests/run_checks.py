"""Negative-path checks for the strict-spec rules (run: python tests/run_checks.py).

These verify the harness actually enforces the event's zero-score rule:
missing output, missing unit, wrong-dimension unit, out-of-tolerance value,
and malformed task specs must all be caught — not waved through.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.task_loader import TaskSpecError, load_task, load_task_dir
from harness.units import UnitError, convert
from harness.validator import score_answer, validate_answer

ROOT = Path(__file__).resolve().parent.parent
failures = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


tasks = {t.id: t for t in load_task_dir(ROOT / "sample_tasks")}
beam = tasks["beam-001"]
good = {"outputs": {
    "max_deflection": {"value": 0.0137224, "unit": "m"},
    "max_stress": {"value": 114.35e6, "unit": "Pa"},
}}

# happy path (SI answers against mm/MPa requirements, via conversion)
s, _ = score_answer(beam, good)
check("good answer scores 1.0", s == 1.0)

# missing output -> zero
bad = {"outputs": {"max_deflection": {"value": 13.72, "unit": "mm"}}}
s, r = score_answer(beam, bad)
check("missing output scores 0", s == 0.0 and not r.complete)

# missing unit -> zero
bad = {"outputs": {
    "max_deflection": {"value": 13.72},
    "max_stress": {"value": 114.35, "unit": "MPa"},
}}
s, r = score_answer(beam, bad)
check("missing unit scores 0", s == 0.0 and any("MISSING unit" in p for p in r.problems))

# wrong dimension (stress reported in mm) -> zero
bad = {"outputs": {
    "max_deflection": {"value": 13.72, "unit": "mm"},
    "max_stress": {"value": 114.35, "unit": "mm"},
}}
s, r = score_answer(beam, bad)
check("wrong-dimension unit scores 0", s == 0.0 and any("dimension mismatch" in p for p in r.problems))

# right unit, wrong value -> zero
bad = {"outputs": {
    "max_deflection": {"value": 99.0, "unit": "mm"},
    "max_stress": {"value": 114.35, "unit": "MPa"},
}}
s, r = score_answer(beam, bad)
check("out-of-tolerance value scores 0", s == 0.0 and any("out of tolerance" in p for p in r.problems))

# Celsius trap: efficiency computed with raw Celsius ratio must fail
carnot = tasks["carnot-001"]
trap = {"outputs": {
    "efficiency": {"value": 1 - 25 / 500, "unit": "1"},
    "work_output": {"value": (1 - 25 / 500) * 120, "unit": "kW"},
}}
s, _ = score_answer(carnot, trap)
check("celsius-trap answer scores 0", s == 0.0)

# unit engine sanity
check("degC->K offset", abs(convert(25, "degC", "K") - 298.15) < 1e-9)
check("mm->m", abs(convert(1000, "mm", "m") - 1.0) < 1e-12)
try:
    convert(1, "mm", "kPa")
    check("cross-dimension convert raises", False)
except UnitError:
    check("cross-dimension convert raises", True)

# malformed task spec must be rejected by the loader
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "bad.json"
    p.write_text(json.dumps({"id": "x", "title": "x", "prompt": "x",
                             "required_outputs": [{"name": "a"}]}))
    try:
        load_task(p)
        check("spec without unit rejected", False)
    except TaskSpecError:
        check("spec without unit rejected", True)

print("\n%d failure(s)" % len(failures))
sys.exit(1 if failures else 0)
