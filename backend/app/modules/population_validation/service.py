from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any
import json

import yaml

from backend.app.modules.data_foundation.io_utils import read_csv, write_csv, write_json, write_md
from backend.app.modules.population_validation.alignment import load_canonical_schema, align_variables
from backend.app.modules.population_validation.metrics import (
    bounded_score,
    categorical_summary,
    categorical_values,
    correlation_ratio,
    cramers_v,
    jensen_shannon_divergence,
    ks_statistic,
    numeric_summary,
    numeric_values,
    paired_numeric,
    pearson,
    proportions,
    rounded,
    spearman,
    total_variation_distance,
    wasserstein_distance,
)
from backend.app.modules.synthetic_population.assessment import ROOT, read_json
from backend.app.modules.synthetic_population.constraints import ConstraintEngine


VALIDATION_VERSION = "phase4_population_validation_v1"
DEFAULT_CONFIG = {
    "quality_weights": {
        "distribution_fidelity": 0.30,
        "correlation_preservation": 0.30,
        "data_validity": 0.20,
        "statistical_similarity": 0.20,
    },
    "validity": {"soft_anomaly_penalty_weight": 0.10},
    "gates": {
        "pass_quality_score": 0.85,
        "warning_quality_score": 0.70,
        "minimum_critical_variable_fidelity": 0.80,
        "minimum_any_variable_fidelity": 0.65,
        "minimum_correlation_preservation": 0.65,
        "maximum_hard_violation_rate": 0.0,
    },
    "critical_relationships": [
        ["age", "employment_status"],
        ["education_level", "employment_status"],
        ["education_level", "individual_income"],
        ["employment_status", "individual_income"],
        ["gender", "employment_status"],
        ["district", "urban_rural"],
    ],
}
OFFICIAL_MARGINAL_FILES = {
    "gender": "data/calibration/gender_marginals.csv",
    "urban_rural": "data/calibration/urban_rural_marginals.csv",
    "social_group": "data/calibration/social_group_marginals.csv",
    "worker_category": "data/calibration/worker_marginals.csv",
}


