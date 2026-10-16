"""Structured contracts exchanged between the environment, tools and agents.

Every LLM output is parsed into one of these models; anything that fails to
parse is treated as a validation failure (and triggers reprompting), never
executed directly.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Mode(str, Enum):
    """Operating modes of the supervisory finite-state machine."""

    NORMAL = "NORMAL"                    # hold current settings (monitor only)
    RETUNE = "RETUNE"                    # change PID gains of one or more zones
    DERATE = "DERATE"                    # lower setpoint and/or heater output limit
    SENSOR_CORRECTION = "SENSOR_CORRECTION"  # compensate a biased sensor with an offset
    COMPENSATE = "COMPENSATE"            # use neighbouring zones to cover a dead heater
    SAFE_SHUTDOWN = "SAFE_SHUTDOWN"      # hard interlock: cut all heater power


class Snapshot(BaseModel):
    """Plant state shown to agents (measured values only, never the hidden truth)."""

    t_s: float
    n_zones: int
    measured_T: list[float]
    setpoints: list[float]
    heater_output_pct: list[float]
    q_max: list[float]
    gains: list[dict]
    sensor_offset: list[float]
    residuals: list[float] = Field(description="measured minus nominal-model prediction, degC")
    trend: dict = Field(default_factory=dict, description="recent downsampled history per signal")
    ambient_T: float = 23.0
    safety_limit_T: float = 60.0


class FaultReport(BaseModel):
    detected: bool
    t_detect_s: float | None = None
    symptoms: list[str] = Field(default_factory=list)
    # localisation fields: filled by the oracle in the base-paper setting, by diagnosis in ours
    fault_class: Literal["actuator", "sensor", "process", "unknown"] = "unknown"
    fault_kind: str | None = None
    zone: int | None = None
    localisation_source: Literal["oracle", "diagnosis", "none"] = "none"


class PlanDecision(BaseModel):
    target_mode: Mode
    rationale: str = ""


class ZoneGains(BaseModel):
    Kc: float
    tauI: float


class RecoveryAction(BaseModel):
    """Continuous/discrete recovery parameters proposed by the Action Agent."""

    mode: Mode
    setpoints: dict[int, float] = Field(default_factory=dict)
    gains: dict[int, ZoneGains] = Field(default_factory=dict)
    q_max: dict[int, float] = Field(default_factory=dict)
    sensor_offset: dict[int, float] = Field(default_factory=dict)
    shutdown: bool = False
    rationale: str = ""


class Violation(BaseModel):
    check: str
    zone: int | None = None
    message: str
    value: float | None = None
    limit: float | None = None


class ValidationResult(BaseModel):
    passed: bool
    violations: list[Violation] = Field(default_factory=list)
    predicted: dict = Field(default_factory=dict)  # summary metrics of the twin rollout
    responsible: Literal["planner", "action", "none"] = "none"


class LLMCallRecord(BaseModel):
    agent: str
    model: str
    latency_s: float
    tokens_in: int = 0
    tokens_out: int = 0
    ok: bool = True
    error: str | None = None


class DecisionTrace(BaseModel):
    """Auditable record of one recovery decision episode."""

    method: str
    fault_report: FaultReport | None = None
    plans: list[PlanDecision] = Field(default_factory=list)
    actions: list[RecoveryAction] = Field(default_factory=list)
    validations: list[ValidationResult] = Field(default_factory=list)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)
    reprompts: int = 0
    used_fallback: bool = False
    applied_action: RecoveryAction | None = None
    decision_wall_s: float = 0.0
    notes: list[str] = Field(default_factory=list)
