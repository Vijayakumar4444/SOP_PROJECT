"""
Primary runner script executing Phase 9 Real-World Policy Validation on KMUT policy.
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from backend.app.modules.real_world_validation.service import Phase9RealWorldValidationService

def main():
    print("==================================================================")
    print("  SOP PROJECT — REAL-WORLD POLICY VALIDATION RUNNER (KMUT POLICY) ")
    print("==================================================================")

    service = Phase9RealWorldValidationService(base_dir=".")
    result = service.run_validation("real_world_validation/kmut_policy")

    print("\n--- VALIDATION WORKFLOW COMPLETE ---")
    print(f"Status                           : {result['status']}")
    print(f"Policy ID                        : {result['policy_id']}")
    print(f"Validation Decision              : {result['validation_status']}")
    print(f"Overall Pass                     : {result['overall_pass']}")
    print(f"Statewide Beneficiary MAPE       : {result['statewide_beneficiary_mape']}%")
    print(f"District Pearson Correlation (r) : {result['district_pearson_r']}")

    print("\nExported Artifacts:")
    for k, v in result['exported_artifacts'].items():
        print(f"  - {k:<25}: {v}")

    print("==================================================================")

if __name__ == "__main__":
    main()
