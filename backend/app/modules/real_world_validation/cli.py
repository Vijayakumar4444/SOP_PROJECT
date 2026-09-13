"""
CLI interface for Phase 9 Real-World Policy Validation Engine.
"""

import sys
import argparse
from typing import List, Optional
from .service import Phase9RealWorldValidationService

def main(args: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Phase 9 Real-World Policy Validation CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run real-world policy validation experiment")
    run_parser.add_argument("--policy-dir", default="real_world_validation/kmut_policy", help="Path to policy directory")
    run_parser.add_argument("--base-dir", default=".", help="Base directory")

    parsed = parser.parse_args(args)

    if parsed.command == "run":
        service = Phase9RealWorldValidationService(base_dir=parsed.base_dir)
        res = service.run_validation(parsed.policy_dir)
        print(f"Validation Completed! Status: {res['validation_status']}")
        print(f"Statewide Beneficiary MAPE: {res['statewide_beneficiary_mape']}%")
        print(f"Report Generated: {res['exported_artifacts']['validation_report_md']}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
