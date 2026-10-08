from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from backend.app.database import get_database_url, load_project_env


def policy_fingerprint(policy: Any, configuration: Any) -> str:
    payload = {
        "policy": _normalize_policy(_to_plain(policy)),
        "configuration": _normalize_mapping(_to_plain(configuration)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def extract_policy_parameters(policy: Any, result: dict[str, Any] | None = None) -> dict[str, Any]:
    plain_policy = _to_plain(policy)
    result = result or {}
    beneficiary = result.get("beneficiary", {})
    budget = result.get("budget", {})
    equity = result.get("equity", {})
    interpretation = result.get("interpretation", {})
    simulation = result.get("simulation", {})
    prediction = result.get("prediction", {})
    adjustment = prediction.get("implementationAdjustment") or {}
    delivery = prediction.get("benchmarkDeliveryCalibration") or {}
    prediction_error = prediction.get("actualPredictionError") or {}
    rules = plain_policy.get("rules", [])
    return {
        "target_group": beneficiary.get("targetUniverse") or _infer_target_group(plain_policy),
        "rule_attributes": [str(rule.get("attribute", "")).strip() for rule in rules if rule.get("attribute")],
        "benefit_amount": _annual_benefit_from_policy(plain_policy),
        "coverage": beneficiary.get("coverage") or simulation.get("beneficiaryCoverage"),
        "target_fit": beneficiary.get("targetFit"),
        "fiscal_pressure": budget.get("utilization"),
        "risk_score": budget.get("riskScore"),
        "equity_score": equity.get("overall") or simulation.get("equityScore"),
        "final_outcome": interpretation.get("classification"),
        "implementation_adjustment_factor": adjustment.get("factor"),
        "observed_delivery_factor": delivery.get("observedDeliveryFactor"),
        "benchmark_delivery_calibration_applied": delivery.get("applied"),
        "prediction_absolute_percent_error": prediction_error.get("absolutePercentError"),
        "prediction_percent_error": prediction_error.get("percentError"),
        "official_benchmark_beneficiaries": (prediction.get("officialBenchmark") or {}).get("beneficiaries"),
        "validation_status": (prediction.get("validationStatus") or {}).get("status"),
    }


def build_policy_memory_context(
    similar_policies: list[dict[str, Any]],
    policy_hash: str | None = None,
    cache_status: str = "miss",
) -> dict[str, Any]:
    return {
        "policyHash": policy_hash,
        "cacheStatus": cache_status,
        "similarPolicyCount": len(similar_policies),
        "similarPolicies": similar_policies,
        "priors": _aggregate_priors(similar_policies),
    }


class PolicyMemoryStore:
    def __init__(self, conninfo: str | None = None):
        load_project_env()
        self.conninfo = conninfo if conninfo is not None else get_database_url()

    @property
    def configured(self) -> bool:
        return bool(self.conninfo)

    def ensure_schema(self) -> None:
        if not self.configured:
            return
        with psycopg.connect(self.conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)

    def find_exact_completed(self, policy_hash: str) -> dict[str, Any] | None:
        if not self.configured:
            return None
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select run_id, policy_hash, result_payload, created_at
                    from policy_simulation_runs
                    where policy_hash = %s
                      and status = 'completed'
                      and result_payload is not null
                      and result_payload->'backendOutput'->>'source' = 'pipeline_artifacts'
                    order by created_at desc
                    limit 1
                    """,
                    (policy_hash,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def get_run_inputs(self, run_id: str) -> dict[str, Any] | None:
        if not self.configured:
            return None
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        run_id,
                        policy_hash,
                        policy_payload,
                        configuration_payload,
                        status,
                        cached_from_run_id,
                        result_payload,
                        created_at
                    from policy_simulation_runs
                    where run_id = %s
                    """,
                    (run_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def find_similar_completed(
        self,
        policy: Any,
        policy_hash: str,
        limit: int = 5,
        minimum_score: float = 0.35,
    ) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        query_params = extract_policy_parameters(policy)
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        r.run_id,
                        r.policy_hash,
                        r.policy_name,
                        r.department,
                        r.description,
                        r.created_at,
                        p.target_group,
                        p.rule_attributes,
                        p.benefit_amount,
                        p.coverage,
                        p.target_fit,
                        p.fiscal_pressure,
                        p.risk_score,
                        p.equity_score,
                        p.final_outcome,
                        p.metrics_payload
                    from policy_simulation_runs r
                    join policy_simulation_parameters p on p.run_id = r.run_id
                    where r.status = 'completed'
                      and r.result_payload->'backendOutput'->>'source' = 'pipeline_artifacts'
                      and r.policy_hash <> %s
                    order by r.created_at desc
                    limit 100
                    """,
                    (policy_hash,),
                )
                rows = [dict(row) for row in cur.fetchall()]
        scored = []
        for row in rows:
            score, reasons = _similarity_score(query_params, row, _to_plain(policy))
            if score >= minimum_score:
                scored.append(_similarity_summary(row, score, reasons))
        scored.sort(key=lambda item: (item["similarityScore"], item["createdAt"]), reverse=True)
        return scored[:limit]

    def create_run(
        self,
        run_id: str,
        policy_hash: str,
        policy: Any,
        configuration: Any,
        status: str = "queued",
        cached_from_run_id: str | None = None,
        result_payload: dict[str, Any] | None = None,
    ) -> None:
        if not self.configured:
            return
        plain_policy = _to_plain(policy)
        plain_config = _to_plain(configuration)
        with psycopg.connect(self.conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into policy_simulation_runs (
                        run_id,
                        policy_hash,
                        policy_name,
                        department,
                        description,
                        policy_payload,
                        configuration_payload,
                        status,
                        cached_from_run_id,
                        result_payload,
                        updated_at
                    )
                    values (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, now())
                    on conflict (run_id) do update set
                        policy_hash = excluded.policy_hash,
                        policy_name = excluded.policy_name,
                        department = excluded.department,
                        description = excluded.description,
                        policy_payload = excluded.policy_payload,
                        configuration_payload = excluded.configuration_payload,
                        status = excluded.status,
                        cached_from_run_id = excluded.cached_from_run_id,
                        result_payload = excluded.result_payload,
                        updated_at = now()
                    """,
                    (
                        run_id,
                        policy_hash,
                        plain_policy.get("name"),
                        plain_policy.get("department"),
                        plain_policy.get("description"),
                        json.dumps(plain_policy, sort_keys=True),
                        json.dumps(plain_config, sort_keys=True),
                        status,
                        cached_from_run_id,
                        json.dumps(result_payload, sort_keys=True) if result_payload else None,
                    ),
                )

    def complete_run(self, run_id: str, result_payload: dict[str, Any], parameters: dict[str, Any]) -> None:
        if not self.configured:
            return
        with psycopg.connect(self.conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update policy_simulation_runs
                    set status = 'completed',
                        result_payload = %s::jsonb,
                        updated_at = now()
                    where run_id = %s
                    """,
                    (json.dumps(result_payload, sort_keys=True), run_id),
                )
                cur.execute(
                    """
                    insert into policy_simulation_parameters (
                        run_id,
                        target_group,
                        rule_attributes,
                        benefit_amount,
                        coverage,
                        target_fit,
                        fiscal_pressure,
                        risk_score,
                        equity_score,
                        final_outcome,
                        metrics_payload,
                        updated_at
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now())
                    on conflict (run_id) do update set
                        target_group = excluded.target_group,
                        rule_attributes = excluded.rule_attributes,
                        benefit_amount = excluded.benefit_amount,
                        coverage = excluded.coverage,
                        target_fit = excluded.target_fit,
                        fiscal_pressure = excluded.fiscal_pressure,
                        risk_score = excluded.risk_score,
                        equity_score = excluded.equity_score,
                        final_outcome = excluded.final_outcome,
                        metrics_payload = excluded.metrics_payload,
                        updated_at = now()
                    """,
                    (
                        run_id,
                        parameters.get("target_group"),
                        parameters.get("rule_attributes", []),
                        parameters.get("benefit_amount"),
                        parameters.get("coverage"),
                        parameters.get("target_fit"),
                        parameters.get("fiscal_pressure"),
                        parameters.get("risk_score"),
                        parameters.get("equity_score"),
                        parameters.get("final_outcome"),
                        json.dumps(parameters, sort_keys=True),
                    ),
                )

    def update_run_status(self, run_id: str, status: str, result_payload: dict[str, Any] | None = None) -> None:
        if not self.configured:
            return
        with psycopg.connect(self.conninfo) as conn:
            with conn.cursor() as cur:
                if result_payload is None:
                    cur.execute(
                        """
                        update policy_simulation_runs
                        set status = %s,
                            updated_at = now()
                        where run_id = %s
                        """,
                        (status, run_id),
                    )
                else:
                    cur.execute(
                        """
                        update policy_simulation_runs
                        set status = %s,
                            result_payload = %s::jsonb,
                            updated_at = now()
                        where run_id = %s
                        """,
                        (status, json.dumps(result_payload, sort_keys=True), run_id),
                    )

    def log_phase(
        self,
        run_id: str,
        phase_name: str,
        status: str,
        artifact_path: str | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.configured:
            return
        with psycopg.connect(self.conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into phase_run_logs (
                        run_id,
                        phase_name,
                        status,
                        artifact_path,
                        message,
                        metadata
                    )
                    values (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        run_id,
                        phase_name,
                        status,
                        artifact_path,
                        message,
                        json.dumps(metadata or {}, sort_keys=True),
                    ),
                )

    def clear_phase_logs(self, run_id: str) -> None:
        if not self.configured:
            return
        with psycopg.connect(self.conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    delete from phase_run_logs
                    where run_id = %s
                    """,
                    (run_id,),
                )

    def get_run_status(self, run_id: str) -> dict[str, Any] | None:
        if not self.configured:
            return None
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select run_id, status, created_at, updated_at
                    from policy_simulation_runs
                    where run_id = %s
                    """,
                    (run_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def get_phase_logs(self, run_id: str) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select phase_name, status, artifact_path, message, metadata, created_at
                    from phase_run_logs
                    where run_id = %s
                    order by created_at asc, id asc
                    """,
                    (run_id,),
                )
                rows = [dict(row) for row in cur.fetchall()]
        return rows


SCHEMA_SQL = """
create table if not exists policy_simulation_runs (
    run_id text primary key,
    policy_hash text not null,
    policy_name text not null,
    department text,
    description text,
    policy_payload jsonb not null,
    configuration_payload jsonb not null,
    status text not null default 'queued',
    cached_from_run_id text null references policy_simulation_runs(run_id),
    result_payload jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_policy_simulation_runs_hash_completed
    on policy_simulation_runs(policy_hash, created_at desc)
    where status = 'completed';

create table if not exists policy_simulation_parameters (
    run_id text primary key references policy_simulation_runs(run_id) on delete cascade,
    target_group text,
    rule_attributes text[] not null default '{}',
    benefit_amount numeric,
    coverage numeric,
    target_fit numeric,
    fiscal_pressure numeric,
    risk_score numeric,
    equity_score numeric,
    final_outcome text,
    metrics_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists phase_run_logs (
    id bigserial primary key,
    run_id text not null references policy_simulation_runs(run_id) on delete cascade,
    phase_name text not null,
    status text not null,
    artifact_path text,
    message text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
"""


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    return value


def _normalize_policy(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _normalize_text(policy.get("name")),
        "department": _normalize_text(policy.get("department")),
        "description": _normalize_text(policy.get("description")),
        "objectives": _normalize_text(policy.get("objectives")),
        "budgetAllocation": policy.get("budgetAllocation"),
        "benefitAmount": policy.get("benefitAmount"),
        "benefitFrequency": _normalize_text(policy.get("benefitFrequency")),
        "administrativeCostPercent": policy.get("administrativeCostPercent"),
        "benchmarkActualBeneficiaries": policy.get("benchmarkActualBeneficiaries"),
        "benchmarkActualAnnualCost": policy.get("benchmarkActualAnnualCost"),
        "benchmarkDate": _normalize_text(policy.get("benchmarkDate")),
        "benchmarkSource": _normalize_text(policy.get("benchmarkSource")),
        "geographicScope": _normalize_text(policy.get("geographicScope")),
        "selectedDistricts": sorted(_normalize_text(item) for item in policy.get("selectedDistricts", [])),
        "rules": [_normalize_rule(rule) for rule in policy.get("rules", [])],
    }


def _normalize_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "attribute": _normalize_text(rule.get("attribute")),
        "operator": _normalize_text(rule.get("operator")).upper(),
        "value": _normalize_text(rule.get("value")),
        "joiner": _normalize_text(rule.get("joiner")).upper() or "AND",
    }


