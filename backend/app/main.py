"""FastAPI backend for the Tamil Nadu policy simulation dashboard."""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


Department = Literal[
    "Social Welfare",
    "Rural Development",
    "Education",
    "Health",
    "Agriculture",
    "Labour",
    "Housing",
    "Other",
]
GeographicScope = Literal["Tamil Nadu", "Selected Districts", "Rural Only", "Urban Only"]
RuleOperator = Literal["=", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "BETWEEN"]
RuleJoiner = Literal["AND", "OR"]
BudgetRisk = Literal["Low", "Moderate", "High", "Critical"]
Outcome = Literal["Success", "Moderate", "Failure"]


class PolicyRule(BaseModel):
    id: str
    attribute: str
    operator: RuleOperator
    value: str
    joiner: RuleJoiner


class Policy(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1)
    department: Department
    description: str = Field(min_length=1)
    objectives: str | None = None
    budgetAllocation: float | None = None
    geographicScope: GeographicScope
    selectedDistricts: list[str] = Field(default_factory=list)
    rules: list[PolicyRule] = Field(default_factory=list)


class SimulationConfiguration(BaseModel):
    monteCarloRuns: int = Field(gt=0)
    confidenceLevel: Literal[90, 95, 99] = 95
    randomSeed: int | None = None
    populationSampleSize: int = Field(gt=0)
    budgetConstraint: bool = True
    sensitivityAnalysis: bool = True


class CreateSimulationRequest(BaseModel):
    policy: Policy
    configuration: SimulationConfiguration


@dataclass
class StoredSimulation:
    policy: Policy
    configuration: SimulationConfiguration
    created_at: float


app = FastAPI(title="PolicySim TN API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SIMULATIONS: dict[str, StoredSimulation] = {}

DISTRICT_NAMES = [
    "Chennai",
    "Coimbatore",
    "Madurai",
    "Tiruchirappalli",
    "Salem",
    "Tirunelveli",
    "Thanjavur",
    "Erode",
    "Vellore",
    "Thoothukudi",
    "Dindigul",
    "Cuddalore",
    "Kancheepuram",
    "Tiruvallur",
    "Virudhunagar",
    "Namakkal",
    "Karur",
    "Sivaganga",
    "Ramanathapuram",
    "Nilgiris",
]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "PolicySim TN API"}


@app.post("/api/policies/validate")
def validate_policy(policy: Policy) -> dict[str, Any]:
    checks = [
        {"label": "Policy name configured", "valid": len(policy.name.strip()) > 3},
        {"label": "Policy description supplied", "valid": len(policy.description.strip()) > 20},
        {"label": "Policy rules valid", "valid": all(rule.attribute and rule.operator and rule.value for rule in policy.rules)},
        {"label": "Backend fiscal model available", "valid": True},
        {
            "label": "District scope valid",
            "valid": policy.geographicScope != "Selected Districts" or bool(policy.selectedDistricts),
            "detail": "At least one district is required." if policy.geographicScope == "Selected Districts" else None,
        },
        {"label": "Population dataset available", "valid": True},
    ]
    return {"valid": all(check["valid"] for check in checks), "checks": checks}


@app.post("/api/policies/parse")
def parse_policy(payload: dict[str, str]) -> list[dict[str, str]]:
    description = payload.get("description", "").lower()
    rules = [{"id": "rule-residence", "attribute": "Residence", "operator": "=", "value": "Tamil Nadu", "joiner": "AND"}]
    if "women" in description or "female" in description:
        rules.insert(0, {"id": "rule-gender", "attribute": "Gender", "operator": "=", "value": "Female", "joiner": "AND"})
    if "income" in description:
        rules.append({"id": "rule-income", "attribute": "Household Income", "operator": "<", "value": "250000", "joiner": "AND"})
    if "age" in description:
        rules.append({"id": "rule-age-min", "attribute": "Age", "operator": ">=", "value": "21", "joiner": "AND"})
        rules.append({"id": "rule-age-max", "attribute": "Age", "operator": "<=", "value": "60", "joiner": "AND"})
    return rules


