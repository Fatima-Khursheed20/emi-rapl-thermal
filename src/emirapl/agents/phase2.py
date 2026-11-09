"""Phase 2 supervisor. Calibration, repair and diagnosis can be disabled independently."""
import json

import numpy as np
from scipy.optimize import differential_evolution

from .pipeline import BasePaperAgent, _lost_zones
from ..contracts import Mode, RecoveryAction, Violation
from ..env.faults import FAULT_TYPES, NOMINAL_MAGNITUDE, FaultSpec, apply_fault
from ..env.thermal import FaultState, PlantState
from ..knowledge import CONSTRAINTS
from ..llm.client import extract_json
from ..safety import thermal_safety
from ..tools.calibration import estimate, replay
from ..tools.twin import DigitalTwin
from ..tools.validator import Validator


class CalibratedTwin(DigitalTwin):
    def __init__(self, nominal, fitted, fault):
        super().__init__("nominal", nominal)
        self.fitted = fitted
        self.fault = fault

    def member(self, true_loop, report, state):
        loop = super().build(true_loop, report)
        th, tc, gain, loss, bias = np.split(state, 5)
        loop.plant.p.alpha *= np.clip(gain, .5, 1.5)
        loop.plant.p.U *= np.clip(loss, .5, 1.5)
        loop.plant.state = PlantState(th.copy(), tc.copy())
        loop.plant.fault = self.fault.copy()
        loop.plant.fault.sensor_bias = np.where(self.fault.sensor_bias != 0, np.clip(bias, -20, 20), 0)
        loop.y = loop.plant.measure()
        return loop

    def build(self, true_loop, report):
        return self.member(true_loop, report, self.fitted.mean)


class EnsembleValidator(Validator):
    def validate(self, action, true_loop, report, lost_zones=None):
        central = super().validate(action, true_loop, report, lost_zones)
        if not central.passed:
            return central
        fitted = self.twin.fitted
        rng = np.random.default_rng(42)
        members = rng.multivariate_normal(fitted.mean, fitted.covariance, size=4)
        predictions = [central.predicted.copy()]
        for member in members:
            validator = Validator(DigitalTwin("matched", self.twin.nominal), self.sp_nom,
                                  self.horizon_s, self.window, self.delay_s)
            trial = validator.validate(action, self.twin.member(true_loop, report, member), report, lost_zones)
            predictions.append(trial.predicted)
            central.violations.extend(trial.violations)
        central.predicted["ensemble"] = predictions
        if all("post_action_safety" in prediction for prediction in predictions):
            peaks = [prediction["post_action_safety"]["peak_degC"] for prediction in predictions]
            p95 = float(np.quantile(peaks, .95))
            central.predicted["p95_max_T"] = p95
            limit = CONSTRAINTS["safety_limit_T"]
            if p95 > limit:
                central.violations.append(Violation(check="ensemble_p95_limit", value=p95, limit=limit,
                                                    message=f"ensemble p95 peak {p95:.2f} exceeds {limit:g} degC"))
        else:
            central.predicted["p95_max_T"] = None
        central.passed = not central.violations
        if not central.passed:
            central.responsible = "action"
        return central


