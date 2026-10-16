"""Fault library for the multi-zone thermal plant.

Fault classes mirror the categories used in the base paper (actuator, process,
sensor) and add a safety-critical actuator fault that only an interlock can handle.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .thermal import FaultState

FAULT_TYPES = {
    "heater_degradation": "actuator",   # heater delivers only a fraction of commanded power
    "heat_loss_increase": "process",    # insulation loss / forced convection raises U
    "sensor_bias": "sensor",            # thermocouple reads offset (negative = reads low)
    "local_insulation_loss": "process", # one zone loses insulation (local U increase)
    "actuator_stuck_high": "actuator",  # heater output frozen high (runaway risk)
}


@dataclass
class FaultSpec:
    kind: str
    zone: int
    magnitude: float  # meaning depends on kind (scale factor, bias in degC, or stuck %)
    onset_s: float

    def describe(self) -> str:
        return f"{self.kind} on zone {self.zone} (magnitude={self.magnitude}) at t={self.onset_s:.0f}s"


# Nominal magnitudes: what an engineer would assume when only the fault type is known.
NOMINAL_MAGNITUDE = {
    "heater_degradation": 0.4,
    "heat_loss_increase": 3.0,
    "sensor_bias": -10.0,
    "local_insulation_loss": 4.0,
    "actuator_stuck_high": 92.0,
}

# Ranges are chosen so that every fault forces a decision: the nominal setpoint becomes
# unreachable (degradation / heat loss), the true temperature drifts off target (bias), or a
# stuck heater may or may not breach the safety limit depending on zone and magnitude.
MAGNITUDE_RANGE = {
    "heater_degradation": (0.3, 0.5),
    "heat_loss_increase": (2.5, 3.5),
    "sensor_bias": (-14.0, -7.0),
    "local_insulation_loss": (3.0, 5.0),
    "actuator_stuck_high": (85.0, 100.0),
}


def apply_fault(fault: FaultState, spec: FaultSpec) -> None:
    """Mutate a FaultState in place so the plant exhibits the fault."""
    z = spec.zone
    if spec.kind == "heater_degradation":
        fault.alpha_scale[z] = spec.magnitude
    elif spec.kind == "heat_loss_increase":
        fault.U_scale[:] = spec.magnitude  # affects whole enclosure (fan / door open)
    elif spec.kind == "local_insulation_loss":
        fault.U_scale[z] = spec.magnitude
    elif spec.kind == "sensor_bias":
        fault.sensor_bias[z] = spec.magnitude
    elif spec.kind == "actuator_stuck_high":
        fault.stuck_value[z] = spec.magnitude
    else:
        raise ValueError(f"unknown fault kind {spec.kind}")


def sample_fault(rng: np.random.Generator, kind: str, n_zones: int, onset_s: float) -> FaultSpec:
    lo, hi = MAGNITUDE_RANGE[kind]
    mag = float(rng.uniform(lo, hi)) if hi > lo else lo
    zone = 0 if kind == "heat_loss_increase" else int(rng.integers(0, n_zones))
    return FaultSpec(kind, zone, round(mag, 3), onset_s)