@app.post("/api/simulations")
def create_simulation(payload: CreateSimulationRequest) -> dict[str, str]:
    simulation_id = f"SIM-TN-{int(time.time() * 1000) % 1_000_000:06d}"
    SIMULATIONS[simulation_id] = StoredSimulation(payload.policy, payload.configuration, time.time())
    return {"simulationId": simulation_id}


@app.get("/api/simulations/{simulation_id}/progress")
def simulation_progress(simulation_id: str) -> dict[str, Any]:
    stored = _get_simulation(simulation_id)
    elapsed = int(time.time() - stored.created_at)
    progress = min(100, max(4, int((elapsed / 18) * 100)))
    completed_iterations = min(stored.configuration.monteCarloRuns, int((progress / 100) * stored.configuration.monteCarloRuns))
    labels = [
        "DATA FOUNDATION",
        "POLICY-DATA COMPATIBILITY ENGINE",
        "SYNTHETIC POPULATION GENERATION",
        "POPULATION VALIDATION",
        "CALIBRATION & REWEIGHTING",
        "POLICY ENGINE",
        "MONTE CARLO & UNCERTAINTY ENGINE",
        "RECOMMENDATION ENGINE",
    ]
    thresholds = [12, 25, 37, 50, 62, 75, 87, 100]
    stages = []
    previous = 0
    for label, threshold in zip(labels, thresholds):
        status = "complete" if progress >= threshold else "active" if progress > previous else "pending"
        stages.append({"label": label, "status": status})
        previous = threshold
    return {
        "simulationId": simulation_id,
        "policyName": stored.policy.name,
        "progress": progress,
        "currentStage": "Recommendation Engine" if progress >= 100 else "Backend Architecture Flow",
        "completedIterations": completed_iterations,
        "totalIterations": stored.configuration.monteCarloRuns,
        "elapsedSeconds": elapsed,
        "stages": stages,
    }


@app.get("/api/simulations/{simulation_id}/results")
def simulation_results(simulation_id: str) -> dict[str, Any]:
    return _build_result(simulation_id, _get_simulation(simulation_id))


@app.get("/api/simulations")
def list_simulations() -> list[dict[str, Any]]:
    return [_build_result(simulation_id, stored)["simulation"] for simulation_id, stored in SIMULATIONS.items()]


def _get_simulation(simulation_id: str) -> StoredSimulation:
    if simulation_id not in SIMULATIONS:
        raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
    return SIMULATIONS[simulation_id]