class Phase2Agent(BasePaperAgent):
    def __init__(self, *args, calibration=True, repair=True, diagnosis=True, approval=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.calibration = calibration
        self.repair = repair
        self.diagnosis = diagnosis
        self.oracle_localisation = False
        self.approval = approval

    def decide_observed(self, snap, report, loop, observations):
        y, u = observations
        ranked = replay(self.validator.twin.nominal, y, u) if self.diagnosis else []
        call = None
        chosen = ranked[0] if ranked else None
        if self.diagnosis and chosen is not None:
            # Present the best fit for each kind/zone so alternatives are distinct.
            hypotheses = []
            seen = set()
            for candidate in ranked:
                key = candidate["kind"], candidate["zone"]
                if key not in seen:
                    seen.add(key)
                    hypotheses.append(candidate)
            options = hypotheses[:5]
            healthy = next(c for c in hypotheses if c["kind"] is None)
            if healthy not in options:
                options[-1] = healthy
            messages = [{"role": "system", "content": "Select a zero-based candidate index. Return JSON with index and a short evidence summary. A null kind is the healthy counter-hypothesis. Use replay MSE and measured residuals."},
                        {"role": "user", "content": json.dumps({"candidates": options, "symptoms": report.symptoms,
                                                               "residuals": snap.residuals})}]
            response = self.llm.complete("diagnosis", messages, {"snapshot": snap, "fault_report": report})
            call = response.record
            try:
                index = extract_json(response.text)["index"] if call.ok else None
                if type(index) is int and 0 <= index < len(options):
                    proposal = options[index]
                    # Check the proposed diagnosis against the strongest counter-hypothesis.
                    if (proposal["mse"] <= chosen["mse"] * 1.1 + .02
                            and (proposal["kind"] is None or proposal["mse"] < healthy["mse"])):
                        chosen = proposal
            except (TypeError, KeyError, ValueError):
                pass
            report = report.model_copy(update={"fault_kind": chosen["kind"], "zone": chosen["zone"],
                                                "fault_class": FAULT_TYPES.get(chosen["kind"], "unknown"),
                                                "localisation_source": "diagnosis"})

        validator = self.validator
        fitted = None
        try:
            if self.calibration and len(y) >= 2:
                fault = FaultState.healthy(snap.n_zones)
                onset = 0
                if report.fault_kind:
                    compatible = next((c for c in ranked if (c["kind"], c["zone"]) ==
                                       (report.fault_kind, report.zone)), None)
                    magnitude = compatible["magnitude"] if compatible else NOMINAL_MAGNITUDE[report.fault_kind]
                    onset = compatible["onset"] if compatible else 0
                    apply_fault(fault, FaultSpec(report.fault_kind, report.zone, magnitude, 0))
                fitted = estimate(validator.twin.nominal, y, u, fault, onset)
                twin = CalibratedTwin(validator.twin.nominal, fitted, fault)
                self.validator = EnsembleValidator(twin, validator.sp_nom, validator.horizon_s,
                                                   validator.window, validator.delay_s)
            trace = super().decide(snap, report, loop)
            if self.diagnosis:
                trace.tool_events.insert(0, {"tool": "fault_replay", "samples": len(y), "candidates": ranked,
                                             "selected": report.model_dump(mode="json")})
            if fitted is not None:
                trace.tool_events.append({"tool": "adaptive_ekf", "mean": fitted.mean.tolist(),
                                          "variance": np.diag(fitted.covariance).tolist(),
                                          "fault_gain": fault.alpha_scale.tolist(),
                                          "fault_loss": (fault.U_scale * fault.global_loss_scale).tolist(),
                                          "innovation_rms": fitted.innovation_rms})
            elif self.calibration:
                trace.notes.append("Calibration skipped because the observation window has fewer than two samples.")
            if call:
                trace.llm_calls.insert(0, call)
                trace.tool_events.append({"tool": "diagnosis_selection", "messages": messages, "output": response.text})
            if trace.applied_action is not None:
                action = trace.applied_action
                verified = self.validator.validate(action, loop, report, _lost_zones(report)) if trace.used_fallback else None
                if verified is not None:
                    trace.validations.append(verified)
                    if not verified.passed:
                        trace.applied_action = self.emergency_shutdown(loop, report, trace)
                    else:
                        trace.validated_action = True
                trace.selected_action = trace.applied_action
                if trace.applied_action is not None and self.approval:
                    allowed = self.approval(trace.applied_action)
                    trace.tool_events.append({"tool": "operator_approval", "allowed": allowed,
                                              "action": trace.applied_action.model_dump(mode="json")})
                    if not allowed:
                        trace.applied_action = None
            return trace
        finally:
            self.validator = validator

    def emergency_shutdown(self, loop, report, trace):
        """Separate an emergency power cut from production-mode shutdown justification."""
        twin = self.validator.twin
        action = RecoveryAction(mode=Mode.SAFE_SHUTDOWN, shutdown=True,
                                rationale="emergency power cut after recovery options failed")
        models = [twin.build(loop, report)]
        if isinstance(twin, CalibratedTwin):
            samples = np.random.default_rng(42).multivariate_normal(twin.fitted.mean, twin.fitted.covariance, size=4)
            models.extend(twin.member(loop, report, sample) for sample in samples)
        horizon, delay = self.validator.horizon_s, self.validator.delay_s
        # Check the reported stuck-heater hypothesis at its maximum physical power.
        # This only affects the emergency branch after ordinary recovery fails.
        if report.fault_kind == "actuator_stuck_high" and report.zone is not None:
            worst = models[0].clone()
            worst.plant.fault.stuck_value[report.zone] = 100.
            models.append(worst)

        def safety(model, candidate):
            rollout = DigitalTwin.rollout(model, candidate, horizon, delay)
            return thermal_safety(rollout.TH[rollout.hold:], model.plant.dt)

        holds = [safety(model, None) for model in models]
        cuts = [safety(model, action) for model in models]
        finite = all(s is not None and s.valid for s in holds + cuts)
        allowed = (finite and any(hold.violation for hold in holds) and all(
            (not cut.violation or (cut.peak_degC <= hold.peak_degC and cut.above_s <= hold.above_s
                                   and (cut.peak_degC < hold.peak_degC or cut.above_s < hold.above_s)))
            for cut, hold in zip(cuts, holds)))
        trace.tool_events.append({"tool": "emergency_shutdown",
                                  "hold": [s.as_dict() if s else None for s in holds],
                                  "cut": [s.as_dict() if s else None for s in cuts],
                                  "mitigation_selected": allowed,
                                  "cut_within_tolerance": bool(finite and not any(s.violation for s in cuts))})
        return action if allowed else None

    def refine(self, action, result, loop, report, lost, trace):
        if not self.repair or result.passed or action.shutdown or result.responsible != "action":
            return action, result
        structural = self.validator.structural(action, report, loop.n)
        repairable = {"setpoint_range", "max_derate"} if action.mode == Mode.DERATE else {"offset_range"}
        if any(v.check not in repairable for v in structural):
            return action, result
        twin = self.validator.twin.build(loop, report)
        reachable = twin.plant.steady_state(np.full(loop.n, 100.), iters=700)
        zones = sorted({v.zone for v in result.violations if v.zone is not None and 0 <= v.zone < loop.n})
        trace.tool_events.append({"tool": "feasible_bounds", "full_power_temperatures": reachable.tolist()})
        if action.mode == Mode.RETUNE and any(reachable[z] < self.validator.sp_nom[z] - 2 for z in zones):
            result.responsible = "planner"
        fields = []
        if action.mode == Mode.DERATE:
            fields = [("setpoints", z, (max(30., self.validator.sp_nom[z] - 15), self.validator.sp_nom[z]),
                       action.setpoints.get(z, self.validator.sp_nom[z])) for z in zones]
        elif action.mode == Mode.SENSOR_CORRECTION:
            fields = [("sensor_offset", z, (-20., 20.), action.sensor_offset.get(z, 0.)) for z in zones]
        if not fields:
            return action, result

        def candidate(values):
            repaired = action.model_copy(deep=True)
            for (field, zone, _, _), value in zip(fields, values):
                getattr(repaired, field)[zone] = float(value)
            return repaired

        def objective(values):
            proposal = candidate(values)
            rollout = DigitalTwin.rollout(twin, proposal, 360., self.validator.delay_s)
            thermal = rollout.TH[rollout.hold:]
            return float(10 * np.maximum(thermal - 60., 0).max() +
                         np.abs(thermal[-60:] - rollout.setpoints).mean() +
                         .015 * np.abs(rollout.setpoints - self.validator.sp_nom).sum())

        bounds = [field[2] for field in fields]
        start = np.clip([field[3] for field in fields], *np.asarray(bounds).T)
        opt = differential_evolution(objective, bounds, x0=start, seed=42, maxiter=1, popsize=3, polish=False)
        proposal = candidate(opt.x)
        verified = self.validator.validate(proposal, loop, report, lost)
        trace.tool_events.append({"tool": "bounded_de_repair", "objective": float(opt.fun), "evaluations": opt.nfev,
                                  "proposal": proposal.model_dump(mode="json"), "passed": verified.passed})
        trace.validations.append(verified)
        if verified.passed:
            trace.actions.append(proposal)
            return proposal, verified
        return action, result

    def feedback(self, violations, trace):
        if self.repair:
            bounds = next((e for e in reversed(trace.tool_events) if e["tool"] == "feasible_bounds"), None)
            if bounds:
                violations.append(Violation(check="physics_bounds", message=json.dumps(bounds)))
        return violations
