"""Atomic evaluation checkpoints and validation of their run provenance."""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from math import isfinite
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

SCHEMA_VERSION = 3
BOOLEAN_METRICS = (
    "detected", "false_alarm", "localisation_correct", "agent_success", "plant_success", "plant_success_since_fault",
    "action_applied", "validated_action", "validated_but_failed", "used_fallback",
    "safety_violation_post", "safety_violation_since_fault", "shutdown", "shutdown_required",
)
NUMBER_METRICS = (
    "reprompts", "repair_attempts", "repairs_validated", "llm_calls", "provider_attempts", "model_reply_failures", "missing_usage_calls",
    "tokens_in", "tokens_out", "llm_latency_s", "api_latency_s", "decision_wall_s",
    "episode_wall_s", "tool_events", "setpoint_retention", "gain_scale_rmse",
    "loss_scale_rmse", "bias_rmse", "max_T_post", "max_T_since_fault", "time_above_limit_s",
    "time_above_limit_post_s", "time_above_limit_before_actuation_s", "iae_post",
)
OPTIONAL_METRICS = {"gain_scale_rmse", "loss_scale_rmse", "bias_rmse"}


class RunDataError(ValueError):
    """Run data cannot safely be read or combined."""


@contextmanager
def run_lock(folder: Path):
    """Lock a results directory until the runner or reader closes its file handle."""
    with (folder / ".run.lock").open("a+b") as lock:
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RunDataError("Results folder is in use. Wait for the other process or use a different --out.") from exc
        yield


def write_json(path: Path, payload):
    # Windows requires the temporary file to be closed before replacement.
    temp = None
    try:
        with NamedTemporaryFile("w", dir=path.parent, suffix=".tmp", encoding="utf-8", delete=False) as file:
            temp = Path(file.name)
            json.dump(payload, file, indent=2, allow_nan=False)
        temp.replace(path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_checksum(record):
    data = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def read_checkpoint(path, scenario, method, repeat):
    record = read_json(path)
    if (not isinstance(record, dict) or record.get("scenario") != asdict(scenario)
            or record.get("method") != method or type(record.get("repeat")) is not int
            or record["repeat"] != repeat):
        raise RunDataError("Checkpoint identity differs from its run assignment.")
    checksum = record.pop("checksum", None)
    if checksum != record_checksum(record):
        raise RunDataError("Checkpoint checksum differs from its contents.")
    metrics = record.get("metrics")
    trace = record.get("trace")
    if not isinstance(metrics, dict) or not isinstance(trace, dict):
        raise RunDataError("Checkpoint has no metrics or trace.")
    if any(type(metrics.get(key)) is not bool for key in BOOLEAN_METRICS):
        raise RunDataError("Checkpoint has missing or invalid outcome flags.")
    for key in NUMBER_METRICS:
        value = metrics.get(key)
        if key in OPTIONAL_METRICS and key in metrics and value is None:
            continue
        if type(value) not in (int, float) or not isfinite(value):
            raise RunDataError(f"Checkpoint has missing or invalid metric {key}.")
    if (metrics["detected"] != bool(trace)
            or metrics["action_applied"] != bool(trace.get("applied_action"))
            or metrics["llm_calls"] != len(trace.get("llm_calls", []))
            or metrics["validated_but_failed"] != (
                metrics["validated_action"] and metrics["agent_success"] and not metrics["plant_success"])):
        raise RunDataError("Checkpoint outcomes disagree with its decision trace.")
    return record


def load_checkpoints(tasks, out):
    for scenario, method, repeat, _, path in tasks:
        if not path.exists():
            continue
        try:
            yield read_checkpoint(path, scenario, method, repeat)
        except (ValueError, TypeError, OverflowError) as exc:
            rejected = out / "rejected_checkpoints"
            rejected.mkdir(exist_ok=True)
            path.replace(rejected / f"{path.stem}-{uuid4().hex[:8]}.json")
            print(f"Rebuilding {path.name}: {exc}", flush=True)
