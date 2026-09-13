from __future__ import annotations

import argparse
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.monte_carlo.service import Phase7MonteCarloService
from backend.app.modules.monte_carlo.config_loader import load_simulation_config
from backend.app.modules.monte_carlo.config_validator import validate_simulation_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 7: Monte Carlo & Uncertainty Engine CLI (Tamil Nadu)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. run command
    run_parser = subparsers.add_parser("run", help="Run a Monte Carlo simulation experiment.")
    run_parser.add_argument("--config", required=True, help="Path to simulation YAML/JSON configuration file.")
    run_parser.add_argument("--iterations", type=int, default=None, help="Override number of iterations.")
    run_parser.add_argument("--seed", type=int, default=None, help="Override base random seed.")
    run_parser.add_argument("--output", default=None, help="Directory to save experiment artifacts.")
    run_parser.add_argument("--no-resume", action="store_true", help="Disable experiment resume and start fresh.")

    # 2. validate command
    val_parser = subparsers.add_parser("validate", help="Validate simulation configuration file.")
    val_parser.add_argument("--config", required=True, help="Path to simulation configuration file.")

    args = parser.parse_args()
    service = Phase7MonteCarloService(project_root=ROOT)

    if args.command == "run":
        res = service.run_experiment(
            config_path=args.config,
            output_dir=args.output,
            iterations_override=args.iterations,
            seed_override=args.seed,
            resume=not args.no_resume,
        )
        print(json.dumps(res, indent=2))
        if not res["success"]:
            sys.exit(1)

    elif args.command == "validate":
        config, _ = load_simulation_config(args.config)
        res = validate_simulation_config(config)
        print(json.dumps(res, indent=2))
        if not res["valid"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
