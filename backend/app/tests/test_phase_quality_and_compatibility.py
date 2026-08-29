from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.compatibility.models import InvalidPolicyDefinitionError
from backend.app.modules.compatibility.service import PolicyDataCompatibilityService
from backend.app.modules.data_foundation.quality import quality_profile



class DataFoundationQualityTests(unittest.TestCase):
    def test_quality_profile_catches_bad_records(self) -> None:
        records = [
            {
                "reference_person_id": "P1",
                "reference_household_id": "H1",
                "source_record_id": "S1",
                "primary_source_id": "SRC",
                "state": "Tamil Nadu",
                "state_code": "33",
                "age": "28",
                "gender": "Male",
                "household_size": "4",
                "survey_weight": "1.5",
                "normalized_reference_weight": "1.0",
                "calibrated_reference_weight_gender_ur": "1.0",
            },
            {
                "reference_person_id": "P1",
                "reference_household_id": "H2",
                "source_record_id": "S2",
                "primary_source_id": "SRC",
                "state": "Kerala",
                "state_code": "32",
                "age": "140",
                "gender": "",
                "household_size": "0",
                "survey_weight": "-1",
                "normalized_reference_weight": "",
                "calibrated_reference_weight_gender_ur": "",
            },
        ]
        checks = {row["check"]: row for row in quality_profile(records)}
        self.assertEqual(checks["duplicate_reference_person_id_count"]["status"], "FAIL")
        self.assertEqual(checks["invalid_age_count"]["value"], 1)
        self.assertEqual(checks["invalid_household_size_count"]["value"], 1)
        self.assertEqual(checks["non_tamil_nadu_row_count"]["value"], 1)
        self.assertEqual(checks["missing_required_gender_count"]["value"], 1)


class CompatibilityEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = PolicyDataCompatibilityService(ROOT, persist_reports=False)

    def test_ready_demographic_policy(self) -> None:
        report = self.service.evaluate({
            "policy_id": "UNIT_READY_DEMOGRAPHIC",
            "name": "Tamil Nadu youth demographic filter",
            "jurisdiction": {"state": "Tamil Nadu"},
            "eligibility": [
                {"variable": "age", "operator": "between", "value": [18, 29]},
                {"variable": "gender", "operator": "equals", "value": "Female"},
                {"variable": "state", "operator": "equals", "value": "Tamil Nadu"},
            ],
            "reference_year": 2024,
        })
        self.assertIn(report.simulation_readiness, {"READY", "READY_WITH_WARNINGS"})
        self.assertGreaterEqual(report.reliability_score, 80)

    def test_partial_proxy_policy(self) -> None:
        report = self.service.evaluate({
            "policy_id": "UNIT_PROXY_INCOME",
            "name": "Income screened programme",
            "jurisdiction": {"state": "Tamil Nadu"},
            "eligibility": [
                {"variable": "household_income", "operator": "less_than", "value": 300000, "unit": "INR/year"},
                {"variable": "state", "operator": "equals", "value": "Tamil Nadu"},
            ],
            "reference_year": 2026,
        })
        income = next(item for item in report.requirements if item.requirement.canonical_variable == "household_income")
        self.assertEqual(income.status, "PROXY_AVAILABLE")
        self.assertTrue(income.warnings)

    def test_incompatible_health_policy_blocks(self) -> None:
        report = self.service.evaluate({
            "policy_id": "UNIT_HEALTH_MISSING",
            "name": "Health insurance top-up",
            "jurisdiction": {"state": "Tamil Nadu"},
            "eligibility": [
                {"variable": "health_insurance", "operator": "equals", "value": "No"},
                {"variable": "disability_status", "operator": "equals", "value": "Yes"},
            ],
            "reference_year": 2026,
        })
        self.assertEqual(report.simulation_readiness, "NOT_READY")
        self.assertTrue(any(req.requirement.canonical_variable == "health_insurance" for req in report.requirements))
        self.assertTrue(any("disability_status" in issue for issue in report.blocking_issues))

    def test_invalid_policy_rejected(self) -> None:
        with self.assertRaises(InvalidPolicyDefinitionError):
            self.service.evaluate({
                "policy_id": "UNIT_INVALID_STATE",
                "name": "Out of state policy",
                "jurisdiction": {"state": "Kerala"},
                "eligibility": [{"variable": "age", "operator": "greater_than", "value": 18}],
            })


if __name__ == "__main__":
    unittest.main()
