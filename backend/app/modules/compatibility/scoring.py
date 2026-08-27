from __future__ import annotations

from .models import RequirementResult
from .rules import SCORING_WEIGHTS, STATUS_SCORES


class ReliabilityScorer:
    def __init__(self, registry: dict):
        self.registry = registry

    def breakdown(self, domains: list[dict], results: list[RequirementResult], joint: dict) -> dict[str, float]:
        domain = sum(d["score"] for d in domains) / (len(domains) * 100) if domains else 0
        variable = sum(r.score for r in results) / max(len(results), 1)
        availability = sum(min(r.non_null_percentage / 100, 1.0) * STATUS_SCORES.get(r.status, 0) for r in results) / max(len(results), 1)
        temporal = sum(r.temporal_score for r in results) / max(len(results), 1)
        geographic = sum(1.0 if r.geographic_status == "COMPATIBLE" else 0.75 if "WARNING" in r.geographic_status else 0.3 for r in results) / max(len(results), 1)
        source_quality = sum(self.quality_score(r.preferred_source) for r in results) / max(len(results), 1)
        return {
            "domain": domain, "variable": variable, "availability": availability,
            "joint_availability": joint.get("score", 0) / 100, "temporal": temporal,
            "geographic": geographic, "source_quality": source_quality,
        }

    def overall(self, score_breakdown: dict[str, float]) -> float:
        return round(sum(score_breakdown[key] * SCORING_WEIGHTS[key] for key in SCORING_WEIGHTS) * 100, 2)

    def quality_score(self, source_id: str) -> float:
        source = self.registry.get("sources", {}).get(source_id, {})
        official = source.get("official_or_secondary", "")
        if "Official" in official:
            return 1.0
        if "Trusted secondary" in official:
            return 0.85
        return 0.65 if source_id else 0.3