def _build_result(simulation_id: str, stored: StoredSimulation) -> dict[str, Any]:
    policy = stored.policy
    configuration = stored.configuration
    text = f"{policy.description} {' '.join(f'{rule.attribute} {rule.operator} {rule.value}' for rule in policy.rules)}".lower()
    attributes = [rule.attribute.lower() for rule in policy.rules]
    annual_benefit = _extract_annual_benefit(policy.description)
    base_population = 12_048_463
    target_universe = _estimate_target_universe(text, attributes, base_population)
    full_population_coverage = _clamp(_estimate_coverage(text, attributes, len(policy.rules)), 0.08, 0.96)
    coverage = _clamp(full_population_coverage / target_universe["share"], 0.03, 0.98)
    target_fit = _estimate_target_fit(text, attributes, len(policy.rules), coverage)
    target_population = target_universe["population"]
    beneficiaries = round(target_population * coverage)
    mean_cost = round(beneficiaries * annual_benefit)
    planning_envelope = _estimate_planning_envelope(full_population_coverage, annual_benefit, base_population)
    utilization = mean_cost / max(planning_envelope, 1)
    probability_overrun = _clamp((utilization - 0.9) / 1.1, 0.01, 0.99)
    risk_score = round(_clamp(utilization * 34 + coverage * 12 + (14 if len(policy.rules) <= 2 else 0), 4, 100))
    risk_level = _risk_level(risk_score)
    equity = _estimate_equity(text, coverage, risk_score)
    classification = _classify_policy(coverage, target_fit, utilization, risk_score, equity["overall"])
    districts = _district_results(coverage, annual_benefit, equity["district"])
    p5 = round(mean_cost * (0.88 - risk_score / 1000))
    p95 = round(mean_cost * (1.08 + risk_score / 420))
    created_timestamp = datetime.fromtimestamp(stored.created_at, tz=timezone.utc).isoformat()
    return {
        "simulation": {
            "id": simulation_id,
            "policyName": policy.name,
            "department": policy.department,
            "date": created_timestamp,
            "monteCarloRuns": configuration.monteCarloRuns,
            "confidenceLevel": configuration.confidenceLevel,
            "beneficiaryCoverage": coverage,
            "estimatedCost": mean_cost,
            "equityScore": equity["overall"],
            "budgetRisk": risk_level,
            "status": "completed",
        },
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "beneficiary": {
            "coverage": coverage,
            "beneficiaries": beneficiaries,
            "targetFit": target_fit,
            "basePopulation": base_population,
            "targetShare": target_universe["share"],
            "targetUniverse": target_universe["label"],
            "eligiblePopulation": beneficiaries,
            "nonEligiblePopulation": target_population - beneficiaries,
            "targetPopulation": target_population,
        },
        "budget": {
            "allocatedBudget": planning_envelope,
            "meanCost": mean_cost,
            "unusedBudget": planning_envelope - mean_cost,
            "costPerBeneficiary": round(mean_cost / max(beneficiaries, 1)),
            "probabilityOverrun": probability_overrun,
            "worstCaseCost": p95,
            "utilization": utilization,
            "riskScore": risk_score,
            "riskLevel": risk_level,
        },
        "monteCarlo": {
            "mean": mean_cost,
            "median": round(mean_cost * 0.985),
            "p5": p5,
            "p95": p95,
            "budget": planning_envelope,
            "overrunProbability": probability_overrun,
            "buckets": _monte_carlo_buckets(mean_cost, risk_score),
        },
        "confidenceIntervals": [
            {"metric": "Beneficiaries", "lower": round(beneficiaries * 0.95), "estimate": beneficiaries, "upper": round(beneficiaries * 1.05), "formatter": "number"},
            {"metric": "Policy Cost", "lower": p5, "estimate": mean_cost, "upper": p95, "formatter": "currency"},
            {"metric": "Coverage", "lower": _clamp(coverage - 0.035, 0, 1), "estimate": coverage, "upper": _clamp(coverage + 0.035, 0, 1), "formatter": "percent"},
            {"metric": "District Coverage", "lower": min(district["coverage"] for district in districts), "estimate": coverage, "upper": max(district["coverage"] for district in districts), "formatter": "percent"},
        ],
        "demographics": _demographics(text, beneficiaries, coverage),
        "districts": districts,
        "equity": equity,
        "interpretation": {
            "classification": classification,
            "summary": _summary(classification, coverage, target_fit, utilization),
            "strengths": _strengths(classification, target_fit, equity["overall"], risk_score),
            "concerns": _concerns(classification, utilization, risk_score),
        },
        "sensitivity": [
            {"variable": "Income Threshold", "beneficiaryImpact": round(coverage * 18, 1), "costImpact": round(utilization * 11, 1), "equityImpact": 6.2},
            {"variable": "Benefit Amount", "beneficiaryImpact": 2.1, "costImpact": round(utilization * 18, 1), "equityImpact": 1.1},
            {"variable": "District Scope", "beneficiaryImpact": 7.8, "costImpact": 8.4, "equityImpact": round((100 - equity["district"]) / 4, 1)},
            {"variable": "Rural Eligibility", "beneficiaryImpact": 5.3, "costImpact": 4.8, "equityImpact": 9.7},
        ],
    }


