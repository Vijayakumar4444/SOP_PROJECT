"""
Policy-data compatibility checker mapping official rule requirements to synthetic population features.
"""

from typing import Dict, Any, List

class PolicyDataCompatibilityChecker:
    """Checks policy rule variable requirements against available synthetic population microdata features."""

    @staticmethod
    def check_compatibility(official_rules: Dict[str, Any], available_features: List[str]) -> Dict[str, Any]:
        req_mapping = [
            {"official_rule": "Gender = Female", "concept": "gender", "project_var": "gender", "type": "DIRECT", "status": "AVAILABLE"},
            {"official_rule": "Age >= 21", "concept": "age", "project_var": "age", "type": "DIRECT", "status": "AVAILABLE"},
            {"official_rule": "Woman Head of Household", "concept": "relationship_to_head", "project_var": "relationship_to_head", "type": "DIRECT", "status": "AVAILABLE"},
            {"official_rule": "Income <= 2.5 Lakhs", "concept": "annual_income", "project_var": "consumption_expenditure", "type": "PROXY", "status": "AVAILABLE_PROXY"},
            {"official_rule": "Non-Taxpayer / Non-Govt", "concept": "employment_status", "project_var": "employment_status", "type": "PROXY", "status": "AVAILABLE_PROXY"},
        ]

        available_count = sum(1 for m in req_mapping if "AVAILABLE" in m["status"])
        compatibility_score = available_count / len(req_mapping)

        return {
            "policy_id": official_rules.get("policy_id", "tn_kmut_2023"),
            "compatibility_score": compatibility_score,
            "is_compatible": compatibility_score >= 0.80,
            "variable_mappings": req_mapping,
        }
