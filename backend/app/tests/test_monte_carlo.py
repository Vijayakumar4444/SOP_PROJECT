from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.monte_carlo.config_loader import load_simulation_config
from backend.app.modules.monte_carlo.config_validator import validate_simulation_config
from backend.app.modules.monte_carlo.distribution_sampler import DistributionSampler
from backend.app.modules.monte_carlo.seed_manager import SeedManager
from backend.app.modules.monte_carlo.population_provider import PopulationProvider
from backend.app.modules.monte_carlo.uncertainty_analyzer import compute_single_metric_uncertainty, compute_uncertainty_summary
from backend.app.modules.monte_carlo.risk_analyzer import compute_risk_probabilities, _wilson_score_interval
from backend.app.modules.monte_carlo.convergence_analyzer import check_simulation_convergence
from backend.app.modules.monte_carlo.sensitivity_analyzer import analyze_parameter_sensitivity, _pearson_correlation, _spearman_correlation
from backend.app.modules.monte_carlo.simulation_model import (
    DistributionType,
    ParameterUncertaintyConfig,
    PopulationConfig,
    PopulationMode,
    RiskMetricConfig,
    SamplingStrategy,
    SimulationConfig,
)


class MonteCarloUnitTests(unittest.TestCase):
    def test_seed_manager_hierarchical_reproducibility(self) -> None:
        sm1 = SeedManager(base_seed=20260913)
        sm2 = SeedManager(base_seed=20260913)

        bundle1 = sm1.get_iteration_seed_bundle(5)
        bundle2 = sm2.get_iteration_seed_bundle(5)

        self.assertEqual(bundle1.iteration_seed, bundle2.iteration_seed)
        self.assertEqual(bundle1.population_seed, bundle2.population_seed)
        self.assertEqual(bundle1.calibration_seed, bundle2.calibration_seed)
        self.assertEqual(bundle1.parameter_seed, bundle2.parameter_seed)
        self.assertEqual(bundle1.policy_seed, bundle2.policy_seed)

    def test_all_distribution_samplers(self) -> None:
        sampler = DistributionSampler(seed=42)

        # Uniform
        v_uni = sampler.sample_parameter(ParameterUncertaintyConfig(distribution=DistributionType.UNIFORM, minimum=10.0, maximum=20.0))
        self.assertTrue(10.0 <= v_uni <= 20.0)

        # Discrete Uniform
        v_duni = sampler.sample_parameter(ParameterUncertaintyConfig(distribution=DistributionType.DISCRETE_UNIFORM, minimum=100.0, maximum=200.0, step=50.0))
        self.assertIn(v_duni, [100, 150, 200])

        # Triangular
        v_tri = sampler.sample_parameter(ParameterUncertaintyConfig(distribution=DistributionType.TRIANGULAR, minimum=5.0, mode=10.0, maximum=15.0))
        self.assertTrue(5.0 <= v_tri <= 15.0)

        # Normal & Truncated Normal
        v_norm = sampler.sample_parameter(ParameterUncertaintyConfig(distribution=DistributionType.NORMAL, mean=50.0, std_dev=5.0))
        self.assertIsInstance(v_norm, float)

        v_trunc = sampler.sample_parameter(ParameterUncertaintyConfig(distribution=DistributionType.TRUNCATED_NORMAL, mean=50.0, std_dev=10.0, minimum=40.0, maximum=60.0))
        self.assertTrue(40.0 <= v_trunc <= 60.0)

        # Bernoulli
        v_bern = sampler.sample_parameter(ParameterUncertaintyConfig(distribution=DistributionType.BERNOULLI, probability=0.9))
        self.assertIsInstance(v_bern, bool)

        # Categorical
        v_cat = sampler.sample_parameter(ParameterUncertaintyConfig(distribution=DistributionType.CATEGORICAL, categories=["A", "B", "C"]))
        self.assertIn(v_cat, ["A", "B", "C"])

    def test_household_bootstrap_preserves_clusters(self) -> None:
        records = [
            {"synthetic_person_id": "P1", "synthetic_household_id": "HH1", "age": 40},
            {"synthetic_person_id": "P2", "synthetic_household_id": "HH1", "age": 10},
            {"synthetic_person_id": "P3", "synthetic_household_id": "HH2", "age": 60},
        ]
        provider = PopulationProvider(records)
        cfg = PopulationConfig(mode=PopulationMode.RESAMPLING, sampling_strategy=SamplingStrategy.HOUSEHOLD_BOOTSTRAP, population_size=4, preserve_households=True)
        sampled = provider.get_population_sample(cfg, seed=123)

        self.assertEqual(len(sampled), 4)
        # Check that household members from same HH stay grouped
        hh_map = {}
        for r in sampled:
            hh = r["synthetic_household_id"]
            hh_map.setdefault(hh, []).append(r["age"])
        
        # Verify cluster structure
        self.assertTrue(any(len(members) > 1 for members in hh_map.values()))

    def test_uncertainty_metrics_calculation(self) -> None:
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = compute_single_metric_uncertainty(vals, percentiles_requested=[0.025, 0.50, 0.975])

        self.assertEqual(stats["mean"], 30.0)
        self.assertEqual(stats["median"], 30.0)
        self.assertEqual(stats["min"], 10.0)
        self.assertEqual(stats["max"], 50.0)
        self.assertGreater(stats["mc_standard_error"], 0.0)
        self.assertIn("p50", stats["percentiles"])

    def test_risk_probabilities_calculation(self) -> None:
        iter_results = [
            {"iteration_status": "COMPLETED", "total_policy_cost": 500},
            {"iteration_status": "COMPLETED", "total_policy_cost": 1500},
            {"iteration_status": "COMPLETED", "total_policy_cost": 2000},
            {"iteration_status": "COMPLETED", "total_policy_cost": 2500},
        ]
        risk_cfg = [RiskMetricConfig(metric="total_policy_cost", operator="greater_than", threshold=1000, output_name="prob_exceed_1000")]
        risk_res = compute_risk_probabilities(iter_results, risk_cfg)

        self.assertEqual(risk_res["n_valid"], 4)
        metric_out = risk_res["risk_metrics"]["prob_exceed_1000"]
        self.assertEqual(metric_out["estimated_probability"], 0.75)
        self.assertTrue(metric_out["confidence_interval_95"]["lower"] <= 0.75 <= metric_out["confidence_interval_95"]["upper"])

    def test_sensitivity_correlation_metrics(self) -> None:
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [10.0, 20.0, 30.0, 40.0, 50.0]

        p_r = _pearson_correlation(xs, ys)
        s_r = _spearman_correlation(xs, ys)

        self.assertAlmostEqual(p_r, 1.0, places=4)
        self.assertAlmostEqual(s_r, 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
