from __future__ import annotations

import argparse
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.policy_engine.service import Phase6PolicyService
from backend.app.modules.policy_engine.policy_loader import load_policy_from_file
from backend.app.modules.policy_engine.policy_validator import validate_policy_schema
from backend.app.modules.policy_engine.compatibility_checker import check_policy_population_compatibility


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 6: Policy Engine CLI for SOP Project (Tamil Nadu)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. run command
    run_parser = subparsers.add_parser("run", help="Execute a policy against a calibrated population.")
    run_parser.add_argument("--policy", required=True, help="Path to policy YAML/JSON configuration file.")
    run_parser.add_argument("--population", default=None, help="Path to population CSV file (defaults to Phase 5 handoff).")
    run_parser.add_argument("--output", default=None, help="Directory to save run artifacts.")
    run_parser.add_argument("--weight-column", default=None, help="Weight column to use for population impact estimates.")
    run_parser.add_argument("--run-id", default=None, help="Optional run identifier.")
    run_parser.add_argument("--seed", type=int, default=None, help="Random seed override for lottery selection.")
    run_parser.add_argument("--summary-only", action="store_true", help="Skip writing individual row-level result files.")

    # 2. validate-policy command
    val_parser = subparsers.add_parser("validate-policy", help="Validate policy schema without executing.")
    val_parser.add_argument("--policy", required=True, help="Path to policy configuration file.")

    # 3. check-compatibility command
    compat_parser = subparsers.add_parser("check-compatibility", help="Check policy variable compatibility against population.")
    compat_parser.add_argument("--policy", required=True, help="Path to policy configuration file.")
    compat_parser.add_argument("--population", default=None, help="Path to population CSV file.")

    args = parser.parse_args()
    service = Phase6PolicyService(project_root=ROOT)

    if args.command == "run":
        res = service.execute_policy(
            policy_path=args.policy,
            population_path=args.population,
            output_dir=args.output,
            weight_column=args.weight_column,
            run_id=args.run_id,
            seed_override=args.seed,
            summary_only=args.summary_only,
        )
        print(json.dumps(res, indent=2))
        if not res["success"]:
            sys.exit(1)

    elif args.command == "validate-policy":
        policy_def, _ = load_policy_from_file(args.policy)
        res = validate_policy_schema(policy_def)
        print(json.dumps(res, indent=2))
        if not res["valid"]:
            sys.exit(1)

    elif args.command == "check-compatibility":
        policy_def, _ = load_policy_from_file(args.policy)
        pop_records, _, _ = service._load_population_records(args.population)
        res = check_policy_population_compatibility(policy_def, pop_records)
        print(json.dumps(res, indent=2))
        if not res["compatible"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
