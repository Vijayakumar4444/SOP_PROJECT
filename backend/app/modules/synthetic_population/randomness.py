from __future__ import annotations

from typing import Any
import random


def seed_everything(seed: int | None) -> dict[str, Any]:
    """Seed available local randomness sources without requiring optional ML libraries."""
    if seed is None:
        return {"seed": None, "python_random": "not_set", "numpy": "not_set"}
    random.seed(seed)
    seeded = {"seed": seed, "python_random": "set", "numpy": "unavailable"}
    try:
        import numpy  # type: ignore

        numpy.random.seed(seed)
        seeded["numpy"] = "set"
    except Exception:
        seeded["numpy"] = "unavailable"
    return seeded
