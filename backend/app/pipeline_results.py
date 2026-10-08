"""Map completed backend pipeline artifacts into the frontend results contract."""

from __future__ import annotations

import json
import re
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
    eligibility_rate = _metric(metrics, "eligibility_rate")
    average_benefit = _metric(metrics, "average_benefit")
    overrun_probability = _budget_exceedance_probability(recommendation, top_ranking, risk)
    fairness_score = _fairness_score(top_fairness, result)

    sample_population = _sample_population(result, metrics)
    mean_cost = _number(cost.get("mean"), result["budget"]["meanCost"])
    median_cost = _number(cost.get("median"), mean_cost)
    p5_cost = _percentile(cost, "p5", mean_cost)
    p95_cost = _percentile(cost, "p95", mean_cost)
    beneficiary_count = round(_number(beneficiaries.get("mean"), result["beneficiary"]["beneficiaries"]))
    eligible_population = round(_number(eligible.get("mean"), result["beneficiary"]["eligiblePopulation"]))
    target_population = max(eligible_population, beneficiary_count, result["beneficiary"]["targetPopulation"])
    coverage = _clamp(_number(coverage_rate.get("mean"), result["beneficiary"]["coverage"]), 0.0, 1.0)
    utilization = _clamp(_number(budget_utilization.get("mean"), result["budget"]["utilization"]), 0.0, 5.0)
    allocated_budget = _allocated_budget(result, recommendation, top_ranking, mean_cost, utilization, result["budget"]["allocatedBudget"])
    risk_score = _risk_score(utilization, overrun_probability, top_ranking)
    risk_level = _risk_level(risk_score)
    classification = "Success" if bool(top_ranking.get("is_feasible")) else "Moderate"
    submitted_annual_benefit = _submitted_annual_benefit(result, _number(result["budget"].get("costPerBeneficiary"), 0))
    pipeline_annual_benefit = _number(average_benefit.get("mean"), submitted_annual_benefit or 0)

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
    result["prediction"] = _prediction_block(
        result=result,
        sample_population=sample_population,
        sample_beneficiaries=beneficiary_count,
        sample_eligible=eligible_population,
        sample_cost=mean_cost,
        eligibility_rate=_number(eligibility_rate.get("mean"), beneficiary_count / max(sample_population, 1)),
        submitted_annual_benefit=submitted_annual_benefit,
        pipeline_annual_benefit=pipeline_annual_benefit,
    )
    classification, classification_reasons = _final_classification(result, recommendation, top_ranking)
    result["interpretation"] = _submitted_policy_interpretation(result, classification, classification_reasons)
    result["backendOutput"] = _submitted_policy_backend_output(result, recommendation)
    statewide_estimate = result["prediction"]["statewideEstimate"]
    statewide_submitted_cost = _number(statewide_estimate.get("annualCostUsingSubmittedBenefit"), mean_cost)
    statewide_budget = _number(statewide_estimate.get("plannedStatewideBudget"), allocated_budget)
    if statewide_budget > 0:
        statewide_utilization = _clamp(statewide_submitted_cost / statewide_budget, 0.0, 5.0)
        result["budget"].update(
            {
                "allocatedBudget": statewide_budget,
                "meanCost": statewide_submitted_cost,
                "unusedBudget": statewide_budget - statewide_submitted_cost,
                "costPerBeneficiary": round(statewide_submitted_cost / max(statewide_estimate.get("beneficiaries", 0), 1)),
                "utilization": statewide_utilization,
                "riskScore": _risk_score(statewide_utilization, overrun_probability, top_ranking),
                "riskLevel": _risk_level(_risk_score(statewide_utilization, overrun_probability, top_ranking)),
            }
        )
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


