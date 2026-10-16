"""Evaluation suite generation (fault x plant size x mismatch x seed)."""
from __future__ import annotations

import itertools
import json
import zlib
from dataclasses import asdict
from pathlib import Path

import numpy as np

from ..env.episode import Scenario
from ..env.faults import FAULT_TYPES, sample_fault

PLANTS = {2: [50.0, 45.0], 4: [50.0, 45.0, 50.0, 45.0]}


def make_suite(name: str, mismatch_levels=(0.0, 0.1, 0.2, 0.3), seeds=(0, 1, 2), zones=(2, 4),
               faults=tuple(FAULT_TYPES), noise_std: float = 0.15) -> list[Scenario]:
    out = []
    for n, kind, mm, seed in itertools.product(zones, faults, mismatch_levels, seeds):
        rng = np.random.default_rng(zlib.crc32(f"{n}-{kind}-{seed}".encode()))  # same fault across mismatch levels
        onset = float(rng.integers(1500, 1801))
        spec = sample_fault(rng, kind, n, onset)
        sid = f"{name}-z{n}-{kind}-mm{int(mm*100):02d}-s{seed}"
        out.append(Scenario(sid, n, PLANTS[n], asdict(spec), mm, noise_std if mm > 0 else 0.05, 1000 * seed + n))
    return out


def save_suite(scenarios: list[Scenario], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    rows = [json.dumps(asdict(s), separators=(", ", ": ")) for s in scenarios]  # one scenario per line
    Path(path).write_text("[\n" + ",\n".join(rows) + "\n]\n")


def load_suite(path: str | Path) -> list[Scenario]:
    return [Scenario(**d) for d in json.loads(Path(path).read_text())]
