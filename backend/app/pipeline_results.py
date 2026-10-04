"""Map completed backend pipeline artifacts into the frontend results contract."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def load_pipeline_result(base_result: dict[str, Any], root: Path = ROOT) -> dict[str, Any] | None:
    """Return a frontend-compatible result using completed phase artifacts.

    The dashboard already expects a rich result shape. Backend phases currently
    emit a smaller set of factual metrics, so this overlays real phase outputs
    on top of the existing generated dashboard shape.
    """

    recommendation_path = root / "artifacts" / "recommendation" / "recommendation_summary.json"
    if not recommendation_path.exists():
        return None

    recommendation = _read_json(recommendation_path)
    top_experiment = recommendation.get("top_recommended_candidate")
    if not top_experiment:
        rankings = recommendation.get("rankings") or []
        top_experiment = rankings[0].get("experiment_id") if rankings else None
    if not top_experiment:
        return None

    experiment_root = root / "artifacts" / "experiments" / str(top_experiment)
    uncertainty_path = experiment_root / "uncertainty_summary.json"
    if not uncertainty_path.exists():
        return None

    uncertainty = _read_json(uncertainty_path)
    fairness = _optional_json(root / "artifacts" / "recommendation" / "fairness_report.json")
    risk = _optional_json(experiment_root / "risk_probabilities.json")
    return build_pipeline_result(base_result, recommendation, uncertainty, fairness, risk, top_experiment)


def build_pipeline_result(
    base_result: dict[str, Any],
    recommendation: dict[str, Any],
    uncertainty: dict[str, Any],
    fairness: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
    top_experiment: str | None = None,
) -> dict[str, Any]:
    result = deepcopy(base_result)
    metrics = uncertainty.get("metrics_summary") or {}
    top_experiment = top_experiment or recommendation.get("top_recommended_candidate")
    top_ranking = _find_experiment(recommendation.get("rankings") or [], top_experiment)
    top_fairness = _find_experiment(fairness.get("fairness_results") or [], top_experiment) if fairness else {}

    cost = _metric(metrics, "total_policy_cost")
    beneficiaries = _metric(metrics, "beneficiary_count")
    weighted_beneficiaries = _metric(metrics, "weighted_beneficiary_population")
    eligible = _metric(metrics, "weighted_eligible_population") or _metric(metrics, "eligible_count")
    coverage_rate = _metric(metrics, "coverage_rate")
    budget_utilization = _metric(metrics, "budget_utilization")
    overrun_probability = _budget_exceedance_probability(recommendation, top_ranking, risk)
    fairness_score = _fairness_score(top_fairness, result)

    mean_cost = _number(cost.get("mean"), result["budget"]["meanCost"])
    median_cost = _number(cost.get("median"), mean_cost)
    p5_cost = _percentile(cost, "p5", mean_cost)
    p95_cost = _percentile(cost, "p95", mean_cost)
    beneficiary_count = round(_number(beneficiaries.get("mean"), result["beneficiary"]["beneficiaries"]))
    eligible_population = round(_number(eligible.get("mean"), result["beneficiary"]["eligiblePopulation"]))
    target_population = max(eligible_population, beneficiary_count, result["beneficiary"]["targetPopulation"])
    coverage = _clamp(_number(coverage_rate.get("mean"), result["beneficiary"]["coverage"]), 0.0, 1.0)
    utilization = _clamp(_number(budget_utilization.get("mean"), result["budget"]["utilization"]), 0.0, 5.0)
    allocated_budget = _allocated_budget(recommendation, top_ranking, mean_cost, utilization, result["budget"]["allocatedBudget"])
    risk_score = _risk_score(utilization, overrun_probability, top_ranking)
    risk_level = _risk_level(risk_score)
    classification = "Success" if bool(top_ranking.get("is_feasible")) else "Moderate"

    result["simulation"].update(
        {
            "beneficiaryCoverage": coverage,
            "estimatedCost": mean_cost,
            "equityScore": fairness_score,
            "budgetRisk": risk_level,
            "status": "completed",
        }
    )
    result["beneficiary"].update(
        {
            "coverage": coverage,
            "beneficiaries": beneficiary_count,
            "targetFit": _target_fit_from_backend(top_ranking, coverage, fairness_score),
            "eligiblePopulation": eligible_population,
            "targetPopulation": target_population,
            "nonEligiblePopulation": max(0, target_population - beneficiary_count),
        }
    )
    result["budget"].update(
        {
            "allocatedBudget": allocated_budget,
            "meanCost": mean_cost,
            "unusedBudget": allocated_budget - mean_cost,
            "costPerBeneficiary": round(mean_cost / max(beneficiary_count, 1)),
            "probabilityOverrun": overrun_probability,
            "worstCaseCost": p95_cost,
            "utilization": utilization,
            "riskScore": risk_score,
            "riskLevel": risk_level,
        }
    )
    result["monteCarlo"].update(
        {
            "mean": mean_cost,
            "median": median_cost,
            "p5": p5_cost,
            "p95": p95_cost,
            "budget": allocated_budget,
            "overrunProbability": overrun_probability,
            "buckets": _backend_buckets(cost, mean_cost),
        }
    )
    result["confidenceIntervals"] = _confidence_intervals(result["confidenceIntervals"], metrics, mean_cost, beneficiary_count, coverage)
    result["equity"].update(
        {
            "overall": fairness_score,
            "gender": _score_from_disparity(top_fairness.get("gender_disparity"), result["equity"]["gender"]),
            "district": _score_from_disparity(top_fairness.get("district_disparity"), result["equity"]["district"]),
            "explanation": "Scores include completed backend recommendation and fairness artifacts.",
        }
    )
    _apply_fairness_breakdowns(result, top_fairness, beneficiary_count)
    result["interpretation"] = _interpretation(recommendation, top_ranking, classification, mean_cost, beneficiary_count, overrun_probability)
    result["backendOutput"] = {
        "source": "pipeline_artifacts",
        "recommendationId": recommendation.get("recommendation_id"),
        "topRecommendedCandidate": top_experiment,
        "totalCandidates": recommendation.get("total_candidates"),
        "feasibleCandidates": recommendation.get("feasible_candidates_count"),
        "generatedAt": recommendation.get("generated_at"),
    }
    return result


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_json(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.exists() else None


def _find_experiment(items: list[dict[str, Any]], experiment_id: str | None) -> dict[str, Any]:
    for item in items:
        if item.get("experiment_id") == experiment_id:
            return item
    return items[0] if items else {}


def _metric(metrics: dict[str, Any], name: str) -> dict[str, Any]:
    value = metrics.get(name)
    return value if isinstance(value, dict) else {}


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _percentile(metric: dict[str, Any], percentile: str, default: float) -> float:
    percentiles = metric.get("percentiles") or {}
    return _number(percentiles.get(percentile), default)


def _allocated_budget(recommendation: dict[str, Any], ranking: dict[str, Any], mean_cost: float, utilization: float, default: float) -> float:
    max_budget = (((recommendation.get("feasibility_checks") or [{}])[0]).get("evaluated_constraints") or {}).get("max_budget") or {}
    if ranking:
        for check in recommendation.get("feasibility_checks") or []:
            if check.get("experiment_id") == ranking.get("experiment_id"):
                max_budget = (check.get("evaluated_constraints") or {}).get("max_budget") or max_budget
                break
    threshold = _number(max_budget.get("threshold"), 0)
    if threshold > 0:
        return threshold
    if utilization > 0:
        return mean_cost / utilization
    return default


def _budget_exceedance_probability(
    recommendation: dict[str, Any], ranking: dict[str, Any], risk: dict[str, Any] | None
) -> float:
    raw_metrics = ranking.get("raw_metrics") or {}
    if "budget_exceedance_risk" in raw_metrics:
        return _clamp(_number(raw_metrics.get("budget_exceedance_risk"), 0), 0.0, 1.0)
    if risk:
        for item in (risk.get("risk_metrics") or {}).values():
            if "cost" in str(item.get("metric", "")):
                return _clamp(_number(item.get("estimated_probability"), 0), 0.0, 1.0)
    return 0.0


def _fairness_score(fairness_item: dict[str, Any], result: dict[str, Any]) -> int:
    score = fairness_item.get("overall_fairness_score")
    if score is None:
        return int(result["equity"]["overall"])
    return round(_clamp(_number(score, 0.0), 0.0, 1.0) * 100)


def _score_from_disparity(disparity: Any, default: int) -> int:
    value = _number(disparity, 0)
    if value <= 0:
        return default
    return round(_clamp(100 - (value - 1) * 35, 35, 100))


def _risk_score(utilization: float, overrun_probability: float, ranking: dict[str, Any]) -> int:
    relative_error = _number((ranking.get("raw_metrics") or {}).get("relative_mc_error"), 0)
    return round(_clamp(utilization * 45 + overrun_probability * 45 + relative_error * 80, 1, 100))


def _risk_level(risk_score: int) -> str:
    if risk_score >= 75:
        return "Critical"
    if risk_score >= 55:
        return "High"
    if risk_score >= 30:
        return "Moderate"
    return "Low"


def _target_fit_from_backend(ranking: dict[str, Any], coverage: float, fairness_score: int) -> int:
    feasibility_bonus = 12 if ranking.get("is_feasible") else -8
    score = 55 + coverage * 18 + fairness_score * 0.18 + feasibility_bonus
    return round(_clamp(score, 0, 100))


def _backend_buckets(cost_metric: dict[str, Any], mean_cost: float) -> list[dict[str, int]]:
    percentiles = cost_metric.get("percentiles") or {}
    points = [
        _number(percentiles.get("p5"), mean_cost * 0.9),
        _number(percentiles.get("p25"), mean_cost * 0.96),
        _number(percentiles.get("p50"), mean_cost),
        _number(percentiles.get("p75"), mean_cost * 1.04),
        _number(percentiles.get("p95"), mean_cost * 1.1),
    ]
    buckets = []
    for index in range(4):
        lower = round(points[index])
        upper = round(max(points[index + 1], lower + 1))
        buckets.append({"lower": lower, "upper": upper, "frequency": [8, 24, 24, 8][index]})
    return buckets


def _confidence_intervals(
    existing: list[dict[str, Any]], metrics: dict[str, Any], mean_cost: float, beneficiaries: int, coverage: float
) -> list[dict[str, Any]]:
    intervals = list(existing)
    replacements = {
        "Beneficiaries": (_metric(metrics, "beneficiary_count"), beneficiaries, "number"),
        "Policy Cost": (_metric(metrics, "total_policy_cost"), mean_cost, "currency"),
        "Coverage": (_metric(metrics, "coverage_rate"), coverage, "percent"),
    }
    next_intervals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in intervals:
        metric_name = item.get("metric")
        if metric_name in replacements:
            metric, estimate, formatter = replacements[metric_name]
            next_intervals.append(_interval(metric_name, metric, estimate, formatter))
            seen.add(metric_name)
        else:
            next_intervals.append(item)
    for metric_name, (metric, estimate, formatter) in replacements.items():
        if metric_name not in seen:
            next_intervals.append(_interval(metric_name, metric, estimate, formatter))
    return next_intervals


def _interval(metric_name: str, metric: dict[str, Any], estimate: float, formatter: str) -> dict[str, Any]:
    ci = metric.get("mean_confidence_interval") or {}
    percentiles = metric.get("percentiles") or {}
    lower = ci.get("lower", percentiles.get("p5", estimate))
    upper = ci.get("upper", percentiles.get("p95", estimate))
    return {
        "metric": metric_name,
        "lower": _number(lower, estimate),
        "estimate": _number(metric.get("mean"), estimate),
        "upper": _number(upper, estimate),
        "formatter": formatter,
    }


def _apply_fairness_breakdowns(result: dict[str, Any], fairness_item: dict[str, Any], beneficiaries: int) -> None:
    breakdowns = fairness_item.get("group_breakdowns") or {}
    gender_share = breakdowns.get("gender_share") or {}
    if gender_share:
        result["demographics"]["gender"] = [
            {"category": "Female", "value": _number(gender_share.get("female"), 0.0)},
            {"category": "Male", "value": _number(gender_share.get("male"), 0.0)},
        ]
    districts = breakdowns.get("districts") or {}
    if districts:
        total = sum(_number(value, 0) for value in districts.values()) or 1
        for district_result in result["districts"]:
            value = districts.get(district_result["district"])
            if value is None:
                continue
            share = _number(value, 0) / total
            district_beneficiaries = round(beneficiaries * share)
            district_result["beneficiaries"] = district_beneficiaries
            district_result["eligiblePopulation"] = max(district_beneficiaries, district_result["eligiblePopulation"])
            district_result["coverage"] = _clamp(district_beneficiaries / max(district_result["eligiblePopulation"], 1), 0, 1)
            district_result["estimatedCost"] = district_beneficiaries * district_result["costPerBeneficiary"]


def _interpretation(
    recommendation: dict[str, Any],
    ranking: dict[str, Any],
    classification: str,
    mean_cost: float,
    beneficiaries: int,
    overrun_probability: float,
) -> dict[str, Any]:
    explanations = recommendation.get("explanations") or []
    summary = explanations[0] if explanations else (
        f"Completed backend pipeline estimates cost at Rs {mean_cost:,.0f} for {beneficiaries:,.0f} beneficiaries."
    )
    strengths = [
        f"Recommendation engine ranked {ranking.get('display_name', 'the selected option')} as the top candidate.",
        f"Expected beneficiary coverage is {beneficiaries:,.0f}.",
    ]
    if ranking.get("is_feasible"):
        strengths.append("All evaluated feasibility constraints passed.")
    concerns = [item for item in explanations if item.startswith("FEASIBILITY EXCLUSION")]
    if overrun_probability > 0:
        concerns.insert(0, f"Budget exceedance probability is {overrun_probability * 100:.1f}%.")
    return {
        "classification": classification,
        "summary": summary,
        "strengths": strengths,
        "concerns": concerns[:3] or ["No major critical concerns detected in completed backend artifacts."],
    }


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))
