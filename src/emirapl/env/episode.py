"""One evaluation episode: warm-up, fault injection, detection, recovery decision, evaluation.

Timeline (s): 0 ---- warm-up / steady operation ---- onset (fault) -- detect -- decide
(+latency) -- apply action ---------------------------------- t_end.
All success metrics are computed on the hidden TRUE plant state, never on the twin.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from math import ceil, isfinite

import numpy as np

from ..agents.monitor import ResidualMonitor, localise_oracle
from ..contracts import DecisionTrace, FaultReport, Snapshot
from ..control.pid import MultiZoneController, PIDGains
from ..env.faults import FaultSpec, apply_fault
from ..knowledge import CONSTRAINTS
from ..safety import thermal_safety
from .closed_loop import ClosedLoop
from .thermal import FaultState, ThermalParams, ThermalPlant

@dataclass
class Scenario:
    scenario_id: str
    n_zones: int
    setpoints: list[float]
    fault: dict  # FaultSpec fields
    mismatch: float  # relative parameter mismatch between true plant and nominal model
    noise_std: float
    seed: int
    t_end_s: float = 4200.0
    secondary_faults: list[dict] = field(default_factory=list)

    def fault_spec(self) -> FaultSpec:
        return FaultSpec(**self.fault)

    def validate(self):
        if type(self.n_zones) is not int or self.n_zones < 1 or len(self.setpoints) != self.n_zones:
            raise ValueError("Provide one setpoint per plant zone.")
        lo, hi = CONSTRAINTS["setpoint_range"]
        if any(not isfinite(value) or not lo <= value <= hi for value in self.setpoints):
            raise ValueError(f"Nominal setpoints must be in [{lo}, {hi}].")
        if not isfinite(self.mismatch) or not 0 <= self.mismatch < 1:
            raise ValueError("Plant mismatch must be in [0, 1).")
        if not isfinite(self.noise_std) or self.noise_std < 0:
            raise ValueError("Noise standard deviation must be finite and nonnegative.")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("Scenario seed must be a nonnegative integer.")
        if not isfinite(self.t_end_s) or self.t_end_s < 1 or int(self.t_end_s) != self.t_end_s:
            raise ValueError("Episode duration must be a positive whole number of seconds.")
        for spec in [self.fault_spec(), *(FaultSpec(**f) for f in self.secondary_faults)]:
            spec.validate_for(self.n_zones, self.t_end_s)


@dataclass
class EpisodeResult:
    scenario_id: str
    method: str
    metrics: dict
    trace: dict
    traj: dict = field(default_factory=dict)


class Episode:
    def __init__(self, sc: Scenario, nominal: ThermalParams | None = None, latency_s: float | None = 30.0,
                 gains: PIDGains | None = None):
        sc.validate()
        if latency_s is not None and (not isfinite(latency_s) or latency_s < 0):
            raise ValueError("Actuation delay must be finite and nonnegative.")
        self.sc = sc
        rng = np.random.default_rng(sc.seed)
        self.nominal = nominal or ThermalParams(n_zones=sc.n_zones)
        true_params = self.nominal.perturbed(rng, sc.mismatch)
        plant = ThermalPlant(true_params, dt=1.0, noise_std=sc.noise_std, rng=rng)
        self.loop = ClosedLoop(plant, MultiZoneController(sc.n_zones, sc.setpoints, gains or PIDGains()))
        self.monitor = ResidualMonitor(self.nominal)
        self.latency_s = latency_s  # None -> use measured wall-clock decision time
        self.spec = sc.fault_spec()

    def snapshot(self, hist: dict) -> Snapshot:
        L, c = self.loop, self.loop.ctrl.snapshot()
        k = len(hist["t"])
        idx = list(range(max(0, k - 300), k, 30))  # last 5 min every 30 s
        trend = {"t_s": [hist["t"][i] for i in idx],
                 "measured_T": [[round(float(v), 2) for v in hist["y"][i]] for i in idx],
                 "heater_output_pct": [[round(float(v), 1) for v in hist["u"][i]] for i in idx]}
        return Snapshot(t_s=L.plant.t, n_zones=L.n, measured_T=[round(float(v), 2) for v in L.y],
                        setpoints=c["setpoints"], heater_output_pct=[round(float(v), 1) for v in L.u],
                        q_max=c["q_max"], gains=c["gains"], sensor_offset=[float(v) for v in L.sensor_offset],
                        residuals=[round(float(v - m), 2) for v, m in zip(self.monitor.residual, self.monitor.mu)],
                        trend=trend, ambient_T=self.nominal.Ta, safety_limit_T=CONSTRAINTS["safety_limit_T"])

    def run(self, method, keep_traj: bool = True) -> EpisodeResult:
        sc, L = self.sc, self.loop
        hist = {"t": [], "y": [], "u": [], "TH": [], "sp": []}
        trace: DecisionTrace | None = None
        t_detect = t_apply = None
        pending = None  # (apply_time, action)
        faults = sorted([self.spec, *(FaultSpec(**f) for f in sc.secondary_faults)], key=lambda f: f.onset_s)
        steps = int(sc.t_end_s)
        for k in range(steps):
            t = L.plant.t
            while faults and t >= faults[0].onset_s:
                apply_fault(L.plant.fault, faults.pop(0))
            y = L.step()
            sps = np.array([l.setpoint for l in L.ctrl.loops])
            qmax = np.array([l.q_max for l in L.ctrl.loops])
            hist["t"].append(L.plant.t); hist["y"].append(y.copy()); hist["u"].append(L.u.copy())
            hist["TH"].append(L.plant.state.TH.copy()); hist["sp"].append(sps)
            if trace is None:
                rep = self.monitor.update(L.plant.t, y, L.u, sps, qmax)
                if rep is not None:
                    t_detect = L.plant.t
                    oracle = getattr(method, "oracle_localisation", True) and t_detect > ceil(self.spec.onset_s)
                    report = localise_oracle(rep, self.spec) if oracle else rep
                    snap = self.snapshot(hist)
                    w0 = time.perf_counter()
                    if hasattr(method, "decide_observed"):
                        last = len(hist["y"]) - 1
                        indices = range(max(last % 5, last - 100), last + 1, 5)
                        observations = ([hist["y"][i] for i in indices], [hist["u"][i] for i in indices])
                        trace = method.decide_observed(snap, report, L, observations)
                    else:
                        trace = method.decide(snap, report, L)
                    trace.decision_wall_s = round(time.perf_counter() - w0, 3)
                    lat = trace.decision_wall_s if self.latency_s is None else self.latency_s
                    if trace.applied_action is not None:
                        trace.selected_action = trace.applied_action
                        trace.applied_action = None
                        pending = (L.plant.t + lat, trace.selected_action)
            if pending is not None and pending[0] <= L.plant.t < steps:
                L.apply(pending[1])
                t_apply = L.plant.t
                trace.applied_action = pending[1]
                trace.tool_events.append({"tool": "plant_actuation", "time_s": t_apply,
                                          "action": pending[1].model_dump(mode="json")})
                pending = None
        if pending is not None:
            trace.tool_events.append({"tool": "actuation_expired", "scheduled_s": pending[0]})
        H = {k: np.array(v) for k, v in hist.items()}
        metrics = self.evaluate(H, trace, t_detect, t_apply)
        traj = {}
        if keep_traj:
            ds = slice(0, None, 5)
            traj = {"t": H["t"][ds].tolist(), "y": H["y"][ds].round(2).tolist(), "TH": H["TH"][ds].round(2).tolist(),
                    "u": H["u"][ds].round(1).tolist(), "sp": H["sp"][ds].round(2).tolist()}
        return EpisodeResult(sc.scenario_id, getattr(method, "name", "?"), metrics,
                             trace.model_dump(mode="json") if trace else {}, traj)

    # ------------------------------------------------------------------
    def shutdown_required(self) -> bool:
        """Oracle: is the plant unsafe even with every controllable heater off?"""
        if not np.isfinite(self.loop.plant.fault.stuck_value).any():
            return False
        sim = self.loop.plant.clone()
        sim.master_power = True  # judge the fault itself, not whatever interlock the method applied
        TH = sim.steady_state(np.zeros(sim.n))
        return bool(TH.max() > CONSTRAINTS["safety_limit_T"])

    def calibration_errors(self, trace, t_detect):
        event = next((event for event in trace.tool_events if event["tool"] == "adaptive_ekf"), None) if trace else None
        if event is None or t_detect is None:
            return {"gain_scale_rmse": None, "loss_scale_rmse": None, "bias_rmse": None}
        _, _, gain, loss, bias = np.split(np.asarray(event["mean"]), 5)
        p, f = self.loop.plant.p, FaultState.healthy(self.sc.n_zones)
        specs = sorted([self.spec, *(FaultSpec(**row) for row in self.sc.secondary_faults)], key=lambda s: s.onset_s)
        for spec in specs:
            if ceil(spec.onset_s) < t_detect:
                apply_fault(f, spec)
        return {
            "gain_scale_rmse": float(np.sqrt(np.mean((gain * event["fault_gain"] - p.alpha * f.alpha_scale / self.nominal.alpha)**2))),
            "loss_scale_rmse": float(np.sqrt(np.mean((loss * event["fault_loss"] -
                                                      p.U * f.U_scale * f.global_loss_scale / self.nominal.U)**2))),
            "bias_rmse": float(np.sqrt(np.mean((bias - f.sensor_bias)**2))),
        }

    def evaluate(self, H: dict, trace: DecisionTrace | None, t_detect, t_apply) -> dict:
        band = CONSTRAINTS["regulation_band_degC"]
        t = H["t"]
        onset = ceil(self.spec.onset_s)
        first_fault = min([onset, *(ceil(f["onset_s"]) for f in self.sc.secondary_faults)])
        lost = set(np.flatnonzero(np.isfinite(self.loop.plant.fault.stuck_value)))
        post = t > (t_apply if t_apply is not None else first_fault)
        after_onset = t > first_fault
        TH = H["TH"]
        if not np.isfinite(TH).all():
            raise ValueError("The true plant produced non-finite temperatures.")
        post_safety = thermal_safety(TH[post])
        all_safety = thermal_safety(TH[after_onset])
        pre_safety = thermal_safety(TH[after_onset & ~post])
        viol_post = post_safety.violation if post_safety else None
        tail = post & (t > (t[-1] - 600))
        sp_final = H["sp"][-1]
        shutdown = bool(t_apply is not None and trace and trace.applied_action and trace.applied_action.shutdown)
        healthy = [z for z in range(self.sc.n_zones) if z not in lost]
        tracking_zones = healthy or list(range(self.sc.n_zones))
        err = np.abs(TH[tail][:, tracking_zones] - sp_final[tracking_zones]).mean(axis=0) if tail.any() else []
        regulated = bool(len(err) and (err <= band).all()) and not shutdown
        sd_req = self.shutdown_required()
        sp_nom = np.array(self.sc.setpoints)
        retention = 0.0 if shutdown else float(np.mean(sp_final[tracking_zones] / sp_nom[tracking_zones]))
        iae = float(np.abs(TH[post][:, tracking_zones] - H["sp"][post][:, tracking_zones]).sum()) if post.any() else None
        plant_success = viol_post is False and ((shutdown and sd_req) or (regulated and not sd_req))
        agent_success = bool(t_apply is not None and trace and trace.applied_action is not None and not trace.used_fallback)
        validated_action = bool(t_apply is not None and trace and trace.validated_action)
        llm = trace.llm_calls if trace else []
        repairs = [event for event in trace.tool_events if event["tool"] == "bounded_de_repair"] if trace else []
        return {
            "detected": t_detect is not None,
            "false_alarm": t_detect is not None and t_detect <= onset,
            "localisation_correct": bool(t_detect is not None and t_detect > onset and trace and trace.fault_report
                                         and (trace.fault_report.fault_kind, trace.fault_report.zone) ==
                                         (self.spec.kind, self.spec.zone)),
            "tool_events": len(trace.tool_events) if trace else 0,
            **self.calibration_errors(trace, t_detect),
            "detect_delay_s": None if t_detect is None else round(t_detect - onset, 1),
            "action_applied": t_apply is not None,
            "actuation_s": t_apply,
            "validated_action": validated_action,
            "agent_success": agent_success,           # base-paper definition (validated LLM action, no fallback)
            "plant_success": bool(plant_success),     # judged on the true plant
            "plant_success_since_fault": bool(plant_success and all_safety and not all_safety.violation),
            "validated_but_failed": bool(agent_success and validated_action and not plant_success),
            "safety_violation_post": viol_post,
            "safety_violation_since_fault": all_safety.violation if all_safety else None,
            "max_T_post": round(post_safety.peak_degC, 2) if post_safety else None,
            "max_T_since_fault": round(all_safety.peak_degC, 2) if all_safety else None,
            "time_above_limit_s": all_safety.above_s if all_safety else None,
            "time_above_limit_post_s": post_safety.above_s if post_safety else None,
            "time_above_limit_before_actuation_s": pre_safety.above_s if pre_safety else 0.,
            "regulated": regulated,
            "tracking_err_tail": [round(float(e), 3) for e in err],
            "shutdown": shutdown,
            "shutdown_required": sd_req,
            "setpoint_retention": round(retention, 3),
            "iae_post": round(iae, 1) if iae is not None else None,
            "reprompts": trace.reprompts if trace else 0,
            "repair_attempts": len(repairs),
            "repairs_validated": sum(event["passed"] for event in repairs),
            "used_fallback": bool(trace and trace.used_fallback),
            "llm_calls": len(llm),
            "model_reply_failures": sum(not c.ok for c in llm),
            "provider_attempts": sum(c.api_attempts for c in llm),
            "missing_usage_calls": sum(c.api_attempts > 0 and not c.usage_reported for c in llm),
            "tokens_in": int(sum(c.tokens_in for c in llm)),
            "tokens_out": int(sum(c.tokens_out for c in llm)),
            "llm_latency_s": round(float(sum(c.latency_s for c in llm)), 2),
            "api_latency_s": round(float(sum(c.api_latency_s for c in llm)), 3),
            "decision_wall_s": trace.decision_wall_s if trace else 0.0,
        }
