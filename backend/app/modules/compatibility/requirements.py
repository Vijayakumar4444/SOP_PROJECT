from __future__ import annotations

from typing import Any

from .models import InvalidPolicyDefinitionError, PolicyRequirement
from .rules import ALIASES


class PolicyRequirementExtractor:
    def validate(self, policy: dict[str, Any]) -> None:
        if not isinstance(policy, dict):
            raise InvalidPolicyDefinitionError("Policy definition must be an object.")
        if "eligibility" not in policy or not isinstance(policy["eligibility"], list):
            raise InvalidPolicyDefinitionError("Policy definition must include an eligibility list.")
        jurisdiction = policy.get("jurisdiction", {})
        if jurisdiction and jurisdiction.get("state") not in {None, "Tamil Nadu"}:
            raise InvalidPolicyDefinitionError("This project supports Tamil Nadu policies only.")

    def extract(self, policy: dict[str, Any]) -> list[PolicyRequirement]:
        self.validate(policy)
        year = int(policy.get("reference_year", 2026))
        seen: dict[str, PolicyRequirement] = {}
        for item in policy.get("eligibility", []):
            var = ALIASES.get(str(item.get("variable", "")).strip(), str(item.get("variable", "")).strip())
            if not var:
                continue
            seen[var] = PolicyRequirement(
                variable=item.get("variable", var),
                canonical_variable=var,
                requirement_type="eligibility",
                importance="CRITICAL",
                required_level="HOUSEHOLD" if "household" in var else "PERSON",
                required_unit=item.get("unit", ""),
                policy_reference_year=year,
            )
        if policy.get("jurisdiction", {}).get("state") == "Tamil Nadu" and "state" not in seen:
            seen["state"] = PolicyRequirement("state", "state", "jurisdiction", "CRITICAL", "PERSON", "", "Tamil Nadu", year)
        if policy.get("benefit", {}).get("amount") is not None and "district" not in seen:
            seen["district"] = PolicyRequirement("district", "district", "group_analysis", "IMPORTANT", "PERSON", "", "Tamil Nadu", year)
        return list(seen.values())
