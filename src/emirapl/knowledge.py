"""Plant knowledge base used to ground the agents.

The base paper stores plant knowledge in an ontology-backed graph (CPSMod,
queried with SPARQL). We keep the same kinds of knowledge (structure, function,
dynamics, control context, fault semantics, admissible modes) as a small typed
graph in Python and retrieve the subgraph relevant to the reported fault. This
keeps the baseline runnable without a GraphDB server while preserving what the
agents get to see.
"""
from __future__ import annotations

from .contracts import Mode

FAULT_CLASS = {
    "heater_degradation": "actuator",
    "heat_loss_increase": "process",
    "sensor_bias": "sensor",
    "local_insulation_loss": "process",
    "actuator_stuck_high": "actuator",
}

# Mode FSM: which recovery modes are admissible for each fault class.
ADMISSIBLE_MODES = {
    "actuator": [Mode.NORMAL, Mode.RETUNE, Mode.DERATE, Mode.COMPENSATE, Mode.SAFE_SHUTDOWN],
    "process": [Mode.NORMAL, Mode.RETUNE, Mode.DERATE, Mode.SAFE_SHUTDOWN],
    "sensor": [Mode.NORMAL, Mode.SENSOR_CORRECTION, Mode.DERATE, Mode.SAFE_SHUTDOWN],
    "unknown": [Mode.NORMAL, Mode.DERATE, Mode.SAFE_SHUTDOWN],
}

MODE_SEMANTICS = {
    Mode.NORMAL: "Keep current controller settings (monitor only); valid if the plant stays safe and regulated.",
    Mode.RETUNE: "Change PI gains (Kc in %/degC, tauI in s) of affected zones; setpoints unchanged.",
    Mode.DERATE: "Lower setpoint(s) and/or heater output limit q_max of affected zones to a feasible level.",
    Mode.SENSOR_CORRECTION: "Add an offset (degC) to a biased sensor so the loop regulates the true temperature.",
    Mode.COMPENSATE: "Adjust setpoints / output limits of zones adjacent to a faulty heater to counter its effect on them.",
    Mode.SAFE_SHUTDOWN: "Open the master heater relay (all heaters off). Use only if no operating mode is safe.",
}

CONSTRAINTS = {
    "safety_limit_T": 60.0,      # hard limit on true heater temperature, degC
    "setpoint_range": [30.0, 58.0],
    "max_derate_degC": 15.0,     # largest allowed setpoint reduction vs nominal
    "Kc_range": [0.5, 20.0],
    "tauI_range": [20.0, 600.0],
    "q_max_range": [0.0, 100.0],
    "sensor_offset_range": [-20.0, 20.0],
    "regulation_band_degC": 1.5,
}

DYNAMICS = (
    "Each zone is a lumped thermal mass (m*Cp ~ 2 J/K) heated by a resistive heater "
    "(gain alpha ~ 0.01 W/% for odd zones, 0.0075 W/% for even zones) and cooled by convection "
    "and radiation to ambient. Neighbouring zones exchange heat through a small shared area, so "
    "heating zone i also warms zones i-1 and i+1. Open-loop time constant ~ 3 min; sensors lag the "
    "heater by ~ 12 s. At 100 % output an odd zone settles near 71 degC and an even zone near 62 degC "
    "(nominal, isolated). Steady-state temperature rises roughly linearly with delivered power."
)


def plant_structure(n_zones: int) -> dict:
    zones = []
    for i in range(n_zones):
        zones.append({
            "zone": i,
            "heater": f"H{i+1}",
            "sensor": f"T{i+1}",
            "controller": f"PI-{i+1}",
            "neighbours": [j for j in (i - 1, i + 1) if 0 <= j < n_zones],
        })
    return {"n_zones": n_zones, "zones": zones, "interlock": "master heater relay (all heaters)"}


def retrieve(fault_kind: str | None, zone: int | None, n_zones: int) -> dict:
    """Return the knowledge subgraph relevant to a reported fault (Graph-RAG analogue)."""
    fclass = FAULT_CLASS.get(fault_kind or "", "unknown")
    structure = plant_structure(n_zones)
    implicated = structure["zones"] if zone is None else [
        z for z in structure["zones"] if z["zone"] == zone or z["zone"] in structure["zones"][zone]["neighbours"]]
    return {
        "fault_kind": fault_kind,
        "fault_class": fclass,
        "implicated_zones": implicated,
        "admissible_modes": [m.value for m in ADMISSIBLE_MODES[fclass]],
        "mode_semantics": {m.value: MODE_SEMANTICS[m] for m in ADMISSIBLE_MODES[fclass]},
        "constraints": CONSTRAINTS,
        "dynamics": DYNAMICS,
        "interlock": structure["interlock"],
    }
