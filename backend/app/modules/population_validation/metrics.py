from __future__ import annotations

from collections import Counter, defaultdict
from math import log2, sqrt
from typing import Any


MISSING_VALUES = {"", None}


def is_missing(value: Any) -> bool:
    return value in MISSING_VALUES


def to_float(value: Any) -> float | None:
    if is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def numeric_values(rows: list[dict[str, Any]], column: str) -> list[float]:
    return [value for value in (to_float(row.get(column)) for row in rows) if value is not None]


def categorical_values(rows: list[dict[str, Any]], column: str) -> list[str]:
    return [str(row.get(column) if not is_missing(row.get(column)) else "Missing") for row in rows]


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def median(values: list[float]) -> float | None:
    return quantile(values, 0.5)


def stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    avg = mean(values)
    if avg is None:
        return None
    return sqrt(sum((value - avg) ** 2 for value in values) / (len(values) - 1))


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = probability * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def numeric_summary(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    values = numeric_values(rows, column)
    total = len(rows)
    missing = total - len(values)
    return {
        "count": len(values),
        "missing_count": missing,
        "missing_percentage": round(missing / total * 100, 4) if total else 0,
        "mean": rounded(mean(values)),
        "median": rounded(median(values)),
        "std": rounded(stdev(values)),
        "min": rounded(min(values)) if values else None,
        "max": rounded(max(values)) if values else None,
        "quantiles": {
            "p05": rounded(quantile(values, 0.05)),
            "p25": rounded(quantile(values, 0.25)),
            "p50": rounded(quantile(values, 0.50)),
            "p75": rounded(quantile(values, 0.75)),
            "p95": rounded(quantile(values, 0.95)),
        },
    }


def categorical_summary(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    total = len(rows)
    missing = sum(1 for row in rows if is_missing(row.get(column)))
    counts = Counter(categorical_values(rows, column))
    return {
        "count": total - missing,
        "missing_count": missing,
        "missing_percentage": round(missing / total * 100, 4) if total else 0,
        "category_counts": dict(sorted(counts.items())),
        "category_proportions": {key: round(value / total, 6) for key, value in sorted(counts.items())} if total else {},
    }


def ks_statistic(reference: list[float], synthetic: list[float]) -> float | None:
    if not reference or not synthetic:
        return None
    ref_counts = Counter(reference)
    syn_counts = Counter(synthetic)
    ref_seen = 0
    syn_seen = 0
    best = 0.0
    for value in sorted(set(ref_counts) | set(syn_counts)):
        ref_seen += ref_counts.get(value, 0)
        syn_seen += syn_counts.get(value, 0)
        best = max(best, abs(ref_seen / len(reference) - syn_seen / len(synthetic)))
    return best


def wasserstein_distance(reference: list[float], synthetic: list[float]) -> float | None:
    if not reference or not synthetic:
        return None
    ref_counts = Counter(reference)
    syn_counts = Counter(synthetic)
    values = sorted(set(ref_counts) | set(syn_counts))
    if len(values) < 2:
        return 0.0
    ref_seen = 0
    syn_seen = 0
    total = 0.0
    for index, value in enumerate(values[:-1]):
        ref_seen += ref_counts.get(value, 0)
        syn_seen += syn_counts.get(value, 0)
        width = values[index + 1] - value
        total += abs(ref_seen / len(reference) - syn_seen / len(synthetic)) * width
    return total


def proportions(values: list[str]) -> dict[str, float]:
    total = len(values)
    counts = Counter(values)
    return {key: value / total for key, value in counts.items()} if total else {}


def total_variation_distance(reference: dict[str, float], synthetic: dict[str, float]) -> float:
    keys = set(reference) | set(synthetic)
    return 0.5 * sum(abs(reference.get(key, 0.0) - synthetic.get(key, 0.0)) for key in keys)


def jensen_shannon_divergence(reference: dict[str, float], synthetic: dict[str, float]) -> float:
    keys = set(reference) | set(synthetic)
    midpoint = {key: (reference.get(key, 0.0) + synthetic.get(key, 0.0)) / 2 for key in keys}
    return 0.5 * kl_divergence(reference, midpoint) + 0.5 * kl_divergence(synthetic, midpoint)


def kl_divergence(left: dict[str, float], right: dict[str, float]) -> float:
    total = 0.0
    for key, left_value in left.items():
        right_value = right.get(key, 0.0)
        if left_value > 0 and right_value > 0:
            total += left_value * log2(left_value / right_value)
    return total


def pearson(x_values: list[float], y_values: list[float]) -> float | None:
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None
    mean_x = mean(x_values)
    mean_y = mean(y_values)
    if mean_x is None or mean_y is None:
        return None
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
    denom_x = sqrt(sum((x - mean_x) ** 2 for x in x_values))
    denom_y = sqrt(sum((y - mean_y) ** 2 for y in y_values))
    denominator = denom_x * denom_y
    return numerator / denominator if denominator else None


def ranks(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    out = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[cursor][0]:
            end += 1
        rank = (cursor + end) / 2 + 1
        for _, index in ordered[cursor:end + 1]:
            out[index] = rank
        cursor = end + 1
    return out


def spearman(x_values: list[float], y_values: list[float]) -> float | None:
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None
    return pearson(ranks(x_values), ranks(y_values))


def paired_numeric(rows: list[dict[str, Any]], left: str, right: str) -> tuple[list[float], list[float]]:
    x_values: list[float] = []
    y_values: list[float] = []
    for row in rows:
        x = to_float(row.get(left))
        y = to_float(row.get(right))
        if x is not None and y is not None:
            x_values.append(x)
            y_values.append(y)
    return x_values, y_values


def cramers_v(rows: list[dict[str, Any]], left: str, right: str) -> float | None:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        a = str(row.get(left) if not is_missing(row.get(left)) else "Missing")
        b = str(row.get(right) if not is_missing(row.get(right)) else "Missing")
        table[a][b] += 1
    row_keys = sorted(table)
    col_keys = sorted({key for counts in table.values() for key in counts})
    n = sum(sum(counts.values()) for counts in table.values())
    if n == 0 or len(row_keys) < 2 or len(col_keys) < 2:
        return None
    row_totals = {row_key: sum(table[row_key].values()) for row_key in row_keys}
    col_totals = {col_key: sum(table[row_key].get(col_key, 0) for row_key in row_keys) for col_key in col_keys}
    chi_square = 0.0
    for row_key in row_keys:
        for col_key in col_keys:
            expected = row_totals[row_key] * col_totals[col_key] / n
            if expected:
                observed = table[row_key].get(col_key, 0)
                chi_square += (observed - expected) ** 2 / expected
    denom = n * min(len(row_keys) - 1, len(col_keys) - 1)
    return sqrt(chi_square / denom) if denom else None


def correlation_ratio(rows: list[dict[str, Any]], category_column: str, numeric_column: str) -> float | None:
    groups: dict[str, list[float]] = defaultdict(list)
    all_values: list[float] = []
    for row in rows:
        value = to_float(row.get(numeric_column))
        if value is None:
            continue
        category = str(row.get(category_column) if not is_missing(row.get(category_column)) else "Missing")
        groups[category].append(value)
        all_values.append(value)
    if len(all_values) < 2 or len(groups) < 2:
        return None
    grand_mean = mean(all_values)
    if grand_mean is None:
        return None
    between = 0.0
    total = 0.0
    for values in groups.values():
        group_mean = mean(values)
        if group_mean is not None:
            between += len(values) * (group_mean - grand_mean) ** 2
    total = sum((value - grand_mean) ** 2 for value in all_values)
    return sqrt(between / total) if total else None


def rounded(value: float | None, digits: int = 6) -> float | None:
    return round(value, digits) if value is not None else None


def bounded_score(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, value))
