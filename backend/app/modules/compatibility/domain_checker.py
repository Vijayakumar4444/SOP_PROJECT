from __future__ import annotations

from .models import PolicyRequirement
from .rules import DOMAINS


class DomainChecker:
    def check(self, requirements: list[PolicyRequirement]) -> list[dict]:
        req_vars = {r.canonical_variable for r in requirements}
        out = []
        for domain, spec in DOMAINS.items():
            core_hits = len(req_vars & spec["core"])
            support_hits = len(req_vars & spec["supporting"])
            if core_hits == 0 and domain != "DEMOGRAPHICS":
                continue
            if core_hits == 0 and support_hits == 0:
                continue
            score = min(1.0, (core_hits * 0.7 + support_hits * 0.3) / max(len(req_vars), 1) + 0.35)
            status = "STRONGLY_SUPPORTED" if score >= 0.85 else "SUPPORTED" if score >= 0.65 else "PARTIALLY_SUPPORTED" if score >= 0.45 else "WEAKLY_SUPPORTED"
            out.append({"domain": domain, "status": status, "score": round(score * 100, 2), "matched_variables": sorted(req_vars & (spec["core"] | spec["supporting"]))})
        return out
