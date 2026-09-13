"""
Centralized metric registry for recommendation evaluation metrics.
"""

from typing import Dict, Any, Optional

METRIC_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "mean_total_cost": {
        "display_name": "Mean Total Fiscal Cost",
        "direction": "minimize",
        "unit": "INR",
        "default_weight": 0.35,
    },
    "p95_total_cost": {
        "display_name": "P95 Tail Fiscal Cost",
        "direction": "minimize",
        "unit": "INR",
        "default_weight": 0.15,
    },
    "p5_total_cost": {
        "display_name": "P5 Min Fiscal Cost",
        "direction": "minimize",
        "unit": "INR",
        "default_weight": 0.05,
    },
    "mean_beneficiaries": {
        "display_name": "Mean Beneficiary Headcount",
        "direction": "maximize",
        "unit": "Persons/Households",
        "default_weight": 0.30,
    },
    "budget_exceedance_risk": {
        "display_name": "Budget Exceedance Risk Probability",
        "direction": "minimize",
        "unit": "Probability [0-1]",
        "default_weight": 0.20,
    },
    "relative_mc_error": {
        "display_name": "Monte Carlo Standard Error Relative",
        "direction": "minimize",
        "unit": "Ratio [0-1]",
        "default_weight": 0.0,
    },
}

class MetricRegistry:
    """Provides metric metadata and default properties."""

    @staticmethod
    def get_info(metric_name: str) -> Dict[str, Any]:
        return METRIC_DEFINITIONS.get(
            metric_name,
            {
                "display_name": metric_name,
                "direction": "minimize",
                "unit": "units",
                "default_weight": 0.1,
            },
        )

    @staticmethod
    def get_direction(metric_name: str, fallback: str = "minimize") -> str:
        info = METRIC_DEFINITIONS.get(metric_name)
        return info["direction"] if info else fallback
