"""
Deterministic template-based explanation generator for policy recommendations (no LLMs).
"""

from typing import List, Dict, Any, Optional
from .recommendation_model import (
    RankingScore,
    FeasibilityCheckResult,
    ParetoCandidateResult,
    TradeoffComparison,
    WeightSensitivityResult,
    DemographicFairnessResult,
)

class ExplanationGenerator:
    """Generates structured, rule-based explanations justifying policy recommendations."""

    @staticmethod
    def generate_explanations(
        rankings: List[RankingScore],
        feasibility_checks: List[FeasibilityCheckResult],
        pareto_candidates: List[ParetoCandidateResult],
        tradeoffs: List[TradeoffComparison],
        sensitivity_results: List[WeightSensitivityResult],
        fairness_results: List[DemographicFairnessResult],
    ) -> List[str]:
        explanations = []

        if not rankings:
            return ["No candidate policies were evaluated."]

        top_candidate = rankings[0]
        feasible_checks_map = {f.experiment_id: f for f in feasibility_checks}
        pareto_map = {p.experiment_id: p for p in pareto_candidates}
        fairness_map = {f.experiment_id: f for f in fairness_results}

        # 1. Top Recommendation Justification
        if top_candidate.is_feasible:
            exp_1 = (
                f"RECOMMENDATION JUSTIFICATION: Policy Option '{top_candidate.display_name}' ({top_candidate.experiment_id}) "
                f"is ranked #1 with an overall Multi-Criteria Weighted Sum Score of {top_candidate.wsm_score:.4f} "
                f"(TOPSIS Relative Closeness Score of {top_candidate.topsis_score:.4f}). "
                f"It satisfies all policy feasibility constraints (Budget Cap, Exceedance Risk, Coverage Minimums, MC Standard Error)."
            )
        else:
            exp_1 = (
                f"RECOMMENDATION WARNING: Top-scoring Policy Option '{top_candidate.display_name}' ({top_candidate.experiment_id}) "
                f"violates one or more feasibility constraints. Review lower-ranked feasible options."
            )
        explanations.append(exp_1)

        # 2. Key Performance Metrics Summary for Top Candidate
        raw = top_candidate.raw_metrics
        cost = raw.get("mean_total_cost", 0.0)
        beneficiaries = raw.get("mean_beneficiaries", 0.0)
        risk = raw.get("budget_exceedance_risk", 0.0)
        exp_2 = (
            f"KEY METRICS SUMMARY FOR RANK #1: Expected Fiscal Cost = ₹{cost:,.2f}, Expected Beneficiary Coverage = {beneficiaries:,.0f} households/individuals, "
            f"Budget Exceedance Risk Probability = {risk:.1%}."
        )
        explanations.append(exp_2)

        # 3. Feasibility & Constraint Violations Rationale
        infeasible_count = 0
        for fc in feasibility_checks:
            if not fc.is_feasible:
                infeasible_count += 1
                violations_str = "; ".join(fc.violations)
                explanations.append(
                    f"FEASIBILITY EXCLUSION: '{fc.display_name}' ({fc.experiment_id}) marked INFEASIBLE due to constraint violations: {violations_str}"
                )

        if infeasible_count == 0:
            explanations.append("FEASIBILITY STATUS: All evaluated policy candidate options satisfied 100% of defined policy feasibility constraints.")

        # 4. Pareto Frontier Rationale
        pareto_optimal_names = [p.display_name for p in pareto_candidates if p.is_pareto_optimal]
        if pareto_optimal_names:
            explanations.append(
                f"PARETO FRONTIER STATUS: The non-dominated Pareto frontier candidates are: {', '.join(pareto_optimal_names)}. "
                f"These options represent optimal trade-offs where no single metric can be improved without sacrificing another."
            )

        # 5. Trade-off Analysis Rationale
        if tradeoffs:
            t = tradeoffs[0]
            explanations.append(f"TRADE-OFF INSIGHT: {t.description}")

        # 6. Stakeholder Weight Sensitivity Rationale
        if sensitivity_results:
            robust_top = True
            first_top_id = sensitivity_results[0].rankings[0]["experiment_id"]
            for sr in sensitivity_results[1:]:
                if sr.rankings and sr.rankings[0]["experiment_id"] != first_top_id:
                    robust_top = False
                    break

            if robust_top:
                explanations.append(
                    f"STAKEHOLDER SENSITIVITY: Policy Option '{top_candidate.display_name}' maintains Rank #1 consistently "
                    f"across all evaluated stakeholder weight profiles (Fiscal Conservative, Equity Focus, Risk Averse, Balanced Governance)."
                )
            else:
                explanations.append(
                    "STAKEHOLDER SENSITIVITY WARNING: Top policy ranking shifts across different stakeholder weight profiles. "
                    "Decision-makers should review stakeholder preference weightings."
                )

        # 7. Demographic Group Equity Rationale
        top_fairness = fairness_map.get(top_candidate.experiment_id)
        if top_fairness:
            explanations.append(
                f"DEMOGRAPHIC FAIRNESS ASSESSMENT: Rank #1 Option '{top_candidate.display_name}' achieved an overall fairness score of "
                f"{top_fairness.overall_fairness_score:.3f} (District Disparity Ratio: {top_fairness.district_disparity:.2f}, "
                f"Gender Disparity Ratio: {top_fairness.gender_disparity:.2f})."
            )

        return explanations