def _normalize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {str(key): mapping[key] for key in sorted(mapping)}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _infer_target_group(policy: dict[str, Any]) -> str:
    attributes = {str(rule.get("attribute", "")).lower(): str(rule.get("value", "")) for rule in policy.get("rules", [])}
    pieces = []
    if "gender" in attributes:
        pieces.append(attributes["gender"])
    if "age" in attributes:
        pieces.append("age-targeted")
    if "household income" in attributes or "annual income" in attributes:
        pieces.append("income-targeted")
    return " + ".join(pieces) if pieces else "general"


def _extract_annual_benefit(description: str) -> float | None:
    benefit_match = re.search(
        r"(?:assistance|benefit|transfer|stipend|pension|subsidy)(?:\s+\w+){0,4}\s+(?:of\s+)?(?:rs|inr|₹)\s*([\d,]+)",
        description or "",
        flags=re.IGNORECASE,
    )
    if benefit_match:
        amount = float(benefit_match.group(1).replace(",", ""))
    else:
        amounts = re.findall(r"(?:rs|inr|₹)\s*([\d,]+)", description or "", flags=re.IGNORECASE)
        amount = float(amounts[0].replace(",", "")) if amounts else None
    if amount is None:
        return None
    return amount * 12 if re.search(r"monthly|per month|month", description or "", flags=re.IGNORECASE) else amount