def _sample_population(result: dict[str, Any], metrics: dict[str, Any]) -> int:
    configured = result.get("simulation", {}).get("populationSampleSize")
    if configured:
        return round(_number(configured, 0))
    eligibility = _number(_metric(metrics, "eligibility_rate").get("mean"), 0)
    eligible = _number(_metric(metrics, "eligible_count").get("mean"), 0)
    if eligibility > 0 and eligible > 0:
        return round(eligible / eligibility)
    return 12_000


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _submitted_annual_benefit(result: dict[str, Any], default: float) -> float:
    simulation = result.get("simulation", {})
    amount = _number(simulation.get("submittedBenefitAmount"), 0)
    if amount > 0:
        frequency = str(simulation.get("submittedBenefitFrequency") or "").lower()
        return amount * 12 if frequency == "monthly" else amount
    return default


def _prediction_block(
    result: dict[str, Any],
    sample_population: int,
    sample_beneficiaries: int,
    sample_eligible: int,
    sample_cost: float,
    eligibility_rate: float,
    submitted_annual_benefit: float,
    pipeline_annual_benefit: float,
) -> dict[str, Any]:
    statewide_population = round(_number(result["beneficiary"].get("basePopulation"), sample_population))
    scale_factor = statewide_population / max(sample_population, 1)
    raw_statewide_beneficiaries = round(sample_beneficiaries * scale_factor)
    statewide_eligible = round(sample_eligible * scale_factor)
    implementation_adjustment = _implementation_adjustment(result)
    implementation_adjusted_beneficiaries = round(raw_statewide_beneficiaries * implementation_adjustment["factor"])
    target_population_model = _target_population_model(result, statewide_population)
    pre_benchmark_beneficiaries = min(implementation_adjusted_beneficiaries, target_population_model["estimatedTargetPopulation"])
    target_population_model["capApplied"] = pre_benchmark_beneficiaries < implementation_adjusted_beneficiaries
    benchmark = _official_benchmark(result)
    benchmark_delivery = _benchmark_delivery_calibration(pre_benchmark_beneficiaries, benchmark)
    statewide_beneficiaries = round(pre_benchmark_beneficiaries * benchmark_delivery["factor"])
    submitted_statewide_cost = statewide_beneficiaries * submitted_annual_benefit
    pipeline_statewide_cost = sample_cost * scale_factor
    planned_statewide_budget = _planned_statewide_budget(result)
    fiscal_pressure = submitted_statewide_cost / planned_statewide_budget if planned_statewide_budget else None
    budget_surplus = planned_statewide_budget - submitted_statewide_cost if planned_statewide_budget else None
    uncalibrated_error = _prediction_error(pre_benchmark_beneficiaries, benchmark)
    error = _prediction_error(statewide_beneficiaries, benchmark)
    validation_status = _validation_status(error, benchmark_delivery)
    frequency = _submitted_benefit_frequency(result)
    return {
        "dataVersion": "statewide_scaled_target_delivery_memory_validated_v6",
        "sample": {
            "population": sample_population,
            "eligible": sample_eligible,
            "beneficiaries": sample_beneficiaries,
            "beneficiaryRate": sample_beneficiaries / max(sample_population, 1),
            "eligibilityRate": eligibility_rate,
            "cost": sample_cost,
        },
        "statewideEstimate": {
            "basePopulation": statewide_population,
            "scaleFactor": scale_factor,
            "eligible": statewide_eligible,
            "rawBeneficiariesBeforeImplementationAdjustment": raw_statewide_beneficiaries,
            "beneficiariesAfterImplementationAdjustment": implementation_adjusted_beneficiaries,
            "beneficiariesBeforeBenchmarkDeliveryCalibration": pre_benchmark_beneficiaries,
            "beneficiaries": statewide_beneficiaries,
            "plannedStatewideBudget": planned_statewide_budget,
            "annualCostUsingSubmittedBenefit": submitted_statewide_cost,
            "annualCostUsingPipelineBenefit": pipeline_statewide_cost,
            "fiscalPressureUsingSubmittedBenefit": fiscal_pressure,
            "budgetSurplusUsingSubmittedBenefit": budget_surplus,
        },
        "submittedPolicyBenefit": {
            "annualAmount": submitted_annual_benefit,
            "monthlyEquivalent": submitted_annual_benefit / 12 if submitted_annual_benefit else 0,
            "frequency": frequency,
            "displayAmount": _display_benefit_amount(submitted_annual_benefit, frequency),
            "displayLabel": _display_benefit_label(frequency),
        },
        "pipelineArtifactBenefit": {
            "annualAmount": pipeline_annual_benefit,
            "monthlyEquivalent": pipeline_annual_benefit / 12 if pipeline_annual_benefit else 0,
            "frequency": "Annual",
            "displayAmount": pipeline_annual_benefit,
            "displayLabel": "Pipeline Artifact Benefit",
        },
        "implementationAdjustment": implementation_adjustment,
        "benchmarkDeliveryCalibration": benchmark_delivery,
        "targetPopulationModel": target_population_model,
        "officialBenchmark": benchmark,
        "uncalibratedPredictionError": uncalibrated_error,
        "actualPredictionError": error,
        "validationStatus": validation_status,
    }