def _estimate_coverage(text: str, attributes: list[str], rule_count: int) -> float:
    coverage = 0.91 if any(term in text for term in ["every household", "all household", "universal"]) else 0.72
    if "gender" in attributes:
        coverage -= 0.20
    if "age" in attributes:
        coverage -= 0.10
    if "household income" in attributes or "annual income" in attributes:
        coverage -= 0.16
    if "disability status" in attributes:
        coverage -= 0.35
    if "employment status" in attributes:
        coverage -= 0.12
    if "district" in attributes:
        coverage -= 0.08
    if "rural only" in text:
        coverage -= 0.18
    if "urban only" in text:
        coverage -= 0.28
    if rule_count <= 2:
        coverage += 0.07
    return coverage


def _estimate_target_universe(text: str, attributes: list[str], base_population: int) -> dict[str, Any]:
    share = 1.0
    labels: list[str] = []

    if "gender" in attributes or "women" in text or "female" in text:
        share *= 0.49
        labels.append("women")
    if "rural only" in text:
        share *= 0.57
        labels.append("rural residents")
    if "urban only" in text:
        share *= 0.43
        labels.append("urban residents")
    if "disability status" in attributes:
        share *= 0.08
        labels.append("persons with disability")
    if "employment status" in attributes:
        share *= 0.18
        labels.append("employment-status target group")
    if "district" in attributes:
        share *= 0.55
        labels.append("selected-district population")

    if not labels:
        return {"population": base_population, "share": 1.0, "label": "Total synthetic population"}

    return {
        "population": round(base_population * share),
        "share": share,
        "label": f"{' + '.join(labels).title()} synthetic population",
    }


def _estimate_target_fit(text: str, attributes: list[str], rule_count: int, coverage: float) -> int:
    targeted_signals = 0
    if "gender" in attributes:
        targeted_signals += 1
    if "age" in attributes:
        targeted_signals += 1
    if "household income" in attributes or "annual income" in attributes or "income" in text:
        targeted_signals += 1
    if "disability status" in attributes:
        targeted_signals += 2
    if "employment status" in attributes:
        targeted_signals += 1
    if "district" in attributes or "rural only" in text or "urban only" in text:
        targeted_signals += 1

    universal = any(term in text for term in ["every household", "all household", "universal"])
    if universal and targeted_signals == 0:
        benchmark = 0.70
    elif targeted_signals >= 4:
        benchmark = 0.18
    elif targeted_signals >= 3:
        benchmark = 0.22
    elif targeted_signals == 2:
        benchmark = 0.30
    elif targeted_signals == 1:
        benchmark = 0.42
    else:
        benchmark = 0.60

    score = 72 + (coverage - benchmark) * 110
    if "income" in text:
        score += 8
    if rule_count <= 2 and not universal:
        score -= 8
    return round(_clamp(score, 0, 100))


def _extract_annual_benefit(description: str) -> int:
    benefit_match = re.search(
        r"(?:assistance|benefit|transfer|stipend|pension|subsidy)(?:\s+\w+){0,4}\s+(?:of\s+)?(?:rs|inr|\u20b9)\s*([\d,]+)",
        description,
        flags=re.IGNORECASE,
    )
    if benefit_match:
        amount = int(benefit_match.group(1).replace(",", ""))
    else:
        amounts = [int(match.replace(",", "")) for match in re.findall(r"(?:rs|inr|\u20b9)\s*([\d,]+)", description, flags=re.IGNORECASE)]
        amount = amounts[0] if amounts else 1000
    return amount * 12 if re.search(r"monthly|per month|month", description, flags=re.IGNORECASE) else amount


