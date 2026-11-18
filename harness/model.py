"""Model layer: interface, local mock (zero cost), real-model stub.

The agent loop talks only to `ModelClient`. Swapping the mock for the real
target model (`google-cloud/claude-opus-5-5` via Vertex AI) must not change
any other code. The real client is a stub in this skeleton: it refuses to run
without explicit configuration so no API cost can be incurred accidentally.
"""
from __future__ import annotations

import json
import math
import os
from abc import ABC, abstractmethod

from .task_loader import Task
from .units import convert

TARGET_MODEL_ID = "google-cloud/claude-opus-5-5"


class ModelNotConfigured(RuntimeError):
    pass


class ModelClient(ABC):
    name = "abstract"

    @abstractmethod
    def solve(self, task: Task, feedback: str | None = None) -> dict:
        """Return an answer dict: {"outputs": {name: {"value":..,"unit":..}}}"""
        raise NotImplementedError


def _inp(task: Task, key: str, unit: str) -> float:
    """Read a task input converted into the requested unit."""
    entry = task.inputs[key]
    return convert(float(entry["value"]), str(entry["unit"]), unit)


# --- Mock solvers: tiny rule-based physics for the SELF-MADE sample tasks ---
# They deliberately answer in SI base units; the validator's unit conversion
# is what turns them into the required units — exactly the discipline the
# real model will have to follow (it will be told the required units too).

def _solve_beam(task: Task) -> dict:
    F = _inp(task, "force", "N")
    L = _inp(task, "length", "m")
    E = _inp(task, "youngs_modulus", "Pa")
    I = _inp(task, "second_moment", "m^4")
    delta = F * L**3 / (3.0 * E * I)
    sigma = F * L * _inp(task, "half_depth", "m") / I  # bending stress Mc/I
    return {"outputs": {
        "max_deflection": {"value": delta, "unit": "m"},
        "max_stress": {"value": sigma, "unit": "Pa"},
    }}


def _solve_pipe(task: Task) -> dict:
    f = float(task.inputs["friction_factor"]["value"])
    L = _inp(task, "length", "m")
    D = _inp(task, "diameter", "m")
    rho = _inp(task, "density", "kg/m^3")
    Q = _inp(task, "flow_rate", "m^3/s")
    A = math.pi * D**2 / 4.0
    v = Q / A
    dp = f * (L / D) * rho * v**2 / 2.0
    return {"outputs": {
        "mean_velocity": {"value": v, "unit": "m/s"},
        "pressure_drop": {"value": dp, "unit": "Pa"},
    }}


def _solve_heat(task: Task) -> dict:
    k = float(task.inputs["conductivity"]["value"])  # W/(m K)
    A = _inp(task, "area", "m^2")
    d = _inp(task, "thickness", "m")
    dT = _inp(task, "temp_hot", "K") - _inp(task, "temp_cold", "K")
    Q = k * A * dT / d
    return {"outputs": {
        "heat_rate": {"value": Q, "unit": "W"},
        "heat_flux": {"value": Q / A, "unit": "W/m^2"},
    }}


def _solve_carnot(task: Task) -> dict:
    Th = _inp(task, "hot_temp", "K")
    Tc = _inp(task, "cold_temp", "K")
    eta = 1.0 - Tc / Th
    Qin = _inp(task, "heat_input", "kW")
    return {"outputs": {
        "efficiency": {"value": eta, "unit": "1"},
        "work_output": {"value": eta * Qin, "unit": "kW"},
    }}


def _solve_projectile(task: Task) -> dict:
    v0 = _inp(task, "speed", "m/s")
    ang = math.radians(_inp(task, "angle", "deg"))
    g = 9.81
    R = v0**2 * math.sin(2 * ang) / g
    H = (v0 * math.sin(ang)) ** 2 / (2 * g)
    T = 2 * v0 * math.sin(ang) / g
    return {"outputs": {
        "range": {"value": R, "unit": "m"},
        "max_height": {"value": H, "unit": "m"},
        "flight_time": {"value": T, "unit": "s"},
    }}


def _solve_rc(task: Task) -> dict:
    R = float(task.inputs["resistance"]["value"]) * 1000.0  # input given in kΩ -> Ω
    C = float(task.inputs["capacitance"]["value"]) * 1e-6  # µF -> F
    V = float(task.inputs["voltage"]["value"])
    tau = R * C
    energy = 0.5 * C * V**2
    return {"outputs": {
        "time_constant": {"value": tau, "unit": "s"},
        "stored_energy": {"value": energy, "unit": "J"},
    }}


def _solve_hydro(task: Task) -> dict:
    rho = _inp(task, "density", "kg/m^3")
    H = _inp(task, "depth", "m")
    Wd = _inp(task, "width", "m")
    g = 9.81
    p_bottom = rho * g * H
    F = rho * g * (H / 2.0) * (H * Wd)  # centroid depth H/2, area H*W
    return {"outputs": {
        "bottom_pressure": {"value": p_bottom, "unit": "Pa"},
        "total_force": {"value": F, "unit": "N"},
    }}


_MOCK_SOLVERS = {
    "beam_deflection": _solve_beam,
    "pipe_pressure_drop": _solve_pipe,
    "heat_conduction": _solve_heat,
    "carnot_efficiency": _solve_carnot,
    "projectile": _solve_projectile,
    "rc_circuit": _solve_rc,
    "hydrostatic_force": _solve_hydro,
}


class MockModelClient(ModelClient):
    """Deterministic local stand-in. No network, no cost."""

    name = "mock"

    def solve(self, task: Task, feedback: str | None = None) -> dict:
        fn = _MOCK_SOLVERS.get(task.solver or "")
        if fn is None:
            raise ModelNotConfigured(
                f"mock model has no solver for task {task.id!r} "
                f"(solver={task.solver!r}); mock only covers self-made samples"
            )
        return fn(task)


class VertexModelClient(ModelClient):
    """Real target model stub: google-cloud/claude-opus-5-5 via Vertex AI.

    Intentionally refuses to run until PLE_MODEL_ENABLED=1 and credentials
    are wired in the next build segment — the skeleton must never spend money.
    """

    name = TARGET_MODEL_ID

    def __init__(self) -> None:
        if os.environ.get("PLE_MODEL_ENABLED") != "1":
            raise ModelNotConfigured(
                "real model disabled (set PLE_MODEL_ENABLED=1 in the next "
                "segment once Kaggle/HF user steps are done); skeleton is "
                "mock-only so it cannot incur API cost"
            )

    def solve(self, task: Task, feedback: str | None = None) -> dict:  # pragma: no cover
        raise ModelNotConfigured("Vertex transport not wired yet (next segment)")


def build_prompt(task: Task) -> str:
    """Prompt contract for the real model (also used in the writeup)."""
    req = "\n".join(
        f'- "{o.name}": a number with unit exactly "{o.unit}"'
        for o in task.required_outputs
    )
    return (
        "Solve the following physical-engineering problem.\n\n"
        f"{task.prompt}\n\n"
        "Return ONLY a JSON object of the form "
        '{"outputs": {"<name>": {"value": <number>, "unit": "<unit>"}}}.\n'
        "Required outputs (every one is mandatory; a missing output or a "
        "missing/wrong unit scores zero for the whole problem):\n"
        f"{req}\n"
        "You may compute in any units internally, but each returned value "
        "MUST be expressed in the required unit stated above."
    )


def parse_model_reply(text: str) -> dict:
    """Extract the JSON answer object from a raw model reply."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found in model reply")
    return json.loads(text[start : end + 1])
