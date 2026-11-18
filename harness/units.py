"""Unit parsing, dimensions and conversion (stdlib only).

The competition scores a task as ZERO if any required output is missing or
carries a wrong / missing unit. This module is the single source of truth for
what a unit string means: its physical dimension and its factor to the SI
base unit of that dimension.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


class UnitError(ValueError):
    """Raised for unknown units or dimension mismatches."""


@dataclass(frozen=True)
class Unit:
    name: str          # canonical symbol, e.g. "mm"
    dimension: str     # e.g. "length"
    to_base: float     # multiply a value in this unit by this to get SI base


# dimension -> SI base unit symbol
BASE_UNITS = {
    "length": "m",
    "mass": "kg",
    "time": "s",
    "temperature": "K",
    "pressure": "Pa",
    "force": "N",
    "energy": "J",
    "power": "W",
    "power_flux": "W/m^2",
    "velocity": "m/s",
    "acceleration": "m/s^2",
    "area": "m^2",
    "volume": "m^3",
    "moment_of_area": "m^4",
    "volume_flow": "m^3/s",
    "density": "kg/m^3",
    "frequency": "Hz",
    "angle": "rad",
    "dimensionless": "1",
}

_REGISTRY: dict[str, Unit] = {}


def _reg(name: str, dimension: str, to_base: float, *aliases: str) -> None:
    u = Unit(name=name, dimension=dimension, to_base=to_base)
    _REGISTRY[name] = u
    for a in aliases:
        _REGISTRY[a] = u


# length
_reg("m", "length", 1.0, "meter", "meters", "metre", "metres")
_reg("mm", "length", 1e-3, "millimeter", "millimeters")
_reg("cm", "length", 1e-2, "centimeter", "centimeters")
_reg("km", "length", 1e3, "kilometer", "kilometers")
_reg("um", "length", 1e-6, "micrometer", "micrometers", "µm")
_reg("in", "length", 0.0254, "inch", "inches")
_reg("ft", "length", 0.3048, "foot", "feet")
# mass
_reg("kg", "mass", 1.0, "kilogram", "kilograms")
_reg("g", "mass", 1e-3, "gram", "grams")
_reg("t", "mass", 1e3, "tonne", "tonnes", "metric ton")
_reg("lb", "mass", 0.45359237, "lbs", "pound", "pounds")
# time
_reg("s", "time", 1.0, "sec", "secs", "second", "seconds")
_reg("ms", "time", 1e-3, "millisecond", "milliseconds")
_reg("min", "time", 60.0, "minute", "minutes")
_reg("h", "time", 3600.0, "hr", "hrs", "hour", "hours")
# temperature (absolute only; degC handled specially in convert())
_reg("K", "temperature", 1.0, "kelvin")
_reg("degC", "temperature", 1.0, "°C", "celsius", "deg C")
_reg("degF", "temperature", 5.0 / 9.0, "°F", "fahrenheit", "deg F")
# pressure
_reg("Pa", "pressure", 1.0, "pascal", "pascals")
_reg("kPa", "pressure", 1e3, "kilopascal", "kilopascals")
_reg("MPa", "pressure", 1e6, "megapascal", "megapascals")
_reg("bar", "pressure", 1e5, "bars")
_reg("atm", "pressure", 101325.0, "atmosphere", "atmospheres")
_reg("psi", "pressure", 6894.757, "lbf/in^2")
# force
_reg("N", "force", 1.0, "newton", "newtons")
_reg("kN", "force", 1e3, "kilonewton", "kilonewtons")
# energy
_reg("J", "energy", 1.0, "joule", "joules")
_reg("kJ", "energy", 1e3, "kilojoule", "kilojoules")
_reg("MJ", "energy", 1e6, "megajoule", "megajoules")
_reg("kWh", "energy", 3.6e6, "kwh", "kilowatt-hour", "kilowatt-hours")
_reg("cal", "energy", 4.184, "calorie", "calories")
_reg("kcal", "energy", 4184.0, "kilocalorie", "kilocalories")
# power
_reg("W", "power", 1.0, "watt", "watts")
_reg("kW", "power", 1e3, "kilowatt", "kilowatts")
_reg("MW", "power", 1e6, "megawatt", "megawatts")
_reg("hp", "power", 745.699872, "horsepower")
_reg("W/m^2", "power_flux", 1.0, "W/m2", "watts per square meter")
# velocity
_reg("m/s", "velocity", 1.0, "mps")
_reg("km/h", "velocity", 1000.0 / 3600.0, "kmh", "kph")
# acceleration
_reg("m/s^2", "acceleration", 1.0, "m/s2", "m/s²")
# area / volume / density / frequency / angle / dimensionless
_reg("m^2", "area", 1.0, "m2", "m²", "sq m")
_reg("cm^2", "area", 1e-4, "cm2", "cm²")
_reg("mm^2", "area", 1e-6, "mm2", "mm²")
_reg("m^3", "volume", 1.0, "m3", "m³")
_reg("m^4", "moment_of_area", 1.0, "m4")
_reg("L", "volume", 1e-3, "l", "liter", "liters", "litre", "litres")
_reg("mL", "volume", 1e-6, "ml", "milliliter", "milliliters")
_reg("m^3/s", "volume_flow", 1.0, "m3/s")
_reg("L/s", "volume_flow", 1e-3, "l/s", "liters per second")
_reg("kg/m^3", "density", 1.0, "kg/m3")
_reg("g/cm^3", "density", 1e3, "g/cm3", "g/cc")
_reg("Hz", "frequency", 1.0, "hertz", "1/s")
_reg("kHz", "frequency", 1e3, "kilohertz")
_reg("rpm", "frequency", 1.0 / 60.0, "rev/min")
_reg("rad", "angle", 1.0, "radian", "radians")
_reg("deg", "angle", 3.141592653589793 / 180.0, "degree", "degrees", "°")
_reg("1", "dimensionless", 1.0, "", "-", "unitless", "none")


def parse_unit(raw: str | None) -> Unit:
    """Parse a unit string into a Unit. Raises UnitError if unknown/missing."""
    if raw is None:
        raise UnitError("missing unit (None)")
    key = str(raw).strip()
    if key in _REGISTRY:
        return _REGISTRY[key]
    lowered = key.lower()
    for name, unit in _REGISTRY.items():
        if name.lower() == lowered:
            return unit
    raise UnitError(f"unknown unit: {raw!r}")


_TEMP_UNITS = {"K", "degC", "degF"}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert value between two units of the same dimension.

    Raises UnitError on dimension mismatch or unknown unit.
    Temperature uses absolute-scale conversion (offsets included).
    """
    fu = parse_unit(from_unit)
    tu = parse_unit(to_unit)
    if fu.dimension != tu.dimension:
        raise UnitError(
            f"dimension mismatch: {from_unit!r} is {fu.dimension}, "
            f"{to_unit!r} is {tu.dimension}"
        )
    if fu.dimension == "temperature":
        # to kelvin
        if fu.name == "degC":
            kelvin = value + 273.15
        elif fu.name == "degF":
            kelvin = (value - 32.0) * 5.0 / 9.0 + 273.15
        else:
            kelvin = value
        if tu.name == "degC":
            return kelvin - 273.15
        if tu.name == "degF":
            return (kelvin - 273.15) * 9.0 / 5.0 + 32.0
        return kelvin
    return value * fu.to_base / tu.to_base


_NUMBER_RE = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*?)\s*$"
)


def parse_value_with_unit(text: str) -> tuple[float, str]:
    """Parse strings like '12.5 mm' or '-3e2 kPa' into (value, unit string)."""
    m = _NUMBER_RE.match(str(text))
    if not m:
        raise UnitError(f"cannot parse numeric value from {text!r}")
    return float(m.group(1)), m.group(2)
