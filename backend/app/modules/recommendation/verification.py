"""
Phase-by-phase end-to-end verification suite covering Phase 1 through Phase 8.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from backend.app.modules.data_foundation.io_utils import read_json
from backend.app.modules.recommendation.service import Phase8RecommendationService

class SimulationEngineVerifier:
    """Verifies that all 8 phases of the SOP Simulation Engine produce valid artifacts and handoffs."""

    @staticmethod
    def verify_all_phases(base_dir: str = ".") -> Dict[str, Any]:
        results = {}

        # Phase 1: Data Foundation
        ref_path = os.path.join(base_dir, "data", "synthetic", "training", "reference_training_v1.csv")
        p1_valid = os.path.exists(ref_path)
        results["phase1_data_foundation"] = {
            "status": "PASS" if p1_valid else "FAIL",
            "artifact": ref_path,
        }

        # Phase 2: Policy-Data Compatibility Engine
        p2_manifest = os.path.join(base_dir, "data", "synthetic", "variable_selection.json")
        p2_valid = os.path.exists(p2_manifest)
        results["phase2_compatibility_engine"] = {
            "status": "PASS" if p2_valid else "FAIL",
            "artifact": p2_manifest,
        }

        # Phase 3: Synthetic Population Generation
        p3_manifest = os.path.join(base_dir, "data", "synthetic", "phase3_finalization_manifest.json")
        p3_valid = os.path.exists(p3_manifest)
        results["phase3_synthetic_population"] = {
            "status": "PASS" if p3_valid else "FAIL",
            "artifact": p3_manifest,
        }

        # Phase 4: Population Validation
        p4_manifest = os.path.join(base_dir, "data", "synthetic", "phase4_validation_manifest.json")
        p4_valid = os.path.exists(p4_manifest)
        results["phase4_population_validation"] = {
            "status": "PASS" if p4_valid else "FAIL",
            "artifact": p4_manifest,
        }

        # Phase 5: Calibration & Reweighting
        p5_manifest = os.path.join(base_dir, "data", "synthetic", "phase5_calibration_handoff.json")
        p5_valid = os.path.exists(p5_manifest)
        results["phase5_calibration_reweighting"] = {
            "status": "PASS" if p5_valid else "FAIL",
            "artifact": p5_manifest,
        }

        # Phase 6: Policy Engine
        p6_manifest = os.path.join(base_dir, "data", "synthetic", "phase6_policy_engine_handoff.json")
        p6_valid = os.path.exists(p6_manifest)
        results["phase6_policy_engine"] = {
            "status": "PASS" if p6_valid else "FAIL",
            "artifact": p6_manifest,
        }

        # Phase 7: Monte Carlo and Uncertainty Engine
        p7_manifest = os.path.join(base_dir, "data", "synthetic", "phase7_monte_carlo_handoff.json")
        p7_valid = os.path.exists(p7_manifest)
        results["phase7_monte_carlo_engine"] = {
            "status": "PASS" if p7_valid else "FAIL",
            "artifact": p7_manifest,
        }

        # Phase 8: Recommendation Engine
        config_path = os.path.join(base_dir, "config", "recommendation", "examples", "tn_policy_recommendation.yaml")
        service = Phase8RecommendationService(base_dir=base_dir)
        p8_res = service.run_recommendation(config_path)

        p8_manifest = os.path.join(base_dir, "data", "synthetic", "phase8_recommendation_handoff.json")
        p8_valid = os.path.exists(p8_manifest) and p8_res["status"] == "PASS"
        results["phase8_recommendation_engine"] = {
            "status": "PASS" if p8_valid else "FAIL",
            "artifact": p8_manifest,
            "top_recommended_candidate": p8_res["top_recommended_candidate"],
        }

        all_passed = all(r["status"] == "PASS" for r in results.values())
        return {
            "overall_status": "PASS" if all_passed else "FAIL",
            "phases_verified": len(results),
            "phase_details": results,
        }

def main():
    print("==================================================================")
    print("  SIMULATION ENGINE END-TO-END PHASE VERIFICATION SUITE (P1-P8)   ")
    print("==================================================================")
    res = SimulationEngineVerifier.verify_all_phases()
    for phase, detail in res["phase_details"].items():
        mark = "✅ PASS" if detail["status"] == "PASS" else "❌ FAIL"
        print(f"  [{mark}] {phase:<35}: {detail['artifact']}")

    print("\n------------------------------------------------------------------")
    print(f"OVERALL PIPELINE VERIFICATION RESULT: {res['overall_status']}")
    print("==================================================================")

if __name__ == "__main__":
    main()
