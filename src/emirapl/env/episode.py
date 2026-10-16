"""One evaluation episode: warm-up, fault injection, detection, recovery decision, evaluation.

Timeline (s): 0 ---- warm-up / steady operation ---- onset (fault) -- detect -- decide
(+latency) -- apply action ---------------------------------- t_end.
All success metrics are computed on the hidden TRUE plant state, never on the twin.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

import numpy as np

from ..agents.monitor import ResidualMonitor, localise_oracle
from ..contracts import DecisionTrace, FaultReport, Snapshot
from ..control.pid import MultiZoneController, PIDGains
from ..env.faults import FaultSpec, apply_fault
from ..knowledge import CONSTRAINTS
from .closed_loop import ClosedLoop
from .thermal import ThermalParams, ThermalPlant

EXCURSION_TOL_DEGC = 0.5  # a post-action overshoot above the limit by more than this is a violation
EXCURSION_TOL_S = 60.0  # ...as is spending more than this long above the limit after the action

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

    def fault_spec(self) -> FaultSpec:
        return FaultSpec(**self.fault)


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
        steps = int(sc.t_end_s)
        for k in range(steps):
            t = L.plant.t
            if t >= self.spec.onset_s and not getattr(self, "_fault_on", False):
                apply_fault(L.plant.fault, self.spec)
                self._fault_on = True
            y = L.step()
            sps = np.array([l.setpoint for l in L.ctrl.loops])
            qmax = np.array([l.q_max for l in L.ctrl.loops])
            hist["t"].append(L.plant.t); hist["y"].append(y.copy()); hist["u"].append(L.u.copy())
            hist["TH"].append(L.plant.state.TH.copy()); hist["sp"].append(sps)
            if trace is None:
                rep = self.monitor.update(L.plant.t, y, L.u, sps, qmax)
                if rep is not None:
                    t_detect = L.plant.t
                    report = localise_oracle(rep, self.spec)
                    snap = self.snapshot(hist)
                    w0 = time.time()
                    trace = method.decide(snap, report, L)
                    trace.decision_wall_s = round(time.time() - w0, 3)
                    lat = trace.decision_wall_s if self.latency_s is None else self.latency_s
                    if trace.applied_action is not None:
                        pending = (L.plant.t + lat, trace.applied_action)
            if pending is not None and L.plant.t >= pending[0]:
                L.apply(pending[1])
                t_apply = L.plant.t
                pending = None
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
        if self.spec.kind != "actuator_stuck_high":
            return False
        sim = self.loop.plant.clone()
        TH = sim.steady_state(np.zeros(sim.n))
        return bool(TH.max() > CONSTRAINTS["safety_limit_T"])

    def evaluate(self, H: dict, trace: DecisionTrace | None, t_detect, t_apply) -> dict:
        limit, band = CONSTRAINTS["safety_limit_T"], CONSTRAINTS["regulation_band_degC"]
        t = H["t"]
        onset = self.spec.onset_s
        lost = {self.spec.zone} if self.spec.kind.startswith("actuator_stuck") else set()
        post = t >= (t_apply if t_apply is not None else onset)
        after_onset = t >= onset
        TH = H["TH"]
        max_post = float(TH[post].max()) if post.any() else float("nan")
        time_above = float((TH[after_onset] > limit).any(axis=1).sum())
        time_above_post = float((TH[post] > limit).any(axis=1).sum())
        # excursion tolerance: thermal inertia after a (correct) action may overshoot briefly
        viol_post = bool(max_post > limit + EXCURSION_TOL_DEGC or time_above_post > EXCURSION_TOL_S)
        tail = t >= (t[-1] - 600)
        sp_final = H["sp"][-1]
        shutdown = bool(trace and trace.applied_action and trace.applied_action.shutdown)
        healthy = [z for z in range(self.sc.n_zones) if z not in lost]
        err = np.abs(TH[tail][:, healthy] - sp_final[healthy]).mean(axis=0)
        regulated = bool((err <= band).all()) and not shutdown
        sd_req = self.shutdown_required()
        sp_nom = np.array(self.sc.setpoints)
        retention = 0.0 if shutdown else float(np.mean(sp_final[healthy] / sp_nom[healthy]))
        iae = float(np.abs(TH[post][:, healthy] - H["sp"][post][:, healthy]).sum()) if post.any() else float("nan")
        plant_success = (not viol_post) and ((shutdown and sd_req) or (regulated and not sd_req))
        agent_success = bool(trace and trace.applied_action is not None and not trace.used_fallback)
        llm = trace.llm_calls if trace else []
        return {
            "detected": t_detect is not None,
            "detect_delay_s": None if t_detect is None else round(t_detect - onset, 1),
            "action_applied": t_apply is not None,
            "agent_success": agent_success,           # base-paper definition (validated LLM action, no fallback)
            "plant_success": bool(plant_success),     # judged on the true plant
            "validated_but_failed": bool(agent_success and not plant_success),
            "safety_violation_post": viol_post,
            "max_T_post": round(max_post, 2),
            "time_above_limit_s": time_above,
            "time_above_limit_post_s": time_above_post,
            "regulated": regulated,
            "tracking_err_tail": [round(float(e), 3) for e in err],
            "shutdown": shutdown,
            "shutdown_required": sd_req,
            "setpoint_retention": round(retention, 3),
            "iae_post": round(iae, 1),
            "reprompts": trace.reprompts if trace else 0,
            "used_fallback": bool(trace and trace.used_fallback),
            "llm_calls": len(llm),
            "tokens_in": int(sum(c.tokens_in for c in llm)),
            "tokens_out": int(sum(c.tokens_out for c in llm)),
            "llm_latency_s": round(float(sum(c.latency_s for c in llm)), 2),
            "decision_wall_s": trace.decision_wall_s if trace else 0.0,
        }