def _annual_benefit_from_policy(policy: dict[str, Any]) -> float | None:
    amount = _float_or_none(policy.get("benefitAmount"))
    if amount:
        return amount * 12 if _normalize_text(policy.get("benefitFrequency")).lower() == "monthly" else amount
    return _extract_annual_benefit(policy.get("description", ""))


def _similarity_score(query_params: dict[str, Any], candidate: dict[str, Any], policy: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    query_attrs = {str(item).lower() for item in query_params.get("rule_attributes", []) if item}
    candidate_attrs = {str(item).lower() for item in candidate.get("rule_attributes", []) if item}
    if query_attrs or candidate_attrs:
        overlap = len(query_attrs & candidate_attrs)
        union = len(query_attrs | candidate_attrs)
        attr_score = overlap / union if union else 0.0
        score += 0.45 * attr_score
        if overlap:
            reasons.append(f"shares {overlap} eligibility rule attribute(s)")

    if _normalize_text(candidate.get("department")).lower() == _normalize_text(policy.get("department")).lower():
        score += 0.20
        reasons.append("same department")

    query_target = _normalize_text(query_params.get("target_group")).lower()
    candidate_target = _normalize_text(candidate.get("target_group")).lower()
    if query_target and candidate_target:
        query_tokens = set(re.findall(r"[a-z0-9]+", query_target))
        candidate_tokens = set(re.findall(r"[a-z0-9]+", candidate_target))
        token_overlap = len(query_tokens & candidate_tokens)
        token_union = len(query_tokens | candidate_tokens)
        target_score = token_overlap / token_union if token_union else 0.0
        score += 0.20 * target_score
        if token_overlap:
            reasons.append("similar target group")

    query_benefit = _float_or_none(query_params.get("benefit_amount"))
    candidate_benefit = _float_or_none(candidate.get("benefit_amount"))
    if query_benefit and candidate_benefit:
        ratio = min(query_benefit, candidate_benefit) / max(query_benefit, candidate_benefit)
        score += 0.15 * ratio
        if ratio >= 0.75:
            reasons.append("similar benefit amount")

    return round(min(score, 1.0), 4), reasons


def _similarity_summary(row: dict[str, Any], score: float, reasons: list[str]) -> dict[str, Any]:
    return {
        "runId": row.get("run_id"),
        "policyName": row.get("policy_name"),
        "department": row.get("department"),
        "similarityScore": score,
        "reasons": reasons,
        "createdAt": row.get("created_at").isoformat() if row.get("created_at") else None,
        "metrics": {
            "targetGroup": row.get("target_group"),
            "coverage": _float_or_none(row.get("coverage")),
            "targetFit": _float_or_none(row.get("target_fit")),
            "fiscalPressure": _float_or_none(row.get("fiscal_pressure")),
            "riskScore": _float_or_none(row.get("risk_score")),
            "equityScore": _float_or_none(row.get("equity_score")),
            "finalOutcome": row.get("final_outcome"),
            "benefitAmount": _float_or_none(row.get("benefit_amount")),
            "implementationAdjustmentFactor": _float_or_none((row.get("metrics_payload") or {}).get("implementation_adjustment_factor")),
            "observedDeliveryFactor": _float_or_none((row.get("metrics_payload") or {}).get("observed_delivery_factor")),
            "predictionAbsolutePercentError": _float_or_none((row.get("metrics_payload") or {}).get("prediction_absolute_percent_error")),
            "predictionPercentError": _float_or_none((row.get("metrics_payload") or {}).get("prediction_percent_error")),
        },
    }


def _aggregate_priors(similar_policies: list[dict[str, Any]]) -> dict[str, Any]:
    if not similar_policies:
        return {}
    metric_names = [
        "coverage",
        "targetFit",
        "fiscalPressure",
        "riskScore",
        "equityScore",
        "benefitAmount",
        "implementationAdjustmentFactor",
        "observedDeliveryFactor",
        "predictionAbsolutePercentError",
        "predictionPercentError",
    ]
    priors: dict[str, Any] = {"sampleSize": len(similar_policies)}
    for metric_name in metric_names:
        values = [
            _float_or_none(policy.get("metrics", {}).get(metric_name))
            for policy in similar_policies
        ]
        numbers = [value for value in values if value is not None]
        if numbers:
            priors[metric_name] = {
                "mean": round(sum(numbers) / len(numbers), 6),
                "min": round(min(numbers), 6),
                "max": round(max(numbers), 6),
            }
    outcomes: dict[str, int] = {}
    for policy in similar_policies:
        outcome = policy.get("metrics", {}).get("finalOutcome")
        if outcome:
            outcomes[str(outcome)] = outcomes.get(str(outcome), 0) + 1
    if outcomes:
        priors["outcomes"] = outcomes
    return priors


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
