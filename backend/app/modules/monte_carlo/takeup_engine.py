from __future__ import annotations

from typing import Any
import random

from backend.app.modules.monte_carlo.simulation_model import TakeUpConfig, TakeUpMode


def apply_takeup_uncertainty(
    records: list[dict[str, Any]],
    config: TakeUpConfig,
    seed: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not config.enabled:
        for r in records:
            r["participates_takeup"] = True
        return records, {"takeup_applied": False}

    rng = random.Random(seed)
    
    participating_count = 0
    total_eligible = 0

    group_map = {}
    if config.mode == TakeUpMode.GROUP_SPECIFIC:
        for g in config.groups:
            group_map[(g.field, str(g.value).lower())] = g.probability

    for r in records:
        if not r.get("is_eligible", False):
            r["participates_takeup"] = False
            continue

        total_eligible += 1
        prob = config.probability

        if config.mode == TakeUpMode.GROUP_SPECIFIC:
            prob = config.default_probability
            for (field, val_str), g_prob in group_map.items():
                if field in r and str(r[field]).lower() == val_str:
                    prob = g_prob
                    break

        participates = rng.random() < prob
        r["participates_takeup"] = participates

        if participates:
            participating_count += 1
        else:
            # If eligible person does not participate, mark as unselected
            r["is_selected_beneficiary"] = False
            r["selection_status"] = "OPTED_OUT_TAKEUP"

    stats = {
        "takeup_applied": True,
        "total_eligible": total_eligible,
        "total_participating": participating_count,
        "takeup_rate": round(participating_count / total_eligible, 4) if total_eligible > 0 else 0.0,
    }

    return records, stats
