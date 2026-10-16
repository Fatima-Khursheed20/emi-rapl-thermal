"""Run the Phase-1 evaluation suite.

Examples
--------
# offline (no API key): non-LLM baselines + pipeline check with the scripted client
python scripts/run_eval.py --methods no_recovery rule_table de_retune --run phase1_nonllm

# base-paper agent with Gemini free tier (needs GEMINI_API_KEY in .env)
python scripts/run_eval.py --methods single_llm base_agent_matched base_agent_nominal \
    --provider gemini --model gemini-2.5-flash --run phase1_gemini --limit 20
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

from emirapl.eval.runner import METHODS, aggregate, run  # noqa: E402
from emirapl.eval.suite import load_suite, make_suite, save_suite  # noqa: E402
from emirapl.llm.client import make_llm  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default=str(ROOT / "configs" / "suites" / "phase1_suite.json"))
    ap.add_argument("--methods", nargs="+", default=["no_recovery", "rule_table"], choices=METHODS)
    ap.add_argument("--provider", default="scripted", choices=["scripted", "gemini", "groq", "ollama", "openai"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--run", default="phase1")
    ap.add_argument("--limit", type=int, default=None, help="only the first N scenarios")
    ap.add_argument("--filter", default=None, help="substring filter on scenario_id, e.g. 'z2-' or 'mm20'")
    ap.add_argument("--latency", default="30", help="seconds of plant time per decision, or 'measured'")
    ap.add_argument("--traj", action="store_true", help="store downsampled trajectories in episodes.jsonl")
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    load_dotenv(ROOT / ".env")

    suite_path = Path(args.suite)
    if not suite_path.exists():
        save_suite(make_suite("p1"), suite_path)
        print(f"generated suite -> {suite_path}")
    scenarios = load_suite(suite_path)
    if args.filter:
        scenarios = [s for s in scenarios if args.filter in s.scenario_id]
    if args.limit:
        scenarios = scenarios[: args.limit]
    llm = make_llm(args.provider, args.model, temperature=args.temperature) if args.provider != "scripted" else make_llm("scripted")
    latency = None if args.latency == "measured" else float(args.latency)
    out = ROOT / "results" / args.run
    print(f"{len(scenarios)} scenarios x {len(args.methods)} methods -> {out}  (llm={getattr(llm, 'name', '-')})")
    df = run(scenarios, args.methods, llm, out, latency_s=latency, keep_traj=args.traj)
    agg = aggregate(df)
    agg.to_csv(out / "aggregate_by_method.csv")
    aggregate(df, by=("method", "fault")).to_csv(out / "aggregate_by_method_fault.csv")
    aggregate(df, by=("method", "mismatch")).to_csv(out / "aggregate_by_method_mismatch.csv")
    print(agg.to_string())


if __name__ == "__main__":
    main()
