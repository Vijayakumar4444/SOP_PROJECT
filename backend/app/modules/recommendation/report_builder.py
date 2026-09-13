"""
Report builder writing structured JSON, CSV, Markdown reports and Phase 8 completion manifest.
"""

import os
from typing import Dict, Any, List
from ..data_foundation.io_utils import write_json, write_csv, write_md
from .recommendation_model import (
    RecommendationConfig,
    RecommendationSummary,
    RankingScore,
    FeasibilityCheckResult,
    ParetoCandidateResult,
    TradeoffComparison,
    PairwiseComparison,
    WeightSensitivityResult,
    DemographicFairnessResult,
)

class ReportBuilder:
    """Formats and writes structured recommendation artifacts and markdown reports."""

    @staticmethod
    def build_all_reports(
        config: RecommendationConfig,
        summary: RecommendationSummary,
        pairwise_comparisons: List[PairwiseComparison],
        base_dir: str = ".",
    ) -> Dict[str, str]:
        output_dir = config.output_dir
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(base_dir, output_dir)
        os.makedirs(output_dir, exist_ok=True)

        summary_path = os.path.join(output_dir, config.summary_json)
        ranking_csv_path = os.path.join(output_dir, config.ranking_csv)
        tradeoff_path = os.path.join(output_dir, config.tradeoff_json)
        fairness_path = os.path.join(output_dir, config.fairness_json)
        report_md_path = os.path.join(output_dir, config.report_md)

        handoff_path = config.handoff_manifest
        if not os.path.isabs(handoff_path):
            handoff_path = os.path.join(base_dir, handoff_path)
        os.makedirs(os.path.dirname(handoff_path), exist_ok=True)

        # 1. Summary JSON
        summary_dict = {
            "recommendation_id": summary.recommendation_id,
            "generated_at": summary.generated_at,
            "top_recommended_candidate": summary.top_recommended_candidate,
            "total_candidates": summary.total_candidates,
            "feasible_candidates_count": summary.feasible_candidates_count,
            "rankings": [
                {
                    "experiment_id": r.experiment_id,
                    "display_name": r.display_name,
                    "rank": r.rank,
                    "topsis_rank": r.topsis_rank,
                    "is_feasible": r.is_feasible,
                    "wsm_score": r.wsm_score,
                    "topsis_score": r.topsis_score,
                    "raw_metrics": r.raw_metrics,
                    "normalized_metrics": r.normalized_metrics,
                }
                for r in summary.rankings
            ],
            "feasibility_checks": [
                {
                    "experiment_id": f.experiment_id,
                    "display_name": f.display_name,
                    "is_feasible": f.is_feasible,
                    "violations": f.violations,
                    "evaluated_constraints": f.evaluated_constraints,
                }
                for f in summary.feasibility_checks
            ],
            "pareto_candidates": [
                {
                    "experiment_id": p.experiment_id,
                    "display_name": p.display_name,
                    "is_pareto_optimal": p.is_pareto_optimal,
                    "dominated_by": p.dominated_by,
                    "dominates": p.dominates,
                }
                for p in summary.pareto_candidates
            ],
            "explanations": summary.explanations,
        }
        write_json(summary_path, summary_dict)

        # 2. Ranking CSV
        csv_records = []
        for r in summary.rankings:
            rec = {
                "rank": r.rank,
                "topsis_rank": r.topsis_rank,
                "experiment_id": r.experiment_id,
                "display_name": r.display_name,
                "is_feasible": "YES" if r.is_feasible else "NO",
                "wsm_score": r.wsm_score,
                "topsis_score": r.topsis_score,
                "mean_total_cost": r.raw_metrics.get("mean_total_cost", 0.0),
                "p95_total_cost": r.raw_metrics.get("p95_total_cost", 0.0),
                "mean_beneficiaries": r.raw_metrics.get("mean_beneficiaries", 0.0),
                "budget_exceedance_risk": r.raw_metrics.get("budget_exceedance_risk", 0.0),
            }
            csv_records.append(rec)
        write_csv(ranking_csv_path, csv_records)

        # 3. Tradeoff JSON
        tradeoff_dict = {
            "tradeoffs": [
                {
                    "candidate_a": t.candidate_a,
                    "candidate_b": t.candidate_b,
                    "metric_a": t.metric_a,
                    "metric_b": t.metric_b,
                    "value_a_diff": t.value_a_diff,
                    "value_b_diff": t.value_b_diff,
                    "marginal_tradeoff_ratio": t.marginal_tradeoff_ratio,
                    "description": t.description,
                }
                for t in summary.tradeoffs
            ],
            "pairwise_comparisons": [
                {
                    "candidate_a": pw.candidate_a,
                    "candidate_b": pw.candidate_b,
                    "wins_a": pw.wins_a,
                    "wins_b": pw.wins_b,
                    "ties": pw.ties,
                    "detailed_deltas": pw.detailed_deltas,
                }
                for pw in pairwise_comparisons
            ],
        }
        write_json(tradeoff_path, tradeoff_dict)

        # 4. Fairness JSON
        fairness_dict = {
            "fairness_results": [
                {
                    "experiment_id": f.experiment_id,
                    "display_name": f.display_name,
                    "district_disparity": f.district_disparity,
                    "gender_disparity": f.gender_disparity,
                    "overall_fairness_score": f.overall_fairness_score,
                    "group_breakdowns": f.group_breakdowns,
                }
                for f in summary.fairness_results
            ]
        }
        write_json(fairness_path, fairness_dict)

        # 5. Recommendation Markdown Report
        md_lines = [
            f"# {config.title}",
            "",
            f"**Recommendation Scenario ID**: `{summary.recommendation_id}`  ",
            f"**Generated At**: `{summary.generated_at}`  ",
            f"**Total Candidates Evaluated**: `{summary.total_candidates}` (Feasible: `{summary.feasible_candidates_count}`)  ",
            "",
            "## Executive Summary & Recommendation Rationale",
            "",
        ]

        for exp in summary.explanations:
            md_lines.append(f"- {exp}")

        md_lines.extend([
            "",
            "## Policy Candidate Ranking Results",
            "",
            "| Rank | TOPSIS Rank | Feasible | Candidate Display Name | WSM Score | TOPSIS Score | Expected Cost (₹) | Beneficiaries | Risk Prob |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ])

        for r in summary.rankings:
            feas_str = "✅ YES" if r.is_feasible else "❌ NO"
            cost_str = f"₹{r.raw_metrics.get('mean_total_cost', 0.0):,.2f}"
            ben_str = f"{r.raw_metrics.get('mean_beneficiaries', 0.0):,.0f}"
            risk_str = f"{r.raw_metrics.get('budget_exceedance_risk', 0.0):.1%}"
            md_lines.append(
                f"| {r.rank} | {r.topsis_rank} | {feas_str} | {r.display_name} | {r.wsm_score:.4f} | {r.topsis_score:.4f} | {cost_str} | {ben_str} | {risk_str} |"
            )

        md_lines.extend([
            "",
            "## Pareto Frontier Dominance Status",
            "",
            "| Candidate | Pareto Optimal? | Dominated By | Dominates |",
            "| --- | --- | --- | --- |",
        ])

        for p in summary.pareto_candidates:
            p_str = "⭐ Non-Dominated" if p.is_pareto_optimal else "Dominated"
            dom_by = ", ".join(p.dominated_by) if p.dominated_by else "None"
            doms = ", ".join(p.dominates) if p.dominates else "None"
            md_lines.append(f"| {p.display_name} | {p_str} | {dom_by} | {doms} |")

        md_lines.extend([
            "",
            "## Stakeholder Profile Weight Sensitivity",
            "",
        ])

        for ws in summary.weight_sensitivity:
            md_lines.append(f"### Profile: {ws.profile_name}")
            for rk in ws.rankings:
                feas_mark = " (Feasible)" if rk["is_feasible"] else " (Infeasible)"
                md_lines.append(f"- **Rank {rk['rank']}**: {rk['display_name']}{feas_mark} — Score: {rk['wsm_score']:.4f}")

        md_lines.extend([
            "",
            "## Demographic Fairness & District Equity Assessment",
            "",
            "| Candidate | District Disparity Ratio | Gender Disparity Ratio | Overall Fairness Score |",
            "| --- | --- | --- | --- |",
        ])

        for f in summary.fairness_results:
            md_lines.append(
                f"| {f.display_name} | {f.district_disparity:.2f} | {f.gender_disparity:.2f} | {f.overall_fairness_score:.3f} |"
            )

        write_md(report_md_path, md_lines)

        # 6. Handoff Manifest
        handoff_data = {
            "phase": 8,
            "status": "PASS",
            "recommendation_id": summary.recommendation_id,
            "top_recommended_candidate": summary.top_recommended_candidate,
            "artifact_directory": output_dir,
            "summary_json_path": summary_path,
            "ranking_csv_path": ranking_csv_path,
            "tradeoff_json_path": tradeoff_path,
            "fairness_json_path": fairness_path,
            "report_md_path": report_md_path,
        }
        write_json(handoff_path, handoff_data)

        return {
            "summary_json": summary_path,
            "ranking_csv": ranking_csv_path,
            "tradeoff_json": tradeoff_path,
            "fairness_json": fairness_path,
            "report_md": report_md_path,
            "handoff_manifest": handoff_path,
        }
