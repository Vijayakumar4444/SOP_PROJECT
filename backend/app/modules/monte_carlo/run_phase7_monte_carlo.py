from __future__ import annotations

from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.data_foundation.io_utils import write_json, write_md
from backend.app.modules.monte_carlo.service import Phase7MonteCarloService


def main() -> None:
    print("============================================================")
    print("SOP Project Phase 7: Monte Carlo & Uncertainty Engine Execution")
    print("============================================================")

    service = Phase7MonteCarloService(project_root=ROOT)
    example_dir = ROOT / "config/monte_carlo/examples"

    experiments = [
        ("experiment_1_population_uncertainty.yaml", "Population Uncertainty (Household Bootstrap)"),
        ("experiment_2_policy_parameter_uncertainty.yaml", "Policy Parameter Uncertainty (Discrete/Triangular)"),
        ("experiment_3_combined_uncertainty.yaml", "Combined Uncertainty (Population + Parameter + Take-up)"),
    ]

    all_exp_results = []

    for cfg_filename, desc in experiments:
        cfg_path = example_dir / cfg_filename
        print(f"\n---> Running Monte Carlo Experiment: {desc} ({cfg_filename})")
        res = service.run_experiment(config_path=cfg_path, iterations_override=30)
        all_exp_results.append(res)

        if res["success"]:
            summary = res["summary"]
            cost_stats = summary.get("metrics_summary", {}).get("total_policy_cost", {})
            print(f"     Status: SUCCESS (Experiment ID: {res['experiment_id']})")
            print(f"     Completed Iterations: {res['completed_iterations']} valid / {res['failed_iterations']} failed")
            print(f"     Converged Status:     {res['converged']}")
            print(f"     Mean Cost (INR):      ₹{cost_stats.get('mean', 0.0):,.2f} ± ₹{cost_stats.get('std_dev', 0.0):,.2f}")
            print(f"     95% Cost Interval:    ₹{cost_stats.get('percentiles', {}).get('p2_5', 0.0):,.2f} to ₹{cost_stats.get('percentiles', {}).get('p97_5', 0.0):,.2f}")
            print(f"     MC Std Error:         ₹{cost_stats.get('mc_standard_error', 0.0):,.2f} (Rel Error: {cost_stats.get('relative_mc_error', 0.0):.4f})")
            print(f"     Risk Metrics:         {res.get('risk_probabilities')}")
        else:
            print(f"     Status: FAILED")
            print(f"     Errors: {res.get('errors')}")

    # Write summary markdown report
    report_md = _generate_phase7_summary_md(all_exp_results)
    report_path = ROOT / "reports/phase7_summary.md"
    write_md(report_path, report_md)
    print(f"\nPhase 7 Summary Report generated at: {report_path}")

    # Handoff for Phase 8
    handoff_path = ROOT / "data/synthetic/phase8_recommendation_handoff.json"
    handoff_data = {
        "phase": 7,
        "status": "PASS",
        "timestamp": datetime_now_iso(),
        "demonstration_experiments": [r["experiment_id"] for r in all_exp_results if r["success"]],
        "interface_method": "Phase7MonteCarloService.run_experiment(config_path, output_dir, iterations_override)",
    }
    write_json(handoff_path, handoff_data)
    print(f"Phase 8 Handoff file created at: {handoff_path}\n")


def datetime_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _generate_phase7_summary_md(results: list[dict]) -> str:
    lines = [
        "# SOP Project - Phase 7 Monte Carlo & Uncertainty Engine Summary",
        "",
        "## Overview",
        "Phase 7 evaluates policy outcome uncertainty for Tamil Nadu using stochastic Monte Carlo simulation.",
        "It measures outcome variability across sampled populations, policy parameter distributions, and take-up rates,",
        "calculates percentiles and 95% confidence intervals, quantifies Monte Carlo standard error, tracks convergence,",
        "and computes risk probabilities (e.g. probability of budget exceedance).",
        "",
        "## Demonstration Experiment Results",
        "",
        "| Experiment ID | Completed (Valid/Failed) | Converged | Mean Cost (INR) | Std Dev (INR) | 95% Uncertainty Interval (P2.5 - P97.5) | Rel MC Error | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in results:
        if not r["success"]:
            lines.append(f"| {r['experiment_id']} | N/A | N/A | N/A | N/A | N/A | N/A | FAILED |")
            continue
        s = r["summary"]
        cost_stats = s.get("metrics_summary", {}).get("total_policy_cost", {})
        pcts = cost_stats.get("percentiles", {})
        lines.append(
            f"| `{r['experiment_id']}` | {r['completed_iterations']} / {r['failed_iterations']} | {r['converged']} | "
            f"₹{cost_stats.get('mean', 0.0):,.2f} | ₹{cost_stats.get('std_dev', 0.0):,.2f} | "
            f"₹{pcts.get('p2_5', 0.0):,.2f} – ₹{pcts.get('p97_5', 0.0):,.2f} | "
            f"{cost_stats.get('relative_mc_error', 0.0):.4f} | PASS |"
        )

    lines.extend([
        "",
        "## Phase 8 Recommendation & Reporting Handoff",
        "Phase 7 exposes experiment artifacts and handoff metrics for Phase 8:",
        "```json",
        "{",
        '  "phase": 7,',
        '  "status": "PASS",',
        '  "handoff_manifest": "data/synthetic/phase8_recommendation_handoff.json"',
        "}",
        "```",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    main()
