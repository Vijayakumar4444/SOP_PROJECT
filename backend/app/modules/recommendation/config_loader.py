"""
Configuration loader for Phase 8 Recommendation Engine.
"""

import os
import json
import yaml
from typing import Dict, Any
from .recommendation_model import (
    RecommendationConfig,
    CandidateExperimentConfig,
    FeasibilityConstraintConfig,
    MetricConfig,
    StakeholderProfileConfig,
)

class RecommendationConfigLoader:
    """Loads Recommendation engine configuration files from YAML or JSON."""

    @staticmethod
    def load_from_file(config_path: str) -> RecommendationConfig:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Recommendation config file not found: {config_path}")

        ext = os.path.splitext(config_path)[1].lower()
        with open(config_path, "r", encoding="utf-8") as f:
            if ext in [".yaml", ".yml"]:
                raw_dict = yaml.safe_load(f)
            elif ext == ".json":
                raw_dict = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file extension: {ext}")

        return RecommendationConfigLoader.from_dict(raw_dict)

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> RecommendationConfig:
        candidates = [
            CandidateExperimentConfig(
                experiment_id=c["experiment_id"],
                path=c["path"],
                display_name=c["display_name"],
                policy_type=c.get("policy_type", "generic"),
            )
            for c in raw.get("candidate_experiments", [])
        ]

        fc_raw = raw.get("feasibility_constraints", {})
        feasibility_constraints = FeasibilityConstraintConfig(
            max_budget=fc_raw.get("max_budget"),
            max_risk_probability=fc_raw.get("max_risk_probability"),
            min_coverage=fc_raw.get("min_coverage"),
            max_relative_mc_error=fc_raw.get("max_relative_mc_error"),
        )

        norm_raw = raw.get("normalization", {})
        normalization_method = norm_raw.get("method", "min_max") if isinstance(norm_raw, dict) else norm_raw

        metrics = [
            MetricConfig(
                name=m["name"],
                direction=m.get("direction", "minimize").lower(),
                weight=float(m.get("weight", 0.25)),
                display_name=m.get("display_name", m["name"]),
            )
            for m in raw.get("metrics", [])
        ]

        profiles = [
            StakeholderProfileConfig(
                name=p["name"],
                description=p.get("description", ""),
                weights={k: float(v) for k, v in p.get("weights", {}).items()},
            )
            for p in raw.get("stakeholder_profiles", [])
        ]

        ranking_raw = raw.get("ranking", {})
        if isinstance(ranking_raw, dict):
            ranking_method = ranking_raw.get("method", "weighted_sum")
            enable_pareto = ranking_raw.get("enable_pareto", True)
            enable_fairness_analysis = ranking_raw.get("enable_fairness_analysis", True)
            enable_tradeoff_analysis = ranking_raw.get("enable_tradeoff_analysis", True)
            enable_weight_sensitivity = ranking_raw.get("enable_weight_sensitivity", True)
        else:
            ranking_method = str(ranking_raw)
            enable_pareto = True
            enable_fairness_analysis = True
            enable_tradeoff_analysis = True
            enable_weight_sensitivity = True

        output_raw = raw.get("output", {})

        return RecommendationConfig(
            version=str(raw.get("version", "1.0")),
            recommendation_id=str(raw.get("recommendation_id", "tn_rec_default")),
            title=str(raw.get("title", "Tamil Nadu Policy Recommendation")),
            description=str(raw.get("description", "")),
            created_at=str(raw.get("created_at", "2026-09-14T00:00:00Z")),
            candidate_experiments=candidates,
            feasibility_constraints=feasibility_constraints,
            normalization_method=normalization_method,
            metrics=metrics,
            stakeholder_profiles=profiles,
            ranking_method=ranking_method,
            enable_pareto=enable_pareto,
            enable_fairness_analysis=enable_fairness_analysis,
            enable_tradeoff_analysis=enable_tradeoff_analysis,
            enable_weight_sensitivity=enable_weight_sensitivity,
            output_dir=output_raw.get("artifact_dir", "artifacts/recommendation"),
            summary_json=output_raw.get("summary_json", "recommendation_summary.json"),
            ranking_csv=output_raw.get("ranking_csv", "ranking_results.csv"),
            tradeoff_json=output_raw.get("tradeoff_json", "tradeoff_report.json"),
            fairness_json=output_raw.get("fairness_json", "fairness_report.json"),
            report_md=output_raw.get("report_md", "recommendation_report.md"),
            handoff_manifest=output_raw.get("handoff_manifest", "data/synthetic/phase8_recommendation_handoff.json"),
        )
