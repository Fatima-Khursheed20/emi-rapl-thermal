"""Shared numerical kernels for the simulator and deterministic twin rollouts."""
import numpy as np

try:
    from numba import njit
except ImportError:
    ACCELERATED = False

    def njit(*, cache):
        return lambda function: function
else:
    ACCELERATED = True

SIGMA = 5.67e-8
KELVIN = 273.15


@njit(cache=True)
def derivatives(th, tc, power, loss, gain, lag, ambient, capacity, area, shared_area, emissivity):
    tk4 = (th + KELVIN) ** 4
    heat = loss * area * (ambient - th) + emissivity * SIGMA * area * ((ambient + KELVIN) ** 4 - tk4)
    for i in range(len(th) - 1):
        exchange = ((loss[i] + loss[i + 1]) * .5 * shared_area * (th[i + 1] - th[i])
                    + emissivity * SIGMA * shared_area * (tk4[i + 1] - tk4[i]))
        heat[i] += exchange
        heat[i + 1] -= exchange
    return (heat + gain * power) / capacity, (th - tc) / lag


@njit(cache=True)
def thermal_step(th, tc, power, dt, physics):
    h1, c1 = derivatives(th, tc, power, *physics)
    h2, c2 = derivatives(th + dt / 2 * h1, tc + dt / 2 * c1, power, *physics)
    h3, c3 = derivatives(th + dt / 2 * h2, tc + dt / 2 * c2, power, *physics)
    h4, c4 = derivatives(th + dt * h3, tc + dt * c3, power, *physics)
    return th + dt / 6 * (h1 + 2 * h2 + 2 * h3 + h4), tc + dt / 6 * (c1 + 2 * c2 + 2 * c3 + c4)


@njit(cache=True)
def constant_temperature(th, tc, power, dt, physics, samples):
    for _ in range(samples):
        th, tc = thermal_step(th, tc, power, dt, physics)
    return th


@njit(cache=True)
def open_loop(th, tc, commands, dt, physics, stuck, sensor_bias):
    """Replay measured commands with fixed parameters and fault effects."""
    measurements = np.empty_like(commands)
    for i in range(len(commands)):
        power = np.where(np.isnan(stuck), np.clip(commands[i], 0., 100.), np.clip(stuck, 0., 100.))
        th, tc = thermal_step(th, tc, power, dt, physics)
        measurements[i] = np.round(tc + sensor_bias, 2)
    return th, tc, measurements


@njit(cache=True)
def closed_loop(th, tc, y, dt, physics, stuck, sensor_bias, initial, changed, integral, previous,
                power_before, power_after, hold, steps):
    """Advance PI state and a noiseless thermal plant across one settings change."""
    temperatures = np.empty((steps, len(th)))
    measurements = np.empty_like(temperatures)
    outputs = np.empty_like(temperatures)
    for i in range(steps):
        settings = initial if i < hold else changed
        power_on = power_before if i < hold else power_after
        power = np.zeros(len(th))
        for zone in range(len(th)):
            sp, kc, ti, td, cap, bias, offset = settings[zone]
            measurement = y[zone] + offset
            error = sp - measurement
            slope = 0. if np.isnan(previous[zone]) else -(measurement - previous[zone]) / dt
            previous[zone] = measurement
            unsaturated = bias + kc * error + kc / ti * integral[zone] + kc * td * slope
            command = min(cap, max(0., unsaturated))
            if not ((unsaturated > cap and error > 0) or (unsaturated < 0 and error < 0)):
                integral[zone] += error * dt
            if power_on:
                power[zone] = command if np.isnan(stuck[zone]) else min(100., max(0., stuck[zone]))
        th, tc = thermal_step(th, tc, power, dt, physics)
        y = np.round(tc + sensor_bias, 2)
        temperatures[i] = th
        measurements[i] = y
        outputs[i] = power
    return temperatures, measurements, outputs
