"""Generate gap comparisons from a verified, complete Phase 2 run."""
import argparse
from itertools import product
from math import isfinite
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon

from emirapl.eval.checkpoints import (SCHEMA_VERSION, RunDataError, read_json, record_checksum,
                                      run_lock, sha256, write_json)


def fraction(frame, column):
    value = float(frame[column].mean())
    return value if isfinite(value) else None


def paired(frame, left, right):
    scope = frame[frame.method.isin((left, right))]
    if scope.method.nunique() != 2:
        return {}
    # Fault types, mismatch/noise variants and repeats share underlying plant
    # draws within a zone count and seed. Keep each block together.
    groups = ["n_zones", "seed"]
    keys = [*groups, "scenario_id", "repeat"]
    pair = scope.pivot(index=keys, columns="method", values="plant_success")
    if pair.isna().any().any():
        raise RunDataError(f"Unmatched outcomes for {left} vs {right}.")
    win = int((pair[left] & ~pair[right]).sum())
    loss = int((~pair[left] & pair[right]).sum())
    delta = (pair[left].astype(float) - pair[right].astype(float)).groupby(level=groups).mean().to_numpy()
    interval = None
    if len(delta) >= 5:
        rng = np.random.default_rng(42)
        boot = rng.choice(delta, size=(4000, len(delta)), replace=True).mean(axis=1)
        interval = np.quantile(boot, [.025, .975]).tolist()
    timing = scope.pivot(index=keys, columns="method", values="decision_wall_s")
    differences = (timing[left] - timing[right]).groupby(level=groups).mean()
    return {"pairs": len(pair), "scenario_blocks": len(delta), "wins": win, "losses": loss,
            "delta": float(delta.mean()), "ci95": interval,
            "mcnemar_p_independent_pairs": float(binomtest(win, win + loss).pvalue) if
            win + loss and len(pair) == len(delta) else None,
            "wilcoxon_latency_p": float(wilcoxon(differences).pvalue) if
            len(delta) >= 5 and differences.ne(0).any() else None}


def read_complete_run(out):
    manifest_path, summary_path = out / "manifest.json", out / "summary.csv"
    manifest = read_json(manifest_path)
    completion = read_json(out / "completion.json")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise RunDataError("These results predate the verified runner. Reproduce them in a fresh output folder.")
    expected = set(product(manifest["scenario_ids"], manifest["methods"], range(manifest["repeats"])))
    if (completion.get("status") != "complete" or not expected
            or completion.get("completed") != len(expected) or completion.get("expected") != len(expected)):
        raise RunDataError("The run is incomplete. Resume it before generating analysis.")
    if (completion.get("manifest_sha256") != sha256(manifest_path)
            or completion.get("summary_sha256") != sha256(summary_path)):
        raise RunDataError("The manifest or summary changed. Rerun the evaluation command to verify and rebuild it.")
    frame = pd.read_csv(summary_path)
    keys = ["scenario_id", "method", "repeat"]
    actual = set(frame[keys].itertuples(index=False, name=None))
    if actual != expected or len(frame) != len(expected):
        raise RunDataError("Summary must contain exactly one row per scenario, method and repeat.")
    for sid, method, repeat in sorted(expected):
        path = out / "episodes" / f"{sid}__{method}__{repeat}.json"
        try:
            record = read_json(path)
            checksum = record.pop("checksum", None)
            if ((record["scenario"]["scenario_id"], record["method"], record["repeat"]) != (sid, method, repeat)
                    or checksum != record_checksum(record)):
                raise ValueError("checkpoint identity or checksum mismatch")
        except (ValueError, OSError, AttributeError, KeyError, TypeError) as exc:
            raise RunDataError(f"Invalid source episode {path.name}. Rerun the evaluation to rebuild it.") from exc
    return manifest, frame


