"""Interactive simulator run with an operator approval gate and saved decision trace."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from emirapl.env.episode import Episode
from emirapl.eval.checkpoints import write_json
from emirapl.eval.runner import build_method
from emirapl.eval.suite import load_suite
from emirapl.llm.client import PROVIDERS, ProviderError, make_llm

ROOT = Path(__file__).resolve().parents[1]


def approve(action):
    print(action.model_dump_json(indent=2))
    try:
        return input("Apply this selected action to the simulator? [y/N] ").strip().lower() == "y"
    except EOFError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=ROOT / "configs/suites/phase2_dev.json")
    parser.add_argument("--scenario", type=int, default=0)
    parser.add_argument("--provider", choices=["scripted", *PROVIDERS], default="scripted")
    parser.add_argument("--model")
    parser.add_argument("--out", type=Path, default=Path("results/_demo.json"))
    args = parser.parse_args(argv)
    try:
        load_dotenv(ROOT / ".env")
        scenarios = load_suite(args.suite)
        if not 0 <= args.scenario < len(scenarios):
            raise ValueError(f"Scenario index must be between 0 and {len(scenarios) - 1}.")
        scenario = scenarios[args.scenario]
        agent = build_method("phase2_agent", scenario, make_llm(args.provider, args.model))
        agent.approval = approve
        result = Episode(scenario).run(agent)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.out, asdict(result))
    except (ValueError, TypeError, OSError, ProviderError) as exc:
        print(f"Demo stopped. {exc}")
        return 2
    print(json.dumps(result.metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