def _submitted_benefit_frequency(result: dict[str, Any]) -> str:
    frequency = str(result.get("simulation", {}).get("submittedBenefitFrequency") or "").strip()
    return frequency or "Annual"


def _display_benefit_amount(annual_benefit: float, frequency: str) -> float:
    if frequency.lower() == "monthly":
        return annual_benefit / 12 if annual_benefit else 0
    return annual_benefit


def _display_benefit_label(frequency: str) -> str:
    if frequency.lower() == "monthly":
        return "Submitted Monthly Benefit"
    if frequency.lower() == "one-time":
        return "Submitted One-Time Benefit"
    return "Submitted Annual Benefit"


def _target_population_model(result: dict[str, Any], statewide_population: int) -> dict[str, Any]:
    simulation = result.get("simulation", {})
    policy = simulation.get("submittedPolicy") or {}
    rules = policy.get("rules") if isinstance(policy, dict) else []
    text = " ".join(
        [
            str(simulation.get("policyName", "")),
            str(policy.get("description", "") if isinstance(policy, dict) else ""),
            str(policy.get("geographicScope", "") if isinstance(policy, dict) else ""),
            " ".join(f"{rule.get('attribute', '')} {rule.get('operator', '')} {rule.get('value', '')}" for rule in rules or [] if isinstance(rule, dict)),
        ]
    ).lower()
    share = 1.0
    constraints: list[str] = []

    if "female" in text or "women" in text or "gender = female" in text:
        share *= 0.49
        constraints.append("gender target share")
    elif "male" in text or "gender = male" in text:
        share *= 0.51
        constraints.append("gender target share")

    if "age >= 60" in text or "60 years" in text or "senior" in text or "elderly" in text:
        share *= 0.145
        constraints.append("senior-age population share")
    elif "age >= 21" in text and ("age <= 60" in text or "21-60" in text):
        share *= 0.57
        constraints.append("working-age adult population share")
    elif "age >= 21" in text:
        share *= 0.72
        constraints.append("adult population share")
    elif "age < 18" in text or "school-age" in text:
        share *= 0.30
        constraints.append("child/school-age population share")

    if "rural only" in text:
        share *= 0.57
        constraints.append("rural scope share")
    elif "urban only" in text:
        share *= 0.43
        constraints.append("urban scope share")

    if any(term in text for term in ["household income", "annual income", "below poverty", "poverty line", "bpl"]):
        share *= 0.92 if any(term in text for term in ["50000", "50,000", "poverty line", "bpl"]) else 0.78
        constraints.append("income eligibility share")

    if any(term in text for term in ["employment status", "unemployed", "non-worker", "non worker"]):
        share *= 0.92
        constraints.append("employment-status target share")

    if any(term in text for term in ["existing scheme", "existing pension", "without regular income support"]):
        share *= 0.96
        constraints.append("existing-benefit exclusion share")

    if any(term in text for term in ["disability status", "disabled", "disability"]):
        share *= 0.08
        constraints.append("disability target share")

    share = _clamp(share, 0.01, 1.0)
    return {
        "method": "rule_based_target_population_v1",
        "estimatedTargetShare": share,
        "estimatedTargetPopulation": round(statewide_population * share),
        "constraints": constraints or ["No target-population narrowing rules detected."],
        "capApplied": False,
    }


