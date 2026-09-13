"""
Benchmark loader for official government ground-truth observed results.
"""

import os
from typing import List, Dict, Any
from ..data_foundation.io_utils import read_csv, read_json
from .validation_model import BenchmarkMetric

class BenchmarkLoader:
    """Loads official ground truth observed results from CSV and JSON manifests."""

    @staticmethod
    def load_observed_results(csv_path: str) -> List[BenchmarkMetric]:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Observed benchmark results file not found: {csv_path}")

        records = read_csv(csv_path)
        benchmarks = []
        for r in records:
            try:
                val = float(r["metric_value"])
            except (ValueError, KeyError):
                val = 0.0

            benchmarks.append(
                BenchmarkMetric(
                    policy_id=r.get("policy_id", "tn_kmut_2023"),
                    reporting_period=r.get("reporting_period", "FY 2023-24"),
                    geographic_level=r.get("geographic_level", "Statewide"),
                    geographic_code=str(r.get("geographic_code", "33")),
                    geographic_name=r.get("geographic_name", "Tamil Nadu"),
                    metric_name=r.get("metric_name", "approved_beneficiaries"),
                    metric_value=val,
                    metric_unit=r.get("metric_unit", "Households"),
                    source_id=r.get("source_id", "SRC_001"),
                )
            )

        return benchmarks
