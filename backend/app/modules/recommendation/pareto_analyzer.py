"""
Pareto frontier dominance analysis for multi-objective policy comparison.
"""

from typing import List, Dict, Any
from .recommendation_model import CandidatePolicyResult, MetricConfig, ParetoCandidateResult

class ParetoAnalyzer:
    """Computes Pareto dominance and non-dominated frontier across policy candidates."""

    @staticmethod
    def analyze_pareto(
        candidates: List[CandidatePolicyResult],
        metrics: List[MetricConfig],
    ) -> List[ParetoCandidateResult]:
        if not candidates:
            return []

        domination_map: Dict[str, Dict[str, List[str]]] = {
            c.experiment_id: {"dominates": [], "dominated_by": []} for c in candidates
        }

        # Pairwise dominance checks
        n = len(candidates)
        for i in range(n):
            cand_a = candidates[i]
            id_a = cand_a.experiment_id
            for j in range(i + 1, n):
                cand_b = candidates[j]
                id_b = cand_b.experiment_id

                a_dominates_b = ParetoAnalyzer._check_dominance(cand_a, cand_b, metrics)
                b_dominates_a = ParetoAnalyzer._check_dominance(cand_b, cand_a, metrics)

                if a_dominates_b:
                    domination_map[id_a]["dominates"].append(id_b)
                    domination_map[id_b]["dominated_by"].append(id_a)
                elif b_dominates_a:
                    domination_map[id_b]["dominates"].append(id_a)
                    domination_map[id_a]["dominated_by"].append(id_b)

        pareto_results = []
        for c in candidates:
            exp_id = c.experiment_id
            dom_data = domination_map[exp_id]
            is_pareto = len(dom_data["dominated_by"]) == 0

            pareto_results.append(
                ParetoCandidateResult(
                    experiment_id=exp_id,
                    display_name=c.display_name,
                    is_pareto_optimal=is_pareto,
                    dominated_by=dom_data["dominated_by"],
                    dominates=dom_data["dominates"],
                )
            )

        return pareto_results

    @staticmethod
    def _check_dominance(
        cand_a: CandidatePolicyResult,
        cand_b: CandidatePolicyResult,
        metrics: List[MetricConfig],
    ) -> bool:
        """Returns True if Candidate A dominates Candidate B."""
        at_least_as_good = True
        strictly_better = False

        for m in metrics:
            val_a = cand_a.raw_metrics.get(m.name, 0.0)
            val_b = cand_b.raw_metrics.get(m.name, 0.0)
            direction = m.direction.lower()

            if direction == "maximize":
                if val_a < val_b - 1e-9:
                    at_least_as_good = False
                    break
                elif val_a > val_b + 1e-9:
                    strictly_better = True
            else:  # minimize
                if val_a > val_b + 1e-9:
                    at_least_as_good = False
                    break
                elif val_a < val_b - 1e-9:
                    strictly_better = True

        return at_least_as_good and strictly_better
