"""
Source reconciler for official government publications and audit reports.
"""

import os
from typing import Dict, Any, List
from ..data_foundation.io_utils import read_json

class SourceReconciler:
    """Reconciles conflicting official government data points across policy notes, budget speeches, and CAG reports."""

    @staticmethod
    def load_reconciliation(json_path: str) -> Dict[str, Any]:
        if not os.path.exists(json_path):
            return {"status": "NO_RECONCILIATION_FILE"}

        data = read_json(json_path)
        reconciled = {}
        for rec in data.get("reconciliation_records", []):
            reconciled[rec["metric"]] = rec["selected_benchmark"]

        return {
            "policy_id": data.get("policy_id", "tn_kmut_2023"),
            "reconciled_metrics": reconciled,
            "raw_records": data.get("reconciliation_records", []),
        }
