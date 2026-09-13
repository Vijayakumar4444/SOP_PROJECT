"""
Multi-criteria decision making ranking engine (WSM, TOPSIS).
"""

import math
from typing import List, Dict, Any
from .recommendation_model import (
    CandidatePolicyResult,
    FeasibilityCheckResult,
    NormalizedMetricResult,
    MetricConfig,
    RankingScore,
)

class RankingEngine:
    """Computes multi-criteria policy candidate rankings using WSM and TOPSIS."""

    @staticmethod
    def rank_candidates(
        candidates: List[CandidatePolicyResult],
        feasibility_checks: List[FeasibilityCheckResult],
        normalized_results: List[NormalizedMetricResult],
        metrics: List[MetricConfig],
        custom_weights: Dict[str, float] = None,
    ) -> List[RankingScore]:
        if not candidates:
            return []

        feasibility_map = {fc.experiment_id: fc.is_feasible for fc in feasibility_checks}
        norm_map = {nr.experiment_id: nr.normalized_metrics for nr in normalized_results}

        # Determine metric weights
        weights: Dict[str, float] = {}
        for m in metrics:
            if custom_weights and m.name in custom_weights:
                weights[m.name] = custom_weights[m.name]
            else:
                weights[m.name] = m.weight

        # 1. Compute Weighted Sum Model (WSM) Scores
        wsm_scores: Dict[str, float] = {}
        for c in candidates:
            norm_metrics = norm_map.get(c.experiment_id, {})
            score = sum(weights.get(m.name, 0.0) * norm_metrics.get(m.name, 0.0) for m in metrics)
            wsm_scores[c.experiment_id] = score

        # 2. Compute TOPSIS Scores
        topsis_scores = RankingEngine._compute_topsis(candidates, metrics, weights)

        # 3. Create RankingScore objects and assign ranks
        ranking_scores = []
        for c in candidates:
            exp_id = c.experiment_id
            is_feasible = feasibility_map.get(exp_id, True)

            ranking_scores.append(
                RankingScore(
                    experiment_id=exp_id,
                    display_name=c.display_name,
                    is_feasible=is_feasible,
                    wsm_score=round(wsm_scores.get(exp_id, 0.0), 6),
                    topsis_score=round(topsis_scores.get(exp_id, 0.0), 6),
                    rank=0,  # Will be set below
                    topsis_rank=0,  # Will be set below
                    normalized_metrics={k: round(v, 4) for k, v in norm_map.get(exp_id, {}).items()},
                    raw_metrics=c.raw_metrics,
                )
            )

        # Sort WSM: Feasible options first (sorted by WSM score desc), then Infeasible options
        ranking_scores.sort(key=lambda s: (s.is_feasible, s.wsm_score), reverse=True)
        for rank_idx, rs in enumerate(ranking_scores, start=1):
            rs.rank = rank_idx

        # Sort TOPSIS: Feasible options first (sorted by TOPSIS score desc), then Infeasible options
        topsis_sorted = sorted(ranking_scores, key=lambda s: (s.is_feasible, s.topsis_score), reverse=True)
        for t_rank, rs in enumerate(topsis_sorted, start=1):
            rs.topsis_rank = t_rank

        return ranking_scores

    @staticmethod
    def _compute_topsis(
        candidates: List[CandidatePolicyResult],
        metrics: List[MetricConfig],
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        if not candidates:
            return {}

        # Construct raw decision matrix
        # Columns = metrics, Rows = candidates
        matrix: Dict[str, Dict[str, float]] = {c.experiment_id: {} for c in candidates}
        for c in candidates:
            for m in metrics:
                matrix[c.experiment_id][m.name] = c.raw_metrics.get(m.name, 0.0)

        # Vector normalization: r_ij = x_ij / sqrt(sum(x_kj^2))
        norm_matrix: Dict[str, Dict[str, float]] = {c.experiment_id: {} for c in candidates}
        for m in metrics:
            col_sq_sum = sum(matrix[c.experiment_id][m.name] ** 2 for c in candidates)
            denom = math.sqrt(col_sq_sum) if col_sq_sum > 1e-9 else 1.0
            for c in candidates:
                norm_matrix[c.experiment_id][m.name] = (matrix[c.experiment_id][m.name] / denom) * weights.get(m.name, 0.0)

        # Ideal Positive (A+) and Ideal Negative (A-) solutions
        ideal_pos: Dict[str, float] = {}
        ideal_neg: Dict[str, float] = {}

        for m in metrics:
            vals = [norm_matrix[c.experiment_id][m.name] for c in candidates]
            if m.direction.lower() == "maximize":
                ideal_pos[m.name] = max(vals)
                ideal_neg[m.name] = min(vals)
            else:  # minimize
                ideal_pos[m.name] = min(vals)
                ideal_neg[m.name] = max(vals)

        # Compute Euclidean distances D+ and D-
        topsis_scores: Dict[str, float] = {}
        for c in candidates:
            exp_id = c.experiment_id
            d_pos_sq = sum((norm_matrix[exp_id][m.name] - ideal_pos[m.name]) ** 2 for m in metrics)
            d_neg_sq = sum((norm_matrix[exp_id][m.name] - ideal_neg[m.name]) ** 2 for m in metrics)
            d_pos = math.sqrt(d_pos_sq)
            d_neg = math.sqrt(d_neg_sq)

            denom = d_pos + d_neg
            relative_closeness = (d_neg / denom) if denom > 1e-9 else 0.5
            topsis_scores[exp_id] = relative_closeness

        return topsis_scores
