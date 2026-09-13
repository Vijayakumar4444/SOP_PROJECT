"""
Trade-off analyzer for identifying key metric trade-offs between policy candidates.
"""

from typing import List, Dict, Any
from .recommendation_model import CandidatePolicyResult, MetricConfig, TradeoffComparison

class TradeoffAnalyzer:
    """Analyzes trade-off relationships and marginal rates of substitution between candidate policies."""

    @staticmethod
    def analyze_tradeoffs(
        candidates: List[CandidatePolicyResult],
        metrics: List[MetricConfig],
    ) -> List[TradeoffComparison]:
        if len(candidates) < 2:
            return []

        tradeoffs = []
        cost_metric = "mean_total_cost"
        cov_metric = "mean_beneficiaries"

        # Compare pairs of top candidates for cost-coverage trade-off
        for i in range(len(candidates)):
            cand_a = candidates[i]
            for j in range(i + 1, len(candidates)):
                cand_b = candidates[j]

                cost_a = cand_a.raw_metrics.get(cost_metric, 0.0)
                cost_b = cand_b.raw_metrics.get(cost_metric, 0.0)
                cov_a = cand_a.raw_metrics.get(cov_metric, 0.0)
                cov_b = cand_b.raw_metrics.get(cov_metric, 0.0)

                cost_diff = cost_a - cost_b
                cov_diff = cov_a - cov_b

                if abs(cov_diff) > 1e-6:
                    marginal_ratio = cost_diff / cov_diff
                    desc = (
                        f"'{cand_a.display_name}' incurs ₹{cost_diff:+,.2f} cost difference "
                        f"for {cov_diff:+,.0f} beneficiary headcount difference compared to '{cand_b.display_name}' "
                        f"(Marginal ratio: ₹{abs(marginal_ratio):,.2f} per additional beneficiary)."
                    )
                else:
                    marginal_ratio = 0.0
                    desc = f"'{cand_a.display_name}' and '{cand_b.display_name}' have identical beneficiary coverage."

                tradeoffs.append(
                    TradeoffComparison(
                        candidate_a=cand_a.experiment_id,
                        candidate_b=cand_b.experiment_id,
                        metric_a=cost_metric,
                        metric_b=cov_metric,
                        value_a_diff=round(cost_diff, 2),
                        value_b_diff=round(cov_diff, 2),
                        marginal_tradeoff_ratio=round(marginal_ratio, 2),
                        description=desc,
                    )
                )

        return tradeoffs
