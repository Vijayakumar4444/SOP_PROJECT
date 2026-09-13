"""
Pairwise head-to-head metric comparator across candidate policies.
"""

from typing import List, Dict, Any
from .recommendation_model import CandidatePolicyResult, MetricConfig, PairwiseComparison

class PairwiseComparator:
    """Performs pairwise head-to-head metric comparisons across policy candidates."""

    @staticmethod
    def compare_pairs(
        candidates: List[CandidatePolicyResult],
        metrics: List[MetricConfig],
    ) -> List[PairwiseComparison]:
        if len(candidates) < 2:
            return []

        pairwise_list = []
        n = len(candidates)
        for i in range(n):
            cand_a = candidates[i]
            for j in range(i + 1, n):
                cand_b = candidates[j]

                wins_a = 0
                wins_b = 0
                ties = 0
                deltas = {}

                for m in metrics:
                    val_a = cand_a.raw_metrics.get(m.name, 0.0)
                    val_b = cand_b.raw_metrics.get(m.name, 0.0)
                    delta = val_a - val_b
                    deltas[m.name] = round(delta, 4)

                    direction = m.direction.lower()
                    if direction == "maximize":
                        if delta > 1e-6:
                            wins_a += 1
                        elif delta < -1e-6:
                            wins_b += 1
                        else:
                            ties += 1
                    else:  # minimize
                        if delta < -1e-6:
                            wins_a += 1
                        elif delta > 1e-6:
                            wins_b += 1
                        else:
                            ties += 1

                pairwise_list.append(
                    PairwiseComparison(
                        candidate_a=cand_a.experiment_id,
                        candidate_b=cand_b.experiment_id,
                        wins_a=wins_a,
                        wins_b=wins_b,
                        ties=ties,
                        detailed_deltas=deltas,
                    )
                )

        return pairwise_list