class PopulationValidationService:
    def __init__(self, root: Path = ROOT, config_path: Path | None = None):
        self.root = root
        self.config = self._load_config(config_path or root / "config/population_validation/scoring.yaml")
        self.canonical_schema = load_canonical_schema(root)

    def validate(
        self,
        reference_population: list[dict[str, Any]],
        synthetic_population: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
        official_marginals: dict[str, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        official_marginals = official_marginals or {}
        variable_schema = metadata.get("variable_schema", {})
        alignment = align_variables(
            list(reference_population[0].keys()) if reference_population else [],
            list(synthetic_population[0].keys()) if synthetic_population else [],
            variable_schema,
            self.canonical_schema,
        )
        variable_metrics = self._variable_metrics(reference_population, synthetic_population, alignment["validated_variables"])
        relationship_metrics = self._relationship_metrics(reference_population, synthetic_population, alignment["validated_variables"])
        validity = self._validity_metrics(synthetic_population)
        official_metrics = self._official_marginal_metrics(synthetic_population, official_marginals)
        critical_variables = self._critical_variables(metadata, alignment["validated_variables"])
        scores = self._component_scores(variable_metrics, relationship_metrics, validity, official_metrics)
        gates = self._gate_results(scores, variable_metrics, relationship_metrics, validity, critical_variables)
        status = self._status(scores["quality_score"], gates)
        warnings = self._warnings(gates, variable_metrics, relationship_metrics, official_metrics, alignment["skipped_variables"])
        return {
            "validation_version": VALIDATION_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "population_id": metadata.get("population_id", "IN_MEMORY_POPULATION"),
            "model_id": metadata.get("model_id"),
            "generator_type": metadata.get("generator_type"),
            "generator_version": metadata.get("model_version") or metadata.get("generator_version"),
            "reference": metadata.get("reference", {}),
            "population_size": len(synthetic_population),
            "reference_size": len(reference_population),
            "alignment": alignment,
            "critical_variables": sorted(critical_variables),
            "variable_metrics": variable_metrics,
            "relationship_metrics": relationship_metrics,
            "validity_metrics": validity,
            "official_marginal_metrics": official_metrics,
            "component_scores": scores,
            "quality_score": scores["quality_score"],
            "validation_status": status,
            "gate_results": gates,
            "warnings": warnings,
            "methodology": self._methodology(),
        }

    def validate_from_phase4_manifest(self, manifest_path: Path | None = None) -> dict[str, Any]:
        manifest_path = manifest_path or self.root / "data/synthetic/phase4_validation_manifest.json"
        manifest = read_json(manifest_path)
        reference_path = self.root / manifest.get("prepared_reference_artifact", manifest.get("reference_population_artifact", ""))
        holdout_path = self.root / manifest.get("holdout_reference_artifact", "")
        reference_rows = read_csv(reference_path)
        holdout_rows = read_csv(holdout_path) if holdout_path.exists() else []
        official_marginals = self._load_official_marginals()
        reports = []
        for artifact in manifest.get("synthetic_population_artifacts", []):
            synthetic_rows = read_csv(self.root / artifact["population_artifact"])
            metadata = dict(artifact)
            metadata["reference"] = {
                "primary_reference_artifact": str(reference_path.relative_to(self.root)).replace("\\", "/"),
                "holdout_reference_artifact": str(holdout_path.relative_to(self.root)).replace("\\", "/") if holdout_rows else None,
                "reference_version": manifest.get("reference_version"),
                "training_dataset_version": manifest.get("training_dataset_version"),
            }
            report = self.validate(reference_rows, synthetic_rows, metadata, official_marginals)
            if holdout_rows:
                report["holdout_summary"] = self._holdout_summary(holdout_rows, synthetic_rows, metadata, official_marginals)
            self._write_population_outputs(report)
            reports.append(report)
        comparison = self.compare_reports(reports, manifest)
        self._write_comparison_outputs(comparison, reports)
        return comparison

    def compare_reports(self, reports: list[dict[str, Any]], manifest: dict[str, Any] | None = None) -> dict[str, Any]:
        manifest = manifest or {}
        sorted_reports = sorted(reports, key=lambda item: item.get("quality_score", 0), reverse=True)
        passing = [item for item in sorted_reports if item.get("validation_status") in {"PASS", "PASS_WITH_WARNINGS"}]
        selected = passing[0] if passing else None
        best = sorted_reports[0] if sorted_reports else None
        comparison_rows = []
        for report in sorted_reports:
            scores = report["component_scores"]
            comparison_rows.append({
                "population_id": report["population_id"],
                "model_id": report.get("model_id", ""),
                "generator_type": report.get("generator_type", ""),
                "population_size": report.get("population_size", 0),
                "distribution_fidelity": rounded(scores["distribution_fidelity"]),
                "correlation_preservation": rounded(scores["correlation_preservation"]),
                "data_validity": rounded(scores["data_validity"]),
                "statistical_similarity": rounded(scores["statistical_similarity"]),
                "quality_score": rounded(report["quality_score"]),
                "validation_status": report["validation_status"],
                "warning_count": len(report.get("warnings", [])),
            })
        selection = {
            "selected_model_id": selected.get("model_id") if selected else None,
            "selected_population_id": selected.get("population_id") if selected else None,
            "generator": selected.get("generator_type") if selected else None,
            "quality_score": rounded(selected.get("quality_score")) if selected else None,
            "validation_status": selected.get("validation_status") if selected else "NO_PASSING_POPULATION",
            "reason": self._selection_reason(selected, best),
            "important_warnings": (selected or best or {}).get("warnings", [])[:10],
            "highest_scoring_population_id": best.get("population_id") if best else None,
        }
        return {
            "validation_version": VALIDATION_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reference_population_artifact": manifest.get("prepared_reference_artifact") or manifest.get("reference_population_artifact"),
            "holdout_reference_artifact": manifest.get("holdout_reference_artifact"),
            "models_evaluated": len(reports),
            "comparison": comparison_rows,
            "selection": selection,
            "calibration_handoff": self._calibration_handoff(selected, best),
            "known_limitations": [
                "Population validation measures statistical fidelity, not causal validity or privacy protection.",
                "Official marginal comparison is limited to calibration files whose categories map directly to synthetic variables.",
                "Parquet validation outputs are emitted as CSV because no parquet writer dependency is available in this project runtime.",
            ],
        }

    def _variable_metrics(
        self,
        reference_rows: list[dict[str, Any]],
        synthetic_rows: list[dict[str, Any]],
        variables: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        metrics = []
        for item in variables:
            variable = item["variable"]
            if item["validation_family"] == "numerical":
                ref_values = numeric_values(reference_rows, variable)
                syn_values = numeric_values(synthetic_rows, variable)
                ks = ks_statistic(ref_values, syn_values)
                wasserstein = wasserstein_distance(ref_values, syn_values)
                ref_range = self._reference_scale(ref_values)
                normalized_wasserstein = min((wasserstein or 0.0) / ref_range, 1.0) if ref_range else 0.0
                missing_score = self._missingness_score(reference_rows, synthetic_rows, variable)
                distribution_score = bounded_score(((1 - (ks or 1.0)) + (1 - normalized_wasserstein) + missing_score) / 3)
                metric = {
                    "variable": variable,
                    "variable_type": item["variable_type"],
                    "validation_family": "numerical",
                    "reference": numeric_summary(reference_rows, variable),
                    "synthetic": numeric_summary(synthetic_rows, variable),
                    "metrics": {
                        "ks_statistic": rounded(ks),
                        "wasserstein_distance": rounded(wasserstein),
                        "reference_scale_for_wasserstein": rounded(ref_range),
                        "normalized_wasserstein_distance": rounded(normalized_wasserstein),
                        "missingness_score": rounded(missing_score),
                    },
                    "fidelity_score": rounded(distribution_score),
                    "warnings": [],
                    "validation_status": "PASS" if distribution_score >= self.config["gates"]["minimum_any_variable_fidelity"] else "WARN",
                }
            else:
                ref_values = categorical_values(reference_rows, variable)
                syn_values = categorical_values(synthetic_rows, variable)
                ref_props = proportions(ref_values)
                syn_props = proportions(syn_values)
                js = jensen_shannon_divergence(ref_props, syn_props)
                tvd = total_variation_distance(ref_props, syn_props)
                missing_score = self._missingness_score(reference_rows, synthetic_rows, variable)
                distribution_score = bounded_score(((1 - js) + (1 - tvd) + missing_score) / 3)
                metric = {
                    "variable": variable,
                    "variable_type": item["variable_type"],
                    "validation_family": "categorical",
                    "reference": categorical_summary(reference_rows, variable),
                    "synthetic": categorical_summary(synthetic_rows, variable),
                    "metrics": {
                        "jensen_shannon_divergence": rounded(js),
                        "total_variation_distance": rounded(tvd),
                        "missingness_score": rounded(missing_score),
                        "missing_from_synthetic": sorted(set(ref_props) - set(syn_props)),
                        "unexpected_in_synthetic": sorted(set(syn_props) - set(ref_props)),
                    },
                    "fidelity_score": rounded(distribution_score),
                    "warnings": [],
                    "validation_status": "PASS" if distribution_score >= self.config["gates"]["minimum_any_variable_fidelity"] else "WARN",
                }
            if metric["metrics"].get("missing_from_synthetic"):
                metric["warnings"].append("Reference categories are missing from synthetic population.")
            if metric["metrics"].get("unexpected_in_synthetic"):
                metric["warnings"].append("Synthetic population contains categories absent from the reference.")
            metrics.append(metric)
        return metrics

    def _relationship_metrics(
        self,
        reference_rows: list[dict[str, Any]],
        synthetic_rows: list[dict[str, Any]],
        variables: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_name = {item["variable"]: item for item in variables}
        rows = []
        for left, right in combinations(sorted(by_name), 2):
            left_family = by_name[left]["validation_family"]
            right_family = by_name[right]["validation_family"]
            if left_family == "numerical" and right_family == "numerical":
                ref_metric = self._numeric_relationship(reference_rows, left, right)
                syn_metric = self._numeric_relationship(synthetic_rows, left, right)
                relationship_type = "pearson_spearman_average"
                scale = 2.0
            elif left_family == "categorical" and right_family == "categorical":
                ref_metric = cramers_v(reference_rows, left, right)
                syn_metric = cramers_v(synthetic_rows, left, right)
                relationship_type = "cramers_v"
                scale = 1.0
            else:
                category, numeric = (left, right) if left_family == "categorical" else (right, left)
                ref_metric = correlation_ratio(reference_rows, category, numeric)
                syn_metric = correlation_ratio(synthetic_rows, category, numeric)
                relationship_type = "correlation_ratio_eta"
                scale = 1.0
            if ref_metric is None or syn_metric is None:
                continue
            difference = abs(ref_metric - syn_metric)
            preservation_score = bounded_score(1 - min(difference / scale, 1.0))
            rows.append({
                "variable_a": left,
                "variable_b": right,
                "relationship_type": relationship_type,
                "reference_metric": rounded(ref_metric),
                "synthetic_metric": rounded(syn_metric),
                "difference": rounded(difference),
                "preservation_score": rounded(preservation_score),
                "critical_relationship": [left, right] in self.config.get("critical_relationships", []) or [right, left] in self.config.get("critical_relationships", []),
            })
        return rows

    def _numeric_relationship(self, rows: list[dict[str, Any]], left: str, right: str) -> float | None:
        x_values, y_values = paired_numeric(rows, left, right)
        pearson_value = pearson(x_values, y_values)
        spearman_value = spearman(x_values, y_values)
        values = [abs(value) for value in [pearson_value, spearman_value] if value is not None]
        if not values:
            return None
        sign = 1 if (pearson_value or spearman_value or 0) >= 0 else -1
        return sign * sum(values) / len(values)

    def _validity_metrics(self, synthetic_rows: list[dict[str, Any]]) -> dict[str, Any]:
        summary = ConstraintEngine().validate_rows(synthetic_rows)
        total = summary["total_records"]
        hard_rows = summary.get("hard_violation_row_count", len({item["row_number"] for item in summary.get("sample_hard_violations", [])}))
        hard_rate = summary["hard_violation_rate"] / 100 if total else 0
        soft_rate = summary["soft_anomaly_rate"] / 100 if total else 0
        soft_weight = float(self.config.get("validity", {}).get("soft_anomaly_penalty_weight", 0.10))
        score = bounded_score((1 - hard_rate) * (1 - soft_weight) + (1 - soft_rate) * soft_weight)
        summary.update({
            "valid_rows": max(total - hard_rows, 0),
            "invalid_rows": hard_rows,
            "validity_rate": rounded(1 - hard_rate),
            "validity_score": rounded(score),
        })
        return summary

    def _official_marginal_metrics(
        self,
        synthetic_rows: list[dict[str, Any]],
        official_marginals: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        results = []
        synthetic_columns = set(synthetic_rows[0]) if synthetic_rows else set()
        for variable, rows in official_marginals.items():
            if variable not in synthetic_columns or not rows:
                continue
            official_props = {str(row[variable]): float(row.get("proportion", 0) or 0) for row in rows if row.get(variable)}
            synthetic_props = proportions(categorical_values(synthetic_rows, variable))
            js = jensen_shannon_divergence(official_props, synthetic_props)
            tvd = total_variation_distance(official_props, synthetic_props)
            results.append({
                "variable": variable,
                "reference_type": "official_marginal",
                "jensen_shannon_divergence": rounded(js),
                "total_variation_distance": rounded(tvd),
                "score": rounded(bounded_score(1 - ((js + tvd) / 2))),
                "official_categories": sorted(official_props),
                "synthetic_categories": sorted(synthetic_props),
            })
        return results

    def _component_scores(
        self,
        variable_metrics: list[dict[str, Any]],
        relationship_metrics: list[dict[str, Any]],
        validity: dict[str, Any],
        official_metrics: list[dict[str, Any]],
    ) -> dict[str, float]:
        distribution = self._average([item["fidelity_score"] for item in variable_metrics])
        correlation = self._average([item["preservation_score"] for item in relationship_metrics])
        validity_score = validity.get("validity_score", 0.0)
        official_score = self._average([item["score"] for item in official_metrics]) if official_metrics else distribution
        statistical = self._average([distribution, correlation, official_score])
        weights = self.config["quality_weights"]
        quality = (
            distribution * weights["distribution_fidelity"]
            + correlation * weights["correlation_preservation"]
            + validity_score * weights["data_validity"]
            + statistical * weights["statistical_similarity"]
        )
        return {
            "distribution_fidelity": rounded(distribution),
            "correlation_preservation": rounded(correlation),
            "data_validity": rounded(validity_score),
            "official_marginal_similarity": rounded(official_score),
            "statistical_similarity": rounded(statistical),
            "quality_score": rounded(quality),
        }

    def _gate_results(
        self,
        scores: dict[str, float],
        variable_metrics: list[dict[str, Any]],
        relationship_metrics: list[dict[str, Any]],
        validity: dict[str, Any],
        critical_variables: set[str],
    ) -> list[dict[str, Any]]:
        gates = self.config["gates"]
        results = []
        hard_rate = validity.get("hard_violation_rate", 0.0)
        results.append(self._gate("hard_validity", hard_rate <= gates["maximum_hard_violation_rate"], hard_rate, gates["maximum_hard_violation_rate"]))
        for item in variable_metrics:
            threshold = gates["minimum_critical_variable_fidelity"] if item["variable"] in critical_variables else gates["minimum_any_variable_fidelity"]
            results.append(self._gate(f"variable_fidelity:{item['variable']}", item["fidelity_score"] >= threshold, item["fidelity_score"], threshold))
        critical_relationships = [item for item in relationship_metrics if item.get("critical_relationship")]
        relationship_pool = critical_relationships or relationship_metrics
        for item in relationship_pool:
            name = f"relationship:{item['variable_a']}:{item['variable_b']}"
            results.append(self._gate(name, item["preservation_score"] >= gates["minimum_correlation_preservation"], item["preservation_score"], gates["minimum_correlation_preservation"]))
        results.append(self._gate("minimum_quality_for_warning", scores["quality_score"] >= gates["warning_quality_score"], scores["quality_score"], gates["warning_quality_score"]))
        return results

    def _status(self, quality_score: float, gates: list[dict[str, Any]]) -> str:
        failed = [item for item in gates if not item["passed"]]
        if failed:
            return "FAIL"
        if quality_score >= self.config["gates"]["pass_quality_score"]:
            return "PASS"
        return "PASS_WITH_WARNINGS"

    def _warnings(
        self,
        gates: list[dict[str, Any]],
        variable_metrics: list[dict[str, Any]],
        relationship_metrics: list[dict[str, Any]],
        official_metrics: list[dict[str, Any]],
        skipped_variables: list[dict[str, Any]],
    ) -> list[str]:
        warnings = [f"Gate failed: {item['name']} observed={item['observed']} threshold={item['threshold']}" for item in gates if not item["passed"]]
        warnings.extend(f"{item['variable']}: {warning}" for item in variable_metrics for warning in item.get("warnings", []))
        weak_relationships = [item for item in relationship_metrics if item["preservation_score"] < self.config["gates"]["minimum_correlation_preservation"]]
        warnings.extend(f"Weak relationship preservation: {item['variable_a']} vs {item['variable_b']} score={item['preservation_score']}" for item in weak_relationships[:10])
        warnings.extend(f"Official marginal comparison weak for {item['variable']} score={item['score']}" for item in official_metrics if item["score"] < self.config["gates"]["minimum_any_variable_fidelity"])
        missing = [item["variable"] for item in skipped_variables if item["status"] == "MISSING_IN_SYNTHETIC"]
        if missing:
            warnings.append(f"Variables present in reference but missing from synthetic population: {', '.join(missing[:20])}")
        return warnings

    def _critical_variables(self, metadata: dict[str, Any], validated_variables: list[dict[str, Any]]) -> set[str]:
        validated = {item["variable"] for item in validated_variables}
        critical = set(metadata.get("critical_variables", []))
        requirements = read_json(self.root / "data/compatibility/synthetic_population_requirements.json") if self.root.exists() else {}
        for item in requirements.values():
            req = item.get("synthetic_population_requirements", {})
            critical.update(req.get("critical_variables", []))
            critical.update(req.get("calibration_variables", []))
            if "household_income" in req.get("approved_proxies", []) and "consumption_expenditure" in validated:
                critical.add("consumption_expenditure")
        return critical & validated

    def _holdout_summary(
        self,
        holdout_rows: list[dict[str, Any]],
        synthetic_rows: list[dict[str, Any]],
        metadata: dict[str, Any],
        official_marginals: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        report = self.validate(holdout_rows, synthetic_rows, {**metadata, "critical_variables": []}, official_marginals)
        return {
            "reference_size": report["reference_size"],
            "distribution_fidelity": report["component_scores"]["distribution_fidelity"],
            "correlation_preservation": report["component_scores"]["correlation_preservation"],
            "statistical_similarity": report["component_scores"]["statistical_similarity"],
            "validation_status": report["validation_status"],
        }

    def _load_official_marginals(self) -> dict[str, list[dict[str, Any]]]:
        out = {}
        for variable, relative in OFFICIAL_MARGINAL_FILES.items():
            path = self.root / relative
            if path.exists():
                out[variable] = read_csv(path)
        return out

    def _write_population_outputs(self, report: dict[str, Any]) -> None:
        population_id = report["population_id"]
        out_dir = self.root / "artifacts/validation" / population_id
        write_json(out_dir / "validation_report.json", self._json_ready(report))
        write_csv(out_dir / "variable_metrics.csv", [self._flat_row(item) for item in report["variable_metrics"]])
        write_csv(out_dir / "relationship_metrics.csv", [self._flat_row(item) for item in report["relationship_metrics"]])
        write_json(out_dir / "validity_metrics.json", self._json_ready(report["validity_metrics"]))
        write_csv(out_dir / "official_marginal_metrics.csv", [self._flat_row(item) for item in report["official_marginal_metrics"]])
        write_md(self.root / "reports/population_validation" / f"{population_id}_validation_report.md", self._population_report(report))

    def _write_comparison_outputs(self, comparison: dict[str, Any], reports: list[dict[str, Any]]) -> None:
        write_json(self.root / "artifacts/validation/phase4_model_comparison.json", self._json_ready(comparison))
        write_csv(self.root / "artifacts/validation/model_comparison.csv", comparison["comparison"])
        write_json(self.root / "data/synthetic/phase5_calibration_handoff.json", self._json_ready(comparison["calibration_handoff"]))
        write_md(self.root / "reports/phase4_model_comparison.md", self._comparison_report(comparison))
        write_md(self.root / "reports/phase4_summary.md", self._summary_report(comparison, reports))

    def _population_report(self, report: dict[str, Any]) -> str:
        scores = report["component_scores"]
        lines = [
            f"# Population Validation Report: {report['population_id']}",
            "",
            f"- Generator: {report.get('generator_type')}",
            f"- Model ID: {report.get('model_id')}",
            f"- Reference rows: {report['reference_size']}",
            f"- Synthetic rows: {report['population_size']}",
            f"- Quality score: {report['quality_score']}",
            f"- Validation status: {report['validation_status']}",
            f"- Distribution fidelity: {scores['distribution_fidelity']}",
            f"- Correlation preservation: {scores['correlation_preservation']}",
            f"- Data validity: {scores['data_validity']}",
            f"- Statistical similarity: {scores['statistical_similarity']}",
            "",
            "## Warnings",
            "",
        ]
        lines.extend(f"- {warning}" for warning in report.get("warnings", [])[:20])
        if not report.get("warnings"):
            lines.append("- None")
        lines.extend([
            "",
            "## Lowest Variable Fidelity",
            "",
        ])
        for item in sorted(report["variable_metrics"], key=lambda row: row["fidelity_score"])[:8]:
            lines.append(f"- {item['variable']}: {item['fidelity_score']} ({item['validation_family']})")
        lines.extend([
            "",
            "## Weakest Relationships",
            "",
        ])
        for item in sorted(report["relationship_metrics"], key=lambda row: row["preservation_score"])[:8]:
            lines.append(f"- {item['variable_a']} vs {item['variable_b']}: {item['preservation_score']} ({item['relationship_type']})")
        if "holdout_summary" in report:
            lines.extend([
                "",
                "## Holdout Check",
                "",
                f"- Holdout reference rows: {report['holdout_summary']['reference_size']}",
                f"- Holdout distribution fidelity: {report['holdout_summary']['distribution_fidelity']}",
                f"- Holdout correlation preservation: {report['holdout_summary']['correlation_preservation']}",
            ])
        lines.extend([
            "",
            "## Methodology Note",
            "",
            "Scores are normalized before aggregation. Population validation does not prove causal validity, privacy protection, or policy outcome accuracy.",
        ])
        return "\n".join(lines)

    def _comparison_report(self, comparison: dict[str, Any]) -> str:
        lines = [
            "# Phase 4 Model Comparison",
            "",
            f"- Reference population: {comparison.get('reference_population_artifact')}",
            f"- Holdout reference: {comparison.get('holdout_reference_artifact')}",
            f"- Models evaluated: {comparison['models_evaluated']}",
            "",
            "## Scores",
            "",
            "| Population | Generator | Distribution | Correlation | Validity | Similarity | Quality | Status |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        for item in comparison["comparison"]:
            lines.append(
                f"| {item['population_id']} | {item['generator_type']} | {item['distribution_fidelity']} | "
                f"{item['correlation_preservation']} | {item['data_validity']} | {item['statistical_similarity']} | "
                f"{item['quality_score']} | {item['validation_status']} |"
            )
        selection = comparison["selection"]
        lines.extend([
            "",
            "## Selection",
            "",
            f"- Selected population: {selection['selected_population_id'] or 'None'}",
            f"- Selected model: {selection['selected_model_id'] or 'None'}",
            f"- Status: {selection['validation_status']}",
            f"- Reason: {selection['reason']}",
            "",
            "## Known Limitations",
            "",
        ])
        lines.extend(f"- {item}" for item in comparison["known_limitations"])
        return "\n".join(lines)

    def _summary_report(self, comparison: dict[str, Any], reports: list[dict[str, Any]]) -> str:
        variables = sorted({metric["variable"] for report in reports for metric in report["variable_metrics"]})
        skipped = sorted({item["variable"] + ": " + item["status"] for report in reports for item in report["alignment"]["skipped_variables"]})
        synthetic = [report["population_id"] for report in reports]
        handoff = comparison["calibration_handoff"]
        lines = [
            "# Phase 4 Summary",
            "",
            f"1. Reference data used: `{comparison.get('reference_population_artifact')}` with holdout `{comparison.get('holdout_reference_artifact')}`.",
            f"2. Synthetic populations validated: {', '.join(synthetic)}.",
            "3. Models that produced them: " + ", ".join(sorted({str(report.get("generator_type")) for report in reports})),
            "4. Variables validated: " + ", ".join(variables),
            "5. Variables skipped: " + ("; ".join(skipped[:30]) if skipped else "None"),
            "6. Distribution fidelity: KS and scale-normalized Wasserstein for numeric fields; Jensen-Shannon divergence and total variation distance for categorical fields.",
            "7. Correlation preservation: Pearson/Spearman average for numeric pairs, Cramer's V for categorical pairs, and eta for mixed pairs.",
            "8. Data validity: reused the Phase 3 constraint engine for hard ranges, canonical categories, and configured soft anomalies.",
            "9. Statistical similarity: average of distribution, relationship, and official-marginal similarity components.",
            "10. Quality score: configurable weighted composite from `config/population_validation/scoring.yaml`.",
            f"11. Population that passed validation: {handoff.get('population_id') if handoff.get('selected_for_calibration') else 'None'}",
            f"12. Best performing population: {comparison['selection'].get('highest_scoring_population_id')}",
            "13. Weaknesses remain: see per-population warnings and weakest relationships in `reports/population_validation/`.",
            f"14. Calibration phase should receive: `data/synthetic/phase5_calibration_handoff.json`.",
        ]
        return "\n".join(lines)

    def _calibration_handoff(self, selected: dict[str, Any] | None, best: dict[str, Any] | None) -> dict[str, Any]:
        report = selected or best or {}
        largest_gaps = sorted(
            [
                {"variable": item["variable"], "fidelity_score": item["fidelity_score"]}
                for item in report.get("variable_metrics", [])
            ],
            key=lambda item: item["fidelity_score"],
        )[:8]
        official = [item["variable"] for item in report.get("official_marginal_metrics", [])]
        return {
            "population_id": selected.get("population_id") if selected else None,
            "model_id": selected.get("model_id") if selected else None,
            "generator_type": selected.get("generator_type") if selected else None,
            "validation_status": selected.get("validation_status") if selected else "NO_PASSING_POPULATION",
            "quality_score": selected.get("quality_score") if selected else None,
            "selected_for_calibration": selected is not None,
            "calibration_priority_variables": [item["variable"] for item in largest_gaps],
            "largest_marginal_gaps": largest_gaps,
            "official_targets_available": sorted(set(official)),
            "warnings": (selected or best or {}).get("warnings", [])[:20],
            "highest_scoring_population_id": best.get("population_id") if best else None,
        }

    def _selection_reason(self, selected: dict[str, Any] | None, best: dict[str, Any] | None) -> str:
        if selected:
            return "Selected highest-scoring population that passed all configured Phase 4 gates."
        if best:
            return "No population passed all configured gates; highest-scoring population is reported for diagnosis only and is not selected for calibration."
        return "No synthetic populations were available for validation."

    def _methodology(self) -> dict[str, Any]:
        return {
            "numeric_distribution": "fidelity = average(1 - KS, 1 - Wasserstein/reference_scale, missingness_score)",
            "categorical_distribution": "fidelity = average(1 - Jensen-Shannon divergence, 1 - Total Variation Distance, missingness_score)",
            "reference_scale": "max-min of the reference variable, falling back to 1 when the reference is constant",
            "relationship_preservation": "1 - normalized absolute difference between reference and synthetic association measures",
            "quality_score": "weighted composite configured in config/population_validation/scoring.yaml",
            "status": "PASS/PASS_WITH_WARNINGS/FAIL is gate based and separate from the numeric score",
        }

    def _load_config(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return DEFAULT_CONFIG
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        for key, value in loaded.items():
            if isinstance(value, dict) and isinstance(config.get(key), dict):
                config[key].update(value)
            else:
                config[key] = value
        return config

    def _reference_scale(self, values: list[float]) -> float:
        if not values:
            return 1.0
        span = max(values) - min(values)
        return span if span > 0 else 1.0

    def _missingness_score(self, reference_rows: list[dict[str, Any]], synthetic_rows: list[dict[str, Any]], variable: str) -> float:
        ref_missing = numeric_summary(reference_rows, variable)["missing_percentage"] if self._mostly_numeric(reference_rows, variable) else categorical_summary(reference_rows, variable)["missing_percentage"]
        syn_missing = numeric_summary(synthetic_rows, variable)["missing_percentage"] if self._mostly_numeric(synthetic_rows, variable) else categorical_summary(synthetic_rows, variable)["missing_percentage"]
        return bounded_score(1 - abs(ref_missing - syn_missing) / 100)

    def _mostly_numeric(self, rows: list[dict[str, Any]], variable: str) -> bool:
        values = [row.get(variable) for row in rows[:100] if row.get(variable) not in {"", None}]
        if not values:
            return False
        numeric_count = sum(1 for value in values if self._can_float(value))
        return numeric_count == len(values)

    def _can_float(self, value: Any) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    def _average(self, values: list[float | None]) -> float:
        clean = [float(value) for value in values if value is not None]
        return sum(clean) / len(clean) if clean else 0.0

    def _gate(self, name: str, passed: bool, observed: Any, threshold: Any) -> dict[str, Any]:
        return {"name": name, "passed": bool(passed), "observed": rounded(observed) if isinstance(observed, float) else observed, "threshold": threshold}

    def _flat_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()}

    def _json_ready(self, value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False))


def run_phase4_validation(root: Path = ROOT) -> dict[str, Any]:
    return PopulationValidationService(root).validate_from_phase4_manifest()
