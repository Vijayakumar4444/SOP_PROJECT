"""
CLI interface for Phase 8 Recommendation Engine.
"""

import sys
import argparse
from typing import List
from .service import Phase8RecommendationService
from .config_loader import RecommendationConfigLoader
from .config_validator import RecommendationConfigValidator
from .result_loader import ExperimentResultLoader
from .compatibility_validator import CompatibilityValidator

def main(args: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Phase 8 Policy Recommendation Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run full policy recommendation workflow")
    run_parser.add_argument("--config", required=True, help="Path to recommendation configuration file")
    run_parser.add_argument("--base-dir", default=".", help="Base directory for paths")

    # Command: validate
    val_parser = subparsers.add_parser("validate", help="Validate recommendation configuration file")
    val_parser.add_argument("--config", required=True, help="Path to recommendation configuration file")

    # Command: check-compatibility
    comp_parser = subparsers.add_parser("check-compatibility", help="Validate compatibility across candidate experiments")
    comp_parser.add_argument("--config", required=True, help="Path to recommendation configuration file")
    comp_parser.add_argument("--base-dir", default=".", help="Base directory for paths")

    parsed = parser.parse_args(args)

    if parsed.command == "run":
        service = Phase8RecommendationService(base_dir=parsed.base_dir)
        res = service.run_recommendation(parsed.config)
        print(f"Recommendation Completed Successfully! Top Candidate: {res['top_recommended_candidate']}")
        print(f"Report Generated: {res['exported_artifacts']['report_md']}")
    elif parsed.command == "validate":
        config = RecommendationConfigLoader.load_from_file(parsed.config)
        RecommendationConfigValidator.validate(config)
        print("Recommendation Configuration is VALID.")
    elif parsed.command == "check-compatibility":
        config = RecommendationConfigLoader.load_from_file(parsed.config)
        candidates = ExperimentResultLoader.load_all(config.candidate_experiments, base_dir=parsed.base_dir)
        res = CompatibilityValidator.validate_compatibility(candidates)
        print(f"Candidate Experiments are COMPATIBLE! Count: {res['candidate_count']}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