def gap_analysis(manifest, data):
    full = data[data.method == "phase2_agent"]
    nominal = data[data.method == "base_agent_nominal"]
    high_data = data[np.isclose(data.mismatch, .3)]
    high = high_data[high_data.method == "phase2_agent"]
    nominal_high = high_data[high_data.method == "base_agent_nominal"]
    full_latency = fraction(high, "decision_wall_s")
    nominal_latency = fraction(nominal_high, "decision_wall_s")
    full_reprompts = fraction(full, "reprompts")
    nominal_reprompts = fraction(nominal, "reprompts")
    valid_detect = full[full.detected & ~full.false_alarm]
    return {
        "scope": manifest,
        "analysis_code_sha256": sha256(Path(__file__).resolve()),
        "safety": {
            "full_plant_success_post_actuation": fraction(full, "plant_success"),
            "full_plant_success_since_fault": fraction(full, "plant_success_since_fault"),
            "full_post_actuation_violations": int(full.safety_violation_post.sum()),
            "full_since_fault_violations": int(full.safety_violation_since_fault.sum()),
        },
        "G1": {
            "full_validated_but_failed_at_30pct": fraction(high, "validated_but_failed"),
            "nominal_validated_but_failed_at_30pct": fraction(nominal_high, "validated_but_failed"),
            "full_vs_no_g1_at_30pct": paired(high_data, "phase2_agent", "phase2_agent_no_g1"),
            "full_vs_baseline_at_30pct": paired(high_data, "phase2_agent", "base_agent_nominal"),
            "full_mean_decision_seconds": full_latency,
            "baseline_mean_decision_seconds": nominal_latency,
            "decision_time_ratio": full_latency / nominal_latency if full_latency is not None and nominal_latency else None,
            "full_gain_scale_rmse_mean": fraction(full, "gain_scale_rmse"),
            "full_loss_scale_rmse_mean": fraction(full, "loss_scale_rmse"),
            "full_bias_rmse_mean": fraction(full, "bias_rmse"),
        },
        "G2": {
            "full_reprompt_recovery": fraction(full[full.reprompts > 0], "agent_success"),
            "baseline_reprompt_recovery": fraction(nominal[nominal.reprompts > 0], "agent_success"),
            "full_reprompt_episodes": int((full.reprompts > 0).sum()),
            "baseline_reprompt_episodes": int((nominal.reprompts > 0).sum()),
            "full_episodes_with_repair": int((full.repair_attempts > 0).sum()),
            "full_repair_attempts": int(full.repair_attempts.sum()),
            "full_repairs_validated": int(full.repairs_validated.sum()),
            "full_mean_reprompts": full_reprompts,
            "baseline_mean_reprompts": nominal_reprompts,
            "relative_reprompt_reduction": (1 - full_reprompts / nominal_reprompts)
            if full_reprompts is not None and nominal_reprompts else None,
            "paired_ablation": paired(data, "phase2_agent", "phase2_agent_no_g2"),
        },
        "G3": {
            "localisation_all_episodes": fraction(full, "localisation_correct"),
            "localisation_after_valid_detection": fraction(valid_detect, "localisation_correct"),
            "full_episodes": len(full),
            "full_valid_detection_episodes": len(valid_detect),
            "full_vs_oracle_matched": paired(data, "phase2_agent", "base_agent_matched"),
            "full_vs_oracle_nominal": paired(data, "phase2_agent", "base_agent_nominal"),
            "full_vs_unlocalised_baseline": paired(data, "phase2_agent", "base_agent_no_oracle"),
            "paired_symptoms_only_ablation": paired(data, "phase2_agent", "phase2_agent_no_g3"),
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    out = parser.parse_args(argv).run
    try:
        with run_lock(out):
            manifest, data = read_complete_run(out)
            if "phase2_agent" not in set(data.method):
                raise RunDataError("Gap analysis needs the full agent. Run --experiment all or E4 for comparison.")
            write_json(out / "gap_analysis.json", gap_analysis(manifest, data))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Analysis stopped. {exc}")
        return 2
    print(f"Verified analysis saved to {out / 'gap_analysis.json'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
