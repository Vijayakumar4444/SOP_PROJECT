from __future__ import annotations

from math import isfinite, sqrt
from statistics import median
from typing import Any

from backend.app.modules.calibration.utils import rounded, to_float


def weight_diagnostics(rows: list[dict[str, Any]], weight_column: str) -> dict[str, Any]:
    weights = [to_float(row.get(weight_column), 0.0) or 0.0 for row in rows]
    n = len(weights)
    total = sum(weights)
    mean = total / n if n else 0.0
    variance = sum((weight - mean) ** 2 for weight in weights) / (n - 1) if n > 1 else 0.0
    std = sqrt(variance)
    ess = effective_sample_size(weights)
    invalid = [weight for weight in weights if not isfinite(weight)]
    negatives = [weight for weight in weights if weight < 0]
    return {
        "weight_column": weight_column,
        "nominal_sample_size": n,
        "weight_sum": rounded(total),
        "min_weight": rounded(min(weights) if weights else 0.0),
        "max_weight": rounded(max(weights) if weights else 0.0),
        "mean_weight": rounded(mean),
        "median_weight": rounded(median(weights) if weights else 0.0),
        "std_weight": rounded(std),
        "coefficient_of_variation": rounded(std / mean if mean else 0.0),
        "effective_sample_size": rounded(ess),
        "ess_ratio": rounded(ess / n if n else 0.0),
        "invalid_weight_count": len(invalid),
        "negative_weight_count": len(negatives),
    }


def effective_sample_size(weights: list[float]) -> float:
    denominator = sum(weight * weight for weight in weights)
    return (sum(weights) ** 2) / denominator if denominator else 0.0
