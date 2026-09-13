from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.policy_engine.policy_loader import load_policy_from_file
from backend.app.modules.policy_engine.policy_validator import validate_policy_schema
from backend.app.modules.policy_engine.rule_engine import evaluate_single_rule, evaluate_logic_group
from backend.app.modules.policy_engine.policy_model import (
    AllocationStrategy,
    BenefitConfig,
    BenefitType,
    ConstraintConfig,
    Frequency,
    LogicGroupConfig,
    MissingValueBehavior,
    PolicyDefinition,
    RuleConfig,
    TargetUnit,
)
from backend.app.modules.policy_engine.beneficiary_selector import select_beneficiaries
from backend.app.modules.policy_engine.benefit_calculator import calculate_policy_benefits
from backend.app.modules.policy_engine.constraint_validator import validate_execution_constraints
from backend.app.modules.policy_engine.aggregation import compute_policy_aggregates
from backend.app.modules.policy_engine.service import Phase6PolicyService


class PolicyEngineUnitTests(unittest.TestCase):
    def test_all_supported_rule_operators(self) -> None:
        rec = {
            "age": 65,
            "district": "Chennai",
            "income": 150000.0,
            "null_field": None,
            "str_code": "TN-12345",
            "social_group": "Scheduled Caste",
        }

        # equals / not_equals
        p, _ = evaluate_single_rule(rec, RuleConfig(field="district", operator="equals", value="Chennai"))
        self.assertTrue(p)
        p, _ = evaluate_single_rule(rec, RuleConfig(field="district", operator="not_equals", value="Madurai"))
        self.assertTrue(p)

        # numeric comparisons
        p, _ = evaluate_single_rule(rec, RuleConfig(field="age", operator="greater_than_or_equal", value=60))
        self.assertTrue(p)
        p, _ = evaluate_single_rule(rec, RuleConfig(field="age", operator="less_than", value=70))
        self.assertTrue(p)

        # in / not_in
        p, _ = evaluate_single_rule(rec, RuleConfig(field="district", operator="in", value=["Chennai", "Kanchipuram"]))
        self.assertTrue(p)
        p, _ = evaluate_single_rule(rec, RuleConfig(field="district", operator="not_in", value=["Madurai", "Coimbatore"]))
        self.assertTrue(p)

        # between / not_between
        p, _ = evaluate_single_rule(rec, RuleConfig(field="income", operator="between", value=[100000, 200000]))
        self.assertTrue(p)
        p, _ = evaluate_single_rule(rec, RuleConfig(field="income", operator="not_between", value=[0, 50000]))
        self.assertTrue(p)

        # null checks
        p, _ = evaluate_single_rule(rec, RuleConfig(field="null_field", operator="is_null", value=None))
        self.assertTrue(p)
        p, _ = evaluate_single_rule(rec, RuleConfig(field="district", operator="is_not_null", value=None))
        self.assertTrue(p)

        # string ops
        p, _ = evaluate_single_rule(rec, RuleConfig(field="str_code", operator="starts_with", value="TN"))
        self.assertTrue(p)
        p, _ = evaluate_single_rule(rec, RuleConfig(field="str_code", operator="ends_with", value="12345"))
        self.assertTrue(p)
        p, _ = evaluate_single_rule(rec, RuleConfig(field="social_group", operator="contains", value="Caste"))
        self.assertTrue(p)

    def test_nested_logic_groups(self) -> None:
        rec = {"age": 25, "employment_status": "Unemployed", "income": 50000}
        
        # AND group
        g_and = LogicGroupConfig(
            logical_operator="AND",
            rules=[
                RuleConfig(field="age", operator="between", value=[18, 30]),
                RuleConfig(field="employment_status", operator="equals", value="Unemployed"),
            ],
        )
        passed, p_ids, f_ids = evaluate_logic_group(rec, g_and)
        self.assertTrue(passed)

        # OR group
        g_or = LogicGroupConfig(
            logical_operator="OR",
            rules=[
                RuleConfig(field="income", operator="less_than", value=20000),
                RuleConfig(field="employment_status", operator="equals", value="Unemployed"),
            ],
        )
        passed, p_ids, f_ids = evaluate_logic_group(rec, g_or)
        self.assertTrue(passed)

    def test_policy_schema_validation(self) -> None:
        valid_policy = PolicyDefinition(
            policy_id="P_001",
            name="Valid Test Policy",
            eligibility=LogicGroupConfig(rules=[RuleConfig(field="age", operator="greater_than", value=60)]),
            benefit=BenefitConfig(amount=1000, frequency=Frequency.MONTHLY),
        )
        val = validate_policy_schema(valid_policy)
        self.assertTrue(val["valid"])

        invalid_policy = PolicyDefinition(
            policy_id="",
            name="",
            benefit=BenefitConfig(amount=-500),
        )
        val_inv = validate_policy_schema(invalid_policy)
        self.assertFalse(val_inv["valid"])
        self.assertTrue(any(e["code"] == "MISSING_POLICY_ID" for e in val_inv["errors"]))
        self.assertTrue(any(e["code"] == "NEGATIVE_BENEFIT_AMOUNT" for e in val_inv["errors"]))

    def test_seeded_lottery_reproducibility(self) -> None:
        records = [
            {"person_id": f"P{i:03d}", "is_eligible": True, "consumption_expenditure": 10000}
            for i in range(100)
        ]

        policy = PolicyDefinition(
            policy_id="P_LOTTERY",
            name="Lottery Test",
            constraints=ConstraintConfig(
                maximum_beneficiaries=10,
                allocation_strategy=AllocationStrategy.SEEDED_LOTTERY,
                lottery_seed=12345,
            ),
        )

        res1, sel1, _ = select_beneficiaries(policy, records)
        res2, sel2, _ = select_beneficiaries(policy, records)

        sel1_ids = [r["person_id"] for r in sel1]
        sel2_ids = [r["person_id"] for r in sel2]

        self.assertEqual(sel1_ids, sel2_ids)
        self.assertEqual(len(sel1), 10)

    def test_phase7_simulation_interface(self) -> None:
        service = Phase6PolicyService(project_root=ROOT)
        policy_file = ROOT / "config/policy_engine/examples/tn_elderly_pension.yaml"
        
        sample_records = [
            {"synthetic_person_id": f"P{i}", "age": 65 if i % 2 == 0 else 30, "state": "Tamil Nadu", "individual_income": 50000, "employment_status": "Self-Employed", "calibration_weight": 10.0}
            for i in range(20)
        ]

        sim_res = service.evaluate_simulation(
            policy_path=policy_file,
            population_records=sample_records,
            weight_column="calibration_weight",
            seed=42,
            parameter_overrides={"total_budget": 500000},
        )

        self.assertEqual(sim_res["total_evaluated_records"], 20)
        self.assertEqual(sim_res["unweighted_eligible_records"], 10)
        self.assertEqual(sim_res["weighted_eligible_population"], 100.0)


if __name__ == "__main__":
    unittest.main()