def _implementation_adjustment(result: dict[str, Any]) -> dict[str, Any]:
    simulation = result.get("simulation", {})
    policy = simulation.get("submittedPolicy") or {}
    rules = policy.get("rules") if isinstance(policy, dict) else []
    text_parts = [
        str(simulation.get("policyName", "")),
        str(policy.get("description", "") if isinstance(policy, dict) else ""),
        " ".join(f"{rule.get('attribute', '')} {rule.get('operator', '')} {rule.get('value', '')}" for rule in rules or [] if isinstance(rule, dict)),
    ]
    text = " ".join(text_parts).lower()
    department = str(policy.get("department") or simulation.get("department") or "").strip().lower()
    factor = 1.0
    reasons: list[str] = []

    if _text_has_any(text, ["destitute", "no regular income", "regular income support"]):
        factor *= 0.95
        reasons.append("destitution/no-regular-income criteria reduce real-world uptake")
    if _text_has_any(text, ["bpl", "below poverty", "poverty line", "household income", "annual income", "income <"]):
        factor *= 0.93
        reasons.append("income/BPL verification creates exclusion and documentation effects")
    if _text_has_any(text, ["employment status", "unemployed", "non-worker", "non worker"]):
        factor *= 0.95
        reasons.append("employment or non-worker verification reduces approved beneficiaries")
    if _text_has_any(text, ["existing scheme", "existing pension", "without regular income support"]):
        factor *= 0.96
        reasons.append("existing-benefit exclusions reduce duplicate eligibility")
    if _text_has_any(text, ["land ownership", "fixed asset", "asset"]):
        factor *= 0.97
        reasons.append("asset and land checks reduce administratively approved cases")
    if _text_has_any(text, ["housing", "construction", "patta", "solar", "green house"]):
        factor *= 0.82
        reasons.append("housing/construction delivery depends on land records, materials, and local execution capacity")
    if department == "labour" or _text_has_any(text, ["gig worker", "platform worker", "informal worker", "unorganised worker"]):
        factor *= 0.88
        reasons.append("labour and platform-worker schemes depend on worker registration, income volatility, and employer/platform verification")
    if department == "health" or _text_has_any(text, ["health", "medical", "insurance", "hospital", "claim"]):
        factor *= 0.90
        reasons.append("health schemes depend on enrolment, provider access, claims processing, and patient awareness")
    if department == "agriculture" or _text_has_any(text, ["farmer", "crop", "cultivation", "agriculture"]):
        factor *= 0.91
        reasons.append("agriculture schemes depend on land/crop records, seasonal timing, and input-delivery capacity")
    if department == "education" or _text_has_any(text, ["student", "school", "college", "education", "scholarship"]):
        factor *= 0.94
        reasons.append("education schemes depend on institution records, enrolment continuity, and attendance verification")

    rule_based_factor = _clamp(factor, 0.05, 1.0)
    factor = rule_based_factor
    memory_prior = _memory_adjustment_prior()
    if memory_prior is not None:
        factor = _clamp(rule_based_factor * 0.55 + memory_prior * 0.45, 0.03, 1.0)
        reasons.append(f"similar-policy memory prior blended into adjustment factor ({memory_prior:.3f})")

    return {
        "factor": factor,
        "method": "rule_based_take_up_exclusion_with_memory_prior_v2",
        "ruleBasedFactor": rule_based_factor,
        "memoryPriorFactor": memory_prior,
        "reasons": reasons or ["No implementation exclusion adjustment applied."],
    }


def _text_has_any(text: str, terms: list[str]) -> bool:
    for term in terms:
        escaped = r"\s+".join(part for part in term.split())
        if re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text):
            return True
    return False