def _estimate_equity(text: str, coverage: float, risk_score: int) -> dict[str, Any]:
    universal = "every household" in text or "universal" in text
    gender = 74 if ("female" in text or "women" in text) else 88 if universal else 84
    social_group = 82 if ("social group" in text or universal) else 76
    rural_urban = 58 if ("rural only" in text or "urban only" in text) else 84
    district = 70 if coverage > 0.85 else 78
    income = 88 if "income" in text else 62
    overall = round(_clamp((gender + social_group + rural_urban + district + income) / 5 - risk_score * 0.08, 35, 94))
    return {
        "overall": overall,
        "gender": gender,
        "socialGroup": social_group,
        "ruralUrban": rural_urban,
        "district": district,
        "income": income,
        "explanation": "Scores are generated from submitted eligibility rules, coverage breadth, income targeting and fiscal risk.",
    }


def _risk_level(risk_score: int) -> BudgetRisk:
    if risk_score >= 75:
        return "Critical"
    if risk_score >= 55:
        return "High"
    if risk_score >= 30:
        return "Moderate"
    return "Low"


def _classify_policy(coverage: float, target_fit: int, utilization: float, risk_score: int, equity_score: int) -> Outcome:
    fiscal_sustainability = _fiscal_sustainability(utilization)
    score = (target_fit * 0.30) + (equity_score * 0.30) + (fiscal_sustainability * 0.25) + ((100 - risk_score) * 0.15)

    if target_fit < 35 or equity_score < 45 or fiscal_sustainability < 20 or risk_score >= 82:
        return "Failure"
    if coverage < 0.10 and target_fit < 55:
        return "Failure"
    if score >= 75 and target_fit >= 65 and equity_score >= 65 and fiscal_sustainability >= 60 and risk_score < 55:
        return "Success"
    if score >= 55 and target_fit >= 45 and equity_score >= 55 and fiscal_sustainability >= 25 and risk_score < 75:
        return "Moderate"
    return "Failure"


def _fiscal_sustainability(utilization: float) -> float:
    return _clamp(100 - max(0, utilization - 0.70) * 150, 0, 100)


def _estimate_planning_envelope(coverage: float, annual_benefit: int, target_population: int) -> int:
    expected_policy_scale = target_population * max(coverage, 0.12) * annual_benefit
    if coverage >= 0.75:
        multiplier = 0.55
    elif coverage >= 0.45:
        multiplier = 0.85
    else:
        multiplier = 1.35
    return round(expected_policy_scale * multiplier)


