"""Measurement-only fault replay and joint thermal state/parameter estimation."""
from dataclasses import dataclass

import numpy as np

from ..env.faults import MAGNITUDE_RANGE, FaultSpec, apply_fault
from ..env.simulation import open_loop
from ..env.thermal import FaultState, PlantState, ThermalPlant


@dataclass
class Estimate:
    mean: np.ndarray
    covariance: np.ndarray
    innovation_rms: float


def replay(nominal, temperatures, commands):
    """Rank single-fault hypotheses using recent commanded inputs and measurements."""
    y, u = np.asarray(temperatures), np.asarray(commands)
    if len(y) < 2:
        return []
    candidates = [(None, None, 0.0)]
    for kind, limits in MAGNITUDE_RANGE.items():
        zones = [0] if kind == "heat_loss_increase" else range(nominal.n_zones)
        candidates.extend((kind, z, float(m)) for z in zones for m in np.linspace(*limits, 3))
    # Compare candidate changes against the healthy prediction over the same window.
    plant = ThermalPlant(nominal, dt=5)
    th, tc = y[0].copy(), y[0].copy()
    commands = np.ascontiguousarray(u[1:], dtype=float)
    healthy_physics = plant.physics()
    healthy_fault = plant.fault
    _, _, healthy = open_loop(th, tc, commands, plant.dt, healthy_physics,
                              healthy_fault.stuck_value, healthy_fault.sensor_bias)
    healthy_error = float(np.mean((y[1:] - healthy)**2))
    prefixes = {
        onset: open_loop(th, tc, commands[:onset], plant.dt, healthy_physics,
                         healthy_fault.stuck_value, healthy_fault.sensor_bias)[:2]
        for onset in range(0, len(commands), 3)
    }
    scores = []
    for kind, zone, magnitude in candidates:
        best = healthy_error
        onset_best = 0
        if kind:
            best = float("inf")
            plant.fault = FaultState.healthy(nominal.n_zones)
            apply_fault(plant.fault, FaultSpec(kind, zone, magnitude, 0))
            physics = plant.physics()
            for onset, (prefix_th, prefix_tc) in prefixes.items():
                _, _, suffix = open_loop(prefix_th, prefix_tc, commands[onset:], plant.dt, physics,
                                         plant.fault.stuck_value, plant.fault.sensor_bias)
                predictions = np.vstack((healthy[:onset], suffix))
                loss = float(np.mean((y[1:] - predictions)**2))
                if loss < best:
                    best, onset_best = loss, onset
        scores.append(dict(kind=kind, zone=zone, magnitude=magnitude, mse=best, onset=onset_best))
    return sorted(scores, key=lambda item: item["mse"])


def estimate(nominal, temperatures, commands, fault, onset):
    """Joint EKF for heater/sensor temperatures, effective gain/loss and sensor bias."""
    y, u = np.asarray(temperatures), np.asarray(commands)
    n = nominal.n_zones
    model = ThermalPlant(nominal.copy(), dt=5)
    model.fault = fault.copy()
    x = np.r_[y[0], y[0], np.ones(2*n), np.zeros(n)]
    P = np.diag(np.repeat([4., 2., .04, .04, .25], n))
    Q = np.diag(np.repeat([.03, .01, .0002, .0002, .0001], n))
    H = np.zeros((n, 5*n))
    H[:, n:2*n] = H[:, 4*n:] = np.eye(n)
    noise = np.full(n, .04)
    residuals = []

    def transition(state, command):
        th, tc, gain, loss, bias = np.split(state, 5)
        model.p.alpha = nominal.alpha * gain
        model.p.U = nominal.U * loss
        model.state = PlantState(th.copy(), tc.copy())
        model.step(command)
        return np.r_[model.state.TH, model.state.TC, gain, loss, bias]

    healthy = FaultState.healthy(n)
    eye = np.eye(5*n)
    for i, (measurement, command) in enumerate(zip(y[1:], u[1:])):
        model.fault = fault if i >= onset else healthy
        if i == onset:
            x[4*n:] = fault.sensor_bias

        prediction = transition(x, command)
        F = np.column_stack([(transition(x + delta * 1e-4, command) - prediction) / 1e-4 for delta in eye])
        P = F @ P @ F.T + Q
        innovation = measurement - H @ prediction
        residuals.append(innovation)
        R = np.diag(noise)
        K = np.linalg.solve(H @ P @ H.T + R, H @ P).T
        x = prediction + K @ innovation
        x[2*n:4*n] = np.clip(x[2*n:4*n], .5, 1.5)
        x[4*n:] = np.clip(x[4*n:], -20, 20)
        x[4*n:][model.fault.sensor_bias == 0] = 0
        A = eye - K @ H
        P = A @ P @ A.T + K @ R @ K.T
        noise = np.clip(.95 * noise + .05 * innovation**2, .0025, 1.)
    return Estimate(x, P, float(np.sqrt(np.mean(np.square(residuals)))))
