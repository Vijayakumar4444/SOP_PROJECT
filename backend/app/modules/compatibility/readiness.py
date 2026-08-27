from __future__ import annotations

from .models import RequirementResult


class ReadinessEvaluator:
    def blocking_issues(self, results: list[RequirementResult]) -> list[str]:
        return [
            f"Critical variable {r.requirement.canonical_variable} is {r.status}."
            for r in results
            if r.requirement.importance == "CRITICAL" and r.status in {"MISSING", "AGGREGATE_ONLY"}
        ]

    def readiness(self, reliability: float, blocking: list[str], results: list[RequirementResult]) -> str:
        if blocking:
            return "NOT_READY"
        if reliability >= 85 and not any(r.warnings for r in results):
            return "READY"
        if reliability >= 65:
            return "READY_WITH_WARNINGS"
        if reliability >= 45:
            return "LIMITED"
        return "NOT_READY"

    def warnings(self, results: list[RequirementResult], joint: dict) -> list[str]:
        warnings = [f"{result.requirement.canonical_variable}: {warning}" for result in results for warning in result.warnings]
        if joint.get("score", 0) < 100:
            warnings.append("Not all critical variables are jointly available in the same row-level dataset.")
        return warnings

    def recommendations(self, results: list[RequirementResult], readiness: str) -> list[str]:
        recs = []
        for result in results:
            if result.status == "PROXY_AVAILABLE":
                recs.append(f"Treat {result.requirement.canonical_variable} as a proxy-backed limitation; collect direct source data if eligibility depends on it.")
            if result.status in {"MISSING", "AGGREGATE_ONLY"}:
                recs.append(f"Acquire row-level {result.requirement.canonical_variable} data before simulation.")
        if readiness == "READY_WITH_WARNINGS":
            recs.append("Simulation can proceed only with limitations explicitly shown in outputs.")
        return recs or ["Data foundation appears adequate for a limited compatibility-positive simulation design."]
