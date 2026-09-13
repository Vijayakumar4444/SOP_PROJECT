"""
Pipeline verification runner testing Phase 9 Real-World Validation modules.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from backend.app.modules.real_world_validation.service import Phase9RealWorldValidationService

def main():
    print("==================================================================")
    print("      REAL-WORLD POLICY VALIDATION PIPELINE VERIFICATION         ")
    print("==================================================================")

    service = Phase9RealWorldValidationService(base_dir=".")
    res = service.run_validation("real_world_validation/kmut_policy")

    assert res["status"] == "PASS", "Validation execution failed"
    assert res["overall_pass"] is True, "Validation scorecard did not pass"

    print("✅ All Real-World Policy Validation verification checks PASSED!")
    print("==================================================================")

if __name__ == "__main__":
    main()
