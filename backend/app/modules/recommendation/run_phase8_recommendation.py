"""
Primary runner script executing Phase 8 Recommendation Engine on demonstration scenarios.
"""

import os
import sys
import json

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from backend.app.modules.recommendation.service import Phase8RecommendationService

def main():
    config_path = os.path.join("config", "recommendation", "examples", "tn_policy_recommendation.yaml")
    if not os.path.exists(config_path):
        print(f"Error: Recommendation configuration not found at '{config_path}'")
        sys.exit(1)

    print("==================================================================")
    print("      SOP PROJECT — PHASE 8 RECOMMENDATION ENGINE RUNNER        ")
    print("==================================================================")
    print(f"Loading recommendation scenario: {config_path}")

    service = Phase8RecommendationService(base_dir=".")
    result = service.run_recommendation(config_path)

    print("\n--- RECOMMENDATION WORKFLOW COMPLETE ---")
    print(f"Status                       : {result['status']}")
    print(f"Recommendation ID            : {result['recommendation_id']}")
    print(f"Top Recommended Candidate     : {result['top_recommended_candidate']}")
    print(f"Total Candidates Evaluated   : {result['total_candidates']}")
    print(f"Feasible Candidates Count    : {result['feasible_candidates']}")
    print("\nExported Artifacts:")
    for k, v in result['exported_artifacts'].items():
        print(f"  - {k:<20}: {v}")

    print("\nGenerated Explanations:")
    for exp in result['explanations']:
        print(f"  * {exp}")

    print("==================================================================")

if __name__ == "__main__":
    main()
