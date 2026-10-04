import unittest
from unittest.mock import MagicMock, patch

from backend.app.main import Policy, PolicyRule, SimulationConfiguration
from backend.app.policy_memory import (
    PolicyMemoryStore,
    _similarity_score,
    build_policy_memory_context,
    extract_policy_parameters,
    policy_fingerprint,
)


class PolicyMemoryTests(unittest.TestCase):
    def _policy(self, rule_id: str = "rule-1") -> Policy:
        return Policy(
            name="Women Income Support",
            department="Social Welfare",
            description="Monthly assistance of Rs 1000 for women with household income below Rs 250000.",
            geographicScope="Tamil Nadu",
            selectedDistricts=[],
            rules=[
                PolicyRule(id=rule_id, attribute="Gender", operator="=", value="Female", joiner="AND"),
                PolicyRule(id="rule-income", attribute="Household Income", operator="<", value="250000", joiner="AND"),
            ],
        )

    def _config(self) -> SimulationConfiguration:
        return SimulationConfiguration(
            monteCarloRuns=1000,
            confidenceLevel=95,
            randomSeed=42,
            populationSampleSize=12000,
            budgetConstraint=True,
            sensitivityAnalysis=True,
        )

    def test_policy_fingerprint_ignores_rule_ids(self):
        left = policy_fingerprint(self._policy("a"), self._config())
        right = policy_fingerprint(self._policy("b"), self._config())

        self.assertEqual(left, right)

    def test_policy_fingerprint_changes_when_rule_changes(self):
        policy = self._policy()
        changed = self._policy()
        changed.rules[1].value = "200000"

        self.assertNotEqual(policy_fingerprint(policy, self._config()), policy_fingerprint(changed, self._config()))

    def test_extract_policy_parameters_from_result(self):
        result = {
            "beneficiary": {"targetUniverse": "Women synthetic population", "coverage": 0.82, "targetFit": 78},
            "budget": {"utilization": 0.61, "riskScore": 45},
            "equity": {"overall": 80},
            "interpretation": {"classification": "Moderate"},
        }

        params = extract_policy_parameters(self._policy(), result)

        self.assertEqual(params["target_group"], "Women synthetic population")
        self.assertEqual(params["rule_attributes"], ["Gender", "Household Income"])
        self.assertEqual(params["benefit_amount"], 12000)
        self.assertEqual(params["final_outcome"], "Moderate")

    def test_build_policy_memory_context_aggregates_priors(self):
        context = build_policy_memory_context(
            [
                {
                    "runId": "SIM-1",
                    "similarityScore": 0.8,
                    "createdAt": "2026-10-04T00:00:00+00:00",
                    "metrics": {"coverage": 0.8, "riskScore": 40, "finalOutcome": "Moderate"},
                },
                {
                    "runId": "SIM-2",
                    "similarityScore": 0.7,
                    "createdAt": "2026-10-04T00:00:01+00:00",
                    "metrics": {"coverage": 0.9, "riskScore": 50, "finalOutcome": "Success"},
                },
            ],
            policy_hash="abc",
        )

        self.assertEqual(context["cacheStatus"], "miss")
        self.assertEqual(context["similarPolicyCount"], 2)
        self.assertEqual(context["priors"]["sampleSize"], 2)
        self.assertEqual(context["priors"]["coverage"]["mean"], 0.85)
        self.assertEqual(context["priors"]["riskScore"]["mean"], 45)

    def test_similarity_score_ranks_relevant_policy_above_unrelated_policy(self):
        query = extract_policy_parameters(self._policy())
        policy = self._policy().model_dump(mode="json")
        relevant = {
            "department": "Social Welfare",
            "target_group": "Female + income-targeted",
            "rule_attributes": ["Gender", "Household Income", "Age"],
            "benefit_amount": 14400,
        }
        unrelated = {
            "department": "Agriculture",
            "target_group": "farmers",
            "rule_attributes": ["Land Ownership"],
            "benefit_amount": 60000,
        }

        relevant_score, relevant_reasons = _similarity_score(query, relevant, policy)
        unrelated_score, unrelated_reasons = _similarity_score(query, unrelated, policy)

        self.assertGreater(relevant_score, unrelated_score)
        self.assertGreaterEqual(relevant_score, 0.35)
        self.assertIn("same department", relevant_reasons)
        self.assertEqual(unrelated_reasons, [])

    def test_similar_search_filters_to_pipeline_artifact_results(self):
        store = PolicyMemoryStore(conninfo="postgresql://example")
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch("backend.app.policy_memory.psycopg.connect", return_value=connection):
            store.find_similar_completed(self._policy(), policy_hash="hash")

        executed_sql = cursor.execute.call_args.args[0]
        self.assertIn("result_payload->'backendOutput'->>'source' = 'pipeline_artifacts'", executed_sql)


if __name__ == "__main__":
    unittest.main()
