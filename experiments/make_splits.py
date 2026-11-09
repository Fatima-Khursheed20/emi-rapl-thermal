"""Generate the locked Phase 2 splits. Fault and plant seeds do not cross splits."""
from dataclasses import replace
from pathlib import Path

from emirapl.eval.suite import make_suite, save_suite

ROOT = Path(__file__).resolve().parents[1] / "configs" / "suites"

dev = make_suite("p2-dev", seeds=(10,), mismatch_levels=(0.1, 0.3))
test = [replace(s, scenario_id=f"{s.scenario_id}-n{i}", noise_std=noise)
        for s in make_suite("p2-test", seeds=range(20, 25))
        for i, noise in enumerate((0.05, 0.15))]
llm = [s for s in test if "-s20-" in s.scenario_id and s.mismatch in (0., .3)
       and s.scenario_id.endswith(f"n{int(s.mismatch > 0)}")]
# A balanced offline screening slice. This is disjoint from the confirmatory test.
screen = make_suite("p2-screen", seeds=(30,), mismatch_levels=(0., .3))
held = []
for s in make_suite("p2-stress", seeds=(40,), mismatch_levels=(0.3,)):
    fault = {**s.fault, "magnitude": {
        "heater_degradation": .55, "sensor_bias": -15., "heat_loss_increase": 3.7,
        "local_insulation_loss": 5.2, "actuator_stuck_high": 82.,
    }[s.fault["kind"]]}
    held.append(replace(s, scenario_id=s.scenario_id + "-unseen", fault=fault))
    if fault["kind"] != "sensor_bias":
        secondary = {"kind": "sensor_bias", "zone": (fault["zone"] + 1) % s.n_zones,
                     "magnitude": -6., "onset_s": fault["onset_s"]}
        held.append(replace(s, scenario_id=s.scenario_id + "-compound", fault=fault, secondary_faults=[secondary]))
for name, suite in (("dev", dev), ("test", test), ("stress", held), ("screen", screen), ("llm", llm)):
    save_suite(suite, ROOT / f"phase2_{name}.json")
