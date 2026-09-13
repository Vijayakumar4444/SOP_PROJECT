from __future__ import annotations

from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.data_foundation.io_utils import write_json, write_md
from backend.app.modules.policy_engine.service import Phase6PolicyService


def main() -> None:
    print("============================================================")
    print("SOP Project Phase 6: Policy Engine Execution")
    print("============================================================")

    service = Phase6PolicyService(project_root=ROOT)
    example_dir = ROOT / "config/policy_engine/examples"

    example_policies = [
        ("tn_elderly_pension.yaml", "Person-Level Elderly Assistance Policy"),
        ("tn_clean_cooking_subsidy.yaml", "Household-Level Clean Cooking Fuel Policy"),
        ("tn_youth_skilling_stipend.yaml", "Budget-Constrained Youth Skilling Policy"),
    ]

    all_results = []

    for policy_filename, desc in example_policies:
        policy_path = example_dir / policy_filename
        print(f"\n---> Executing Policy: {desc} ({policy_filename})")
        res = service.execute_policy(policy_path=policy_path)
        all_results.append(res)
        
        if res["success"]:
            summary = res["summary"]
            print(f"     Status: SUCCESS (Run ID: {res['run_id']})")
            print(f"     Evaluated Records: {summary['total_evaluated_records']:,}")
            print(f"     Eligible Records:  {summary['unweighted_eligible_records']:,} (Weighted: {summary['weighted_eligible_population']:,.2f})")
            print(f"     Beneficiaries:     {summary['unweighted_selected_beneficiaries']:,} (Weighted: {summary['weighted_beneficiary_population']:,.2f})")
            print(f"     Total Cost (INR):  ₹{summary['total_estimated_program_cost_inr']:,.2f}")
        else:
            print(f"     Status: FAILED")
            print(f"     Errors: {res.get('errors')}")

    # Write summary markdown report
    report_md = _generate_phase6_summary_md(all_results)
    report_path = ROOT / "reports/phase6_summary.md"
    write_md(report_path, report_md)
    print(f"\nPhase 6 Summary Report generated at: {report_path}")

    # Handoff for Phase 7
    handoff_path = ROOT / "data/synthetic/phase7_monte_carlo_handoff.json"
    handoff_data = {
        "phase": 6,
        "status": "PASS",
        "timestamp": json.dumps(all_results[0]["summary"].get("policy_id")),
        "demonstration_runs": [r["run_id"] for r in all_results if r["success"]],
        "interface_method": "Phase6PolicyService.evaluate_simulation(policy_path, population_df, weight_column, seed, parameter_overrides)",
    }
    write_json(handoff_path, handoff_data)
    print(f"Phase 7 Handoff file created at: {handoff_path}\n")


def _generate_phase6_summary_md(results: list[dict]) -> str:
    lines = [
        "# SOP Project - Phase 6 Policy Engine Execution Summary",
        "",
        "## Overview",
        "Phase 6 provides a deterministic, reusable Policy Execution Engine for Tamil Nadu.",
        "It evaluates policy eligibility, applies capacity/budget constraints, computes decimal-safe benefit outlays,",
        "and produces weighted population estimates using the Phase 5 calibrated synthetic population.",
        "",
        "## Demonstration Policy Execution Results",
        "",
        "| Policy ID | Name | Target Unit | Evaluated | Eligible (Weighted) | Beneficiaries (Weighted) | Total Program Cost (INR) | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in results:
        if not r["success"]:
            lines.append(f"| {r['policy_id']} | N/A | N/A | N/A | N/A | N/A | N/A | FAILED |")
            continue
        s = r["summary"]
        lines.append(
            f"| `{s['policy_id']}` | {s['policy_name']} | {s['target_unit']} | {s['total_evaluated_records']:,} | "
            f"{s['unweighted_eligible_records']:,} ({s['weighted_eligible_population']:,.2f}) | "
            f"{s['unweighted_selected_beneficiaries']:,} ({s['weighted_beneficiary_population']:,.2f}) | "
            f"₹{s['total_estimated_program_cost_inr']:,.2f} | PASS |"
        )

    lines.extend([
        "",
        "## Phase 7 Callable Interface",
        "Phase 6 exposes a clean callable interface for the Phase 7 Monte Carlo Engine:",
        "```python",
        "from backend.app.modules.policy_engine.service import Phase6PolicyService",
        "service = Phase6PolicyService()",
        "sim_summary = service.evaluate_simulation(",
        "    policy_path='config/policy_engine/examples/tn_elderly_pension.yaml',",
        "    population_df=sampled_df,",
        "    weight_column='calibration_weight',",
        "    seed=42,",
        "    parameter_overrides={'total_budget': 10000000}",
        ")",
        "```",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    main()