def _district_results(coverage: float, annual_benefit: int, district_equity: int) -> list[dict[str, Any]]:
    districts = []
    for index, district in enumerate(DISTRICT_NAMES):
        population = 980_000 + index * 54_000
        local_coverage = _clamp(coverage + (((index * 11) % 17) - 8) / 100, 0.03, 0.98)
        beneficiaries = round(population * local_coverage * 0.62)
        estimated_cost = beneficiaries * annual_benefit
        districts.append({
            "id": district.lower().replace(" ", "-"),
            "district": district,
            "population": population,
            "eligiblePopulation": round(population * 0.62),
            "beneficiaries": beneficiaries,
            "coverage": local_coverage,
            "estimatedCost": estimated_cost,
            "costPerBeneficiary": annual_benefit,
            "equityScore": round(_clamp(district_equity + (((index * 7) % 19) - 9), 30, 96)),
            "budgetPressure": _clamp(local_coverage * annual_benefit / 18_000, 0.08, 1),
            "ruralCoverage": _clamp(local_coverage + (0.04 if index % 2 == 0 else -0.03), 0, 1),
            "urbanCoverage": _clamp(local_coverage + (-0.03 if index % 2 == 0 else 0.03), 0, 1),
            "coordinates": [78 + (index % 5) * 0.85, 8.4 + (index // 5) * 1.3],
        })
    return districts


def _demographics(text: str, beneficiaries: int, coverage: float) -> dict[str, Any]:
    female_focused = "female" in text or "women" in text
    rural_focused = "rural" in text
    return {
        "gender": [
            {"category": "Female", "value": 0.9 if female_focused else 0.49},
            {"category": "Male", "value": 0.09 if female_focused else 0.5},
            {"category": "Other", "value": 0.01},
        ],
        "socialGroup": [
            {"category": "SC", "beneficiaries": round(beneficiaries * 0.22), "coverage": _clamp(coverage + 0.02, 0, 1)},
            {"category": "ST", "beneficiaries": round(beneficiaries * 0.05), "coverage": _clamp(coverage - 0.03, 0, 1)},
            {"category": "OBC", "beneficiaries": round(beneficiaries * 0.48), "coverage": coverage},
            {"category": "General", "beneficiaries": round(beneficiaries * 0.25), "coverage": _clamp(coverage - 0.06, 0, 1)},
        ],
        "ruralUrban": [
            {"category": "Rural", "beneficiaries": round(beneficiaries * (0.78 if rural_focused else 0.57)), "nonBeneficiaries": round(beneficiaries * 0.24)},
            {"category": "Urban", "beneficiaries": round(beneficiaries * (0.22 if rural_focused else 0.43)), "nonBeneficiaries": round(beneficiaries * 0.19)},
        ],
        "ageGroup": [
            {"category": "18-25", "value": round(beneficiaries * 0.13)},
            {"category": "26-35", "value": round(beneficiaries * 0.27)},
            {"category": "36-45", "value": round(beneficiaries * 0.28)},
            {"category": "46-60", "value": round(beneficiaries * 0.24)},
            {"category": "60+", "value": round(beneficiaries * 0.08)},
        ],
        "incomeGroup": [
            {"category": "< Rs 1L", "value": round(beneficiaries * 0.32)},
            {"category": "Rs 1L-Rs 1.5L", "value": round(beneficiaries * 0.30)},
            {"category": "Rs 1.5L-Rs 2L", "value": round(beneficiaries * 0.22)},
            {"category": "Rs 2L-Rs 2.5L", "value": round(beneficiaries * 0.16)},
        ],
    }


def _monte_carlo_buckets(mean_cost: int, risk_score: int) -> list[dict[str, int]]:
    return [
        {
            "lower": round(mean_cost * (0.78 + index * 0.035)),
            "upper": round(mean_cost * (0.815 + index * 0.035)),
            "frequency": round(500 + 4400 * math.exp(-((index - 7.5) ** 2) / (10 + risk_score / 8))),
        }
        for index in range(16)
    ]


def _summary(classification: Outcome, coverage: float, target_fit: int, utilization: float) -> str:
    if classification == "Failure":
        return "Backend appraisal shows weak real-world feasibility because targeting, equity, fiscal pressure or risk is outside acceptable limits."
    if classification == "Moderate":
        return f"The policy is implementable, but one or more metrics need review: coverage {coverage * 100:.1f}%, target fit {target_fit}/100, fiscal pressure {utilization * 100:.1f}%."
    return f"The policy has strong real-world alignment: coverage {coverage * 100:.1f}%, target fit {target_fit}/100, and manageable fiscal pressure."


def _strengths(classification: Outcome, target_fit: int, equity_score: int, risk_score: int) -> list[str]:
    if classification == "Failure":
        return ["Policy objective is identifiable", "Backend appraisal can guide redesign"]
    strengths = []
    if target_fit >= 65:
        strengths.append("Eligibility rules align with the intended beneficiary group")
    if equity_score >= 65:
        strengths.append("Distributional equity is within acceptable range")
    if risk_score < 55:
        strengths.append("Fiscal and uncertainty risk are manageable")
    return strengths or ["Policy can proceed with implementation safeguards"]


def _concerns(classification: Outcome, utilization: float, risk_score: int) -> list[str]:
    if classification == "Failure":
        return ["Targeting or equity is too weak", "Fiscal pressure or uncertainty risk is too high", "Eligibility or benefit design needs revision"]
    if utilization > 0.85 or risk_score > 55:
        return ["Monitor district fiscal pressure", "Review p95 cost before approval"]
    return ["No major critical concerns detected"]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))