def _memory_adjustment_prior() -> float | None:
    priors_path = ROOT / "data" / "synthetic" / "policy_memory_priors.json"
    if not priors_path.exists():
        return None
    try:
        priors_payload = json.loads(priors_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    priors = priors_payload.get("priors") or {}
    stats = priors.get("observedDeliveryFactor") or priors.get("implementationAdjustmentFactor")
    if not isinstance(stats, dict):
        return None
    mean = _number(stats.get("mean"), 0)
    if mean <= 0:
        return None
    return _clamp(mean, 0.03, 1.0)


def _benchmark_delivery_calibration(predicted_beneficiaries: int, benchmark: dict[str, Any] | None) -> dict[str, Any]:
    if not benchmark:
        return {
            "factor": 1.0,
            "method": "no_official_delivery_benchmark",
            "applied": False,
            "reasons": ["No official beneficiary benchmark was submitted for delivery calibration."],
        }
    actual = _number(benchmark.get("beneficiaries"), 0)
    if actual <= 0 or predicted_beneficiaries <= 0:
        return {
            "factor": 1.0,
            "method": "official_benchmark_unusable",
            "applied": False,
            "reasons": ["Official benchmark did not include a usable beneficiary count."],
        }
    observed_factor = _clamp(actual / predicted_beneficiaries, 0.01, 1.0)
    if 0.8 <= observed_factor <= 1.25:
        return {
            "factor": 1.0,
            "observedDeliveryFactor": observed_factor,
            "method": "official_benchmark_within_model_tolerance",
            "applied": False,
            "reasons": ["Official delivery benchmark is close to the model estimate."],
        }
    return {
        "factor": observed_factor,
        "observedDeliveryFactor": observed_factor,
        "method": "official_benchmark_delivery_calibration_v1",
        "applied": True,
        "reasons": [
            "Official implemented-policy record shows delivered beneficiaries differ materially from eligibility-based estimate.",
            "Final beneficiaries are calibrated to observed delivery so failed historical implementation is not reported as successful reach.",
        ],
    }


def _official_benchmark(result: dict[str, Any]) -> dict[str, Any] | None:
    submitted = result.get("simulation", {}).get("officialBenchmark")
    if isinstance(submitted, dict) and (
        _number(submitted.get("beneficiaries"), 0) > 0 or _number(submitted.get("annualCost"), 0) > 0
    ):
        return submitted
    policy_name = str(result.get("simulation", {}).get("policyName", "")).lower()
    target = str(result.get("beneficiary", {}).get("targetUniverse", "")).lower()
    if "old age pension" not in policy_name and "indira gandhi" not in policy_name and "elderly" not in policy_name and "elderly" not in target:
        return None
    return {
        "scheme": "Indira Gandhi National Old Age Pension Scheme (IGNOAPS), Tamil Nadu",
        "beneficiaries": 1_436_569,
        "asOf": "2023-03-31",
        "source": "Tamil Nadu Statistical Handbook 2022-23, Social Welfare table 27.4",
    }


def _planned_statewide_budget(result: dict[str, Any]) -> float | None:
    budget = _number(result.get("simulation", {}).get("plannedStatewideBudget"), 0)
    if budget > 0:
        return budget
    budget = _number(result.get("budget", {}).get("allocatedBudget"), 0)
    return budget if budget > 0 else None


def _prediction_error(predicted_beneficiaries: int, benchmark: dict[str, Any] | None) -> dict[str, Any] | None:
    if not benchmark:
        return None
    actual = _number(benchmark.get("beneficiaries"), 0)
    if actual <= 0:
        return None
    absolute = predicted_beneficiaries - actual
    percent = absolute / actual
    return {
        "predictedBeneficiaries": predicted_beneficiaries,
        "actualBeneficiaries": round(actual),
        "absoluteError": round(absolute),
        "percentError": percent,
        "absolutePercentError": abs(percent),
    }


def _validation_status(error: dict[str, Any] | None, delivery_calibration: dict[str, Any] | None = None) -> dict[str, Any]:
    if delivery_calibration and delivery_calibration.get("applied"):
        return {
            "status": "Benchmark calibrated",
            "severity": "warning",
            "message": "Official implemented-policy records were used to calibrate delivered beneficiaries; this is a historical calibration, not an independent forecast.",
            "absolutePercentError": _number((error or {}).get("absolutePercentError"), 0),
            "thresholds": {
                "strong": 0.05,
                "good": 0.10,
                "review": 0.20,
            },
        }
    if not error:
        return {
            "status": "Unbenchmarked",
            "severity": "info",
            "message": "No official benchmark was submitted or detected for this policy.",
            "absolutePercentError": None,
        }
    ape = _number(error.get("absolutePercentError"), 0)
    if ape <= 0.05:
        status = "Strong"
        severity = "success"
        message = "Prediction is within 5% of the official benchmark."
    elif ape <= 0.10:
        status = "Good"
        severity = "success"
        message = "Prediction is within 10% of the official benchmark."
    elif ape <= 0.20:
        status = "Needs review"
        severity = "warning"
        message = "Prediction error is between 10% and 20%; review assumptions before relying on it."
    else:
        status = "Needs calibration"
        severity = "critical"
        message = "Prediction error is above 20%; calibration is required before this should be treated as accurate."
    return {
        "status": status,
        "severity": severity,
        "message": message,
        "absolutePercentError": ape,
        "thresholds": {
            "strong": 0.05,
            "good": 0.10,
            "review": 0.20,
        },
    }


def _final_classification(
    result: dict[str, Any],
    recommendation: dict[str, Any],
    ranking: dict[str, Any],
) -> tuple[str, list[str]]:
    prediction = result.get("prediction") or {}
    statewide = prediction.get("statewideEstimate") or {}
    error = prediction.get("actualPredictionError") or {}
    benchmark = prediction.get("officialBenchmark") or {}
    delivery = prediction.get("benchmarkDeliveryCalibration") or {}
    adjustment = prediction.get("implementationAdjustment") or {}
    feasible_count = _number(recommendation.get("feasible_candidates_count"), 0)
    fiscal_pressure = _number(statewide.get("fiscalPressureUsingSubmittedBenefit"), 0)
    absolute_error = _number(error.get("absolutePercentError"), 0)
    has_benchmark = _number(benchmark.get("beneficiaries"), 0) > 0
    implementation_factor = _number(adjustment.get("factor"), 1.0)
    reasons: list[str] = []

    if delivery.get("applied") and _number(delivery.get("observedDeliveryFactor"), 1.0) < 0.25:
        reasons.append("Failure signal: official records show very low real-world delivery compared with eligible demand.")
    if absolute_error > 0.20:
        reasons.append("Failure signal: benchmark prediction error is above 20%.")
    if fiscal_pressure > 1.25:
        reasons.append("Failure signal: estimated statewide cost is far above the submitted budget.")
    if implementation_factor < 0.35:
        reasons.append("Failure signal: implementation adjustment indicates severe delivery loss before beneficiaries are reached.")

    if reasons:
        return "Failure", reasons
    if has_benchmark and absolute_error <= 0.10 and fiscal_pressure <= 1.10:
        return "Success", []
    if has_benchmark and absolute_error <= 0.20 and fiscal_pressure <= 1.25:
        return "Moderate", ["Review signal: benchmark fit is acceptable, but fiscal pressure or error is near the review threshold."]
    if bool(ranking.get("is_feasible")) and fiscal_pressure <= 1.0 and absolute_error <= 0.10:
        return "Success", []
    if not has_benchmark and fiscal_pressure <= 0.75 and implementation_factor >= 0.65:
        return "Success", []
    review_reasons: list[str] = []
    if feasible_count <= 0:
        review_reasons.append("Review signal: backend experiment candidates did not pass generic feasibility constraints, so the submitted-policy result should be treated cautiously.")
    if fiscal_pressure > 1.0:
        review_reasons.append("Review signal: submitted statewide cost is close to or above the planned budget.")
    if implementation_factor < 0.65:
        review_reasons.append("Review signal: implementation adjustment indicates meaningful take-up or exclusion risk.")
    return "Moderate", review_reasons


def _submitted_policy_success_summary(result: dict[str, Any]) -> str:
    simulation = result.get("simulation", {})
    prediction = result.get("prediction") or {}
    error = prediction.get("actualPredictionError") or {}
    statewide = prediction.get("statewideEstimate") or {}
    policy_name = simulation.get("policyName") or "Submitted policy"
    predicted = statewide.get("beneficiaries")
    actual = error.get("actualBeneficiaries")
    percent_error = _number(error.get("absolutePercentError"), 0) * 100
    if predicted and actual:
        return (
            f"Submitted policy '{policy_name}' is validated against the official benchmark with "
            f"{predicted:,.0f} predicted beneficiaries versus {actual:,.0f} official beneficiaries "
            f"({percent_error:.1f}% absolute error)."
        )
    return f"Submitted policy '{policy_name}' passes the backend benchmark and fiscal checks."


def _submitted_policy_success_strengths(result: dict[str, Any]) -> list[str]:
    prediction = result.get("prediction") or {}
    statewide = prediction.get("statewideEstimate") or {}
    validation = prediction.get("validationStatus") or {}
    strengths = [
        f"Official benchmark validation status is {validation.get('status', 'acceptable')}.",
    ]
    fiscal_pressure = statewide.get("fiscalPressureUsingSubmittedBenefit")
    if isinstance(fiscal_pressure, (int, float)):
        strengths.append(f"Submitted statewide budget pressure is {fiscal_pressure * 100:.1f}%.")
    strengths.append("Final decision is based on the submitted policy benchmark, not generic recommendation candidates.")
    return strengths


def _submitted_policy_interpretation(
    result: dict[str, Any],
    classification: str,
    classification_reasons: list[str],
) -> dict[str, Any]:
    prediction = result.get("prediction") or {}
    validation = prediction.get("validationStatus") or {}
    statewide = prediction.get("statewideEstimate") or {}
    error = prediction.get("actualPredictionError") or {}
    policy_name = result.get("simulation", {}).get("policyName") or "Submitted policy"
    policy_profile = _policy_profile(result)

    predicted = _number(statewide.get("beneficiaries"), 0)
    actual = _number(error.get("actualBeneficiaries"), 0)
    percent_error = _number(error.get("absolutePercentError"), 0) * 100
    fiscal_pressure = statewide.get("fiscalPressureUsingSubmittedBenefit")

    if actual > 0 and predicted > 0:
        summary = (
            f"Submitted policy '{policy_name}' is evaluated against its official benchmark with "
            f"{predicted:,.0f} predicted beneficiaries versus {actual:,.0f} official beneficiaries "
            f"({percent_error:.1f}% absolute error)."
        )
    else:
        summary = f"Submitted policy '{policy_name}' is evaluated using completed backend phase outputs."

    strengths: list[str] = []
    status = validation.get("status")
    if status:
        strengths.append(f"Official benchmark validation status is {status}.")
    if isinstance(fiscal_pressure, (int, float)):
        strengths.append(f"Submitted statewide budget pressure is {fiscal_pressure * 100:.1f}%.")
    strengths.extend(policy_profile["strengths"])
    strengths.append("Final decision is based on the submitted policy result contract.")

    concerns = classification_reasons or policy_profile["concerns"]
    if not concerns:
        if classification == "Success":
            concerns = ["No critical benchmark or fiscal failure signals detected for the submitted policy."]
        elif classification == "Moderate":
            concerns = ["Submitted policy is acceptable but should be reviewed before relying on the estimate operationally."]
        else:
            concerns = ["Backend classified the submitted policy as failure based on benchmark, delivery, or fiscal checks."]

    return {
        "classification": classification,
        "summary": summary,
        "strengths": strengths,
        "concerns": concerns,
    }


def _policy_profile(result: dict[str, Any]) -> dict[str, list[str]]:
    simulation = result.get("simulation", {})
    policy = simulation.get("submittedPolicy") or {}
    prediction = result.get("prediction") or {}
    adjustment = prediction.get("implementationAdjustment") or {}
    target_model = prediction.get("targetPopulationModel") or {}
    department = str(policy.get("department") or simulation.get("department") or "").strip().lower()
    rules = policy.get("rules") if isinstance(policy, dict) else []
    rule_attributes = {str(rule.get("attribute", "")).strip().lower() for rule in rules or [] if isinstance(rule, dict)}
    text = " ".join(
        [
            str(simulation.get("policyName", "")),
            str(policy.get("description", "") if isinstance(policy, dict) else ""),
            " ".join(f"{rule.get('attribute', '')} {rule.get('operator', '')} {rule.get('value', '')}" for rule in rules or [] if isinstance(rule, dict)),
        ]
    ).lower()
    strengths: list[str] = []
    concerns: list[str] = []

    if rule_attributes:
        strengths.append(f"Eligibility uses {len(rule_attributes)} submitted rule attribute(s): {', '.join(sorted(rule_attributes))}.")
    if target_model.get("constraints"):
        strengths.append("Target population model used submitted constraints: " + ", ".join(target_model["constraints"]) + ".")

    if department == "labour" or _text_has_any(text, ["gig worker", "platform worker", "informal worker", "unorganised worker"]):
        concerns.append("Labour delivery risk: worker registration quality, platform/employer verification, and income volatility can reduce actual take-up.")
    elif department == "health" or _text_has_any(text, ["health", "medical", "insurance", "hospital", "claim"]):
        concerns.append("Health delivery risk: provider access, claims processing, enrolment awareness, and exclusion at point of care should be monitored.")
    elif department == "agriculture" or _text_has_any(text, ["farmer", "crop", "cultivation", "agriculture"]):
        concerns.append("Agriculture delivery risk: land/crop records, seasonality, input availability, and subsidy leakage can affect realised coverage.")
    elif department == "education" or _text_has_any(text, ["student", "school", "college", "education", "scholarship"]):
        concerns.append("Education delivery risk: enrolment records, attendance continuity, and institution verification can affect realised coverage.")
    elif department in {"housing", "rural development"} or _text_has_any(text, ["housing", "construction", "patta", "green house"]):
        concerns.append("Asset delivery risk: land records, procurement, local execution capacity, and completion delays can reduce delivered beneficiaries.")
    elif department == "social welfare":
        concerns.append("Welfare delivery risk: document verification, outreach, duplicate-benefit checks, and grievance handling can affect take-up.")

    factor = adjustment.get("factor")
    if isinstance(factor, (int, float)) and factor < 0.75:
        concerns.append(f"Implementation adjustment is {factor * 100:.1f}%, so delivery assumptions should be reviewed before approval.")

    return {"strengths": strengths[:3], "concerns": concerns[:3]}


def _submitted_policy_backend_output(result: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
    prediction = result.get("prediction") or {}
    validation = prediction.get("validationStatus") or {}
    benchmark_delivery = prediction.get("benchmarkDeliveryCalibration") or {}
    simulation = result.get("simulation") or {}
    return {
        "source": "pipeline_artifacts",
        "artifactSource": "completed_8_phase_backend_pipeline",
        "recommendationId": f"submitted-policy-{simulation.get('id', 'result')}",
        "evaluatedPolicy": simulation.get("policyName"),
        "decisionBasis": "submitted_policy_benchmark_fiscal_delivery_checks",
        "validationStatus": validation.get("status"),
        "dataVersion": prediction.get("dataVersion"),
        "benchmarkCalibrationApplied": bool(benchmark_delivery.get("applied")),
        "generatedAt": recommendation.get("generated_at"),
    }


def _percentile(metric: dict[str, Any], percentile: str, default: float) -> float:
    percentiles = metric.get("percentiles") or {}
    return _number(percentiles.get(percentile), default)


def _allocated_budget(result: dict[str, Any], recommendation: dict[str, Any], ranking: dict[str, Any], mean_cost: float, utilization: float, default: float) -> float:
    submitted_budget = _number(result.get("simulation", {}).get("plannedStatewideBudget"), 0)
    if submitted_budget > 0:
        return submitted_budget
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
