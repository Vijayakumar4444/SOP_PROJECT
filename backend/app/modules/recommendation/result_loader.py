"""
Loads Phase 7 Monte Carlo experiment outputs for recommendation evaluation.
"""

import os
import json
from typing import Dict, Any, List
from ..data_foundation.io_utils import read_json, read_csv
from .recommendation_model import CandidatePolicyResult, CandidateExperimentConfig

class ExperimentResultLoader:
    """Loads Phase 7 Monte Carlo experiment outputs into CandidatePolicyResult data structure."""

    @staticmethod
    def load_candidate(candidate_config: CandidateExperimentConfig, base_dir: str = ".") -> CandidatePolicyResult:
        exp_path = candidate_config.path
        if not os.path.isabs(exp_path):
            exp_path = os.path.join(base_dir, exp_path)

        if not os.path.exists(exp_path):
            raise FileNotFoundError(f"Experiment artifact directory not found: {exp_path}")

        meta_path = os.path.join(exp_path, "experiment_metadata.json")
        unc_path = os.path.join(exp_path, "uncertainty_summary.json")
        risk_path = os.path.join(exp_path, "risk_probabilities.json")
        conv_path = os.path.join(exp_path, "convergence_report.json")
        sens_path = os.path.join(exp_path, "sensitivity_report.json")
        csv_path = os.path.join(exp_path, "iteration_results.csv")

        metadata = read_json(meta_path) if os.path.exists(meta_path) else {}
        uncertainty = read_json(unc_path) if os.path.exists(unc_path) else {}
        risk_probs = read_json(risk_path) if os.path.exists(risk_path) else {}
        convergence = read_json(conv_path) if os.path.exists(conv_path) else {}
        sensitivity = read_json(sens_path) if os.path.exists(sens_path) else {}

        iteration_records = []
        if os.path.exists(csv_path):
            try:
                iteration_records = read_csv(csv_path)
            except Exception:
                iteration_records = []

        # Extract raw metrics from metrics_summary or metrics
        metrics_sec = uncertainty.get("metrics_summary", {}) or uncertainty.get("metrics", {})

        total_cost_unc = metrics_sec.get("total_policy_cost", {}) or metrics_sec.get("total_cost", {})
        beneficiary_unc = metrics_sec.get("beneficiary_count", {}) or metrics_sec.get("beneficiaries", {})

        mean_total_cost = float(total_cost_unc.get("mean", 0.0))
        p95_total_cost = float(total_cost_unc.get("percentiles", {}).get("p95", total_cost_unc.get("percentiles", {}).get("P95", mean_total_cost * 1.15)))
        p5_total_cost = float(total_cost_unc.get("percentiles", {}).get("p5", total_cost_unc.get("percentiles", {}).get("P5", mean_total_cost * 0.85)))
        std_total_cost = float(total_cost_unc.get("std_dev", 0.0))
        relative_mc_error = float(total_cost_unc.get("relative_mc_error", 0.01))

        mean_beneficiaries = float(beneficiary_unc.get("mean", 0.0))
        std_beneficiaries = float(beneficiary_unc.get("std_dev", 0.0))

        risk_dict = risk_probs.get("risk_probabilities", {}) or risk_probs.get("risk_metrics", {})
        budget_exceedance_risk = float(risk_dict.get("budget_exceedance", risk_dict.get("budget_exceedance_probability", 0.0)))

        raw_metrics = {
            "mean_total_cost": mean_total_cost,
            "p95_total_cost": p95_total_cost,
            "p5_total_cost": p5_total_cost,
            "std_total_cost": std_total_cost,
            "mean_beneficiaries": mean_beneficiaries,
            "std_beneficiaries": std_beneficiaries,
            "budget_exceedance_risk": budget_exceedance_risk,
            "relative_mc_error": relative_mc_error,
        }

        return CandidatePolicyResult(
            experiment_id=candidate_config.experiment_id,
            display_name=candidate_config.display_name,
            policy_type=candidate_config.policy_type,
            raw_metrics=raw_metrics,
            metadata=metadata,
            uncertainty_summary=uncertainty,
            risk_probabilities=risk_probs,
            convergence_report=convergence,
            sensitivity_report=sensitivity,
            iteration_records=iteration_records,
        )

    @staticmethod
    def load_all(candidate_configs: List[CandidateExperimentConfig], base_dir: str = ".") -> List[CandidatePolicyResult]:
        results = []
        for cfg in candidate_configs:
            res = ExperimentResultLoader.load_candidate(cfg, base_dir=base_dir)
            results.append(res)
        return results
