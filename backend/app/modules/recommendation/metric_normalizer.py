"""
Metric normalization algorithms (Min-Max, Z-score) for recommendation evaluation.
"""

import math
from typing import List, Dict, Any
from .recommendation_model import CandidatePolicyResult, MetricConfig, NormalizedMetricResult

class MetricNormalizer:
    """Normalizes raw policy metrics according to optimization direction (minimize/maximize)."""

    @staticmethod
    def normalize_candidates(
        candidates: List[CandidatePolicyResult],
        metrics: List[MetricConfig],
        method: str = "min_max",
    ) -> List[NormalizedMetricResult]:
        if not candidates:
            return []

        # Extract metric series across candidates
        series: Dict[str, List[float]] = {m.name: [] for m in metrics}
        for c in candidates:
            for m in metrics:
                val = c.raw_metrics.get(m.name, 0.0)
                series[m.name].append(val)

        # Precompute min, max, mean, std per metric
        stats: Dict[str, Dict[str, float]] = {}
        for m in metrics:
            vals = series[m.name]
            min_v = min(vals) if vals else 0.0
            max_v = max(vals) if vals else 1.0
            mean_v = sum(vals) / len(vals) if vals else 0.0
            variance = sum((x - mean_v) ** 2 for x in vals) / len(vals) if vals else 0.0
            std_v = math.sqrt(variance)
            stats[m.name] = {
                "min": min_v,
                "max": max_v,
                "mean": mean_v,
                "std": std_v if std_v > 1e-9 else 1.0,
            }

        normalized_results = []
        for c in candidates:
            norm_dict = {}
            for m in metrics:
                raw_val = c.raw_metrics.get(m.name, 0.0)
                st = stats[m.name]
                direction = m.direction.lower()

                if method == "z_score":
                    if direction == "maximize":
                        score = (raw_val - st["mean"]) / st["std"]
                    else:  # minimize
                        score = (st["mean"] - raw_val) / st["std"]
                else:  # default min_max
                    range_v = st["max"] - st["min"]
                    if range_v <= 1e-9:
                        score = 1.0  # Equal values across candidates
                    else:
                        if direction == "maximize":
                            score = (raw_val - st["min"]) / range_v
                        else:  # minimize
                            score = (st["max"] - raw_val) / range_v

                norm_dict[m.name] = score

            normalized_results.append(
                NormalizedMetricResult(
                    experiment_id=c.experiment_id,
                    normalized_metrics=norm_dict,
                )
            )

        return normalized_results
