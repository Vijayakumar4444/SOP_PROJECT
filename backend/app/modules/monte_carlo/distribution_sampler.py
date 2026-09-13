from __future__ import annotations

from typing import Any
import math
import random

from backend.app.modules.monte_carlo.simulation_model import DistributionType, ParameterUncertaintyConfig


class DistributionSampler:
    """Centralized parameter sampler using instance-scoped random streams."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def sample_parameter(self, config: ParameterUncertaintyConfig) -> Any:
        dist = config.distribution

        if dist == DistributionType.FIXED:
            return config.minimum if config.minimum is not None else config.mean

        elif dist == DistributionType.UNIFORM:
            low = config.minimum if config.minimum is not None else 0.0
            high = config.maximum if config.maximum is not None else 1.0
            return round(self.rng.uniform(low, high), 4)

        elif dist == DistributionType.DISCRETE_UNIFORM:
            low = config.minimum if config.minimum is not None else 0.0
            high = config.maximum if config.maximum is not None else 100.0
            step = config.step if config.step is not None and config.step > 0 else 1.0
            steps_cnt = int((high - low) // step)
            chosen_step = self.rng.randint(0, max(0, steps_cnt))
            val = low + chosen_step * step
            return int(val) if step.is_integer() and low.is_integer() else round(val, 4)

        elif dist == DistributionType.TRIANGULAR:
            low = config.minimum if config.minimum is not None else 0.0
            high = config.maximum if config.maximum is not None else 1.0
            mode = config.mode if config.mode is not None else (low + high) / 2.0
            return round(self.rng.triangular(low, high, mode), 4)

        elif dist == DistributionType.NORMAL:
            mu = config.mean if config.mean is not None else 0.0
            sigma = config.std_dev if config.std_dev is not None else 1.0
            return round(self.rng.gauss(mu, sigma), 4)

        elif dist == DistributionType.TRUNCATED_NORMAL:
            mu = config.mean if config.mean is not None else 0.0
            sigma = config.std_dev if config.std_dev is not None else 1.0
            low = config.minimum if config.minimum is not None else float("-inf")
            high = config.maximum if config.maximum is not None else float("inf")
            
            for _ in range(100):
                val = self.rng.gauss(mu, sigma)
                if low <= val <= high:
                    return round(val, 4)
            return round(max(low, min(high, mu)), 4)

        elif dist == DistributionType.LOGNORMAL:
            mu = config.mean if config.mean is not None else 0.0
            sigma = config.std_dev if config.std_dev is not None else 1.0
            return round(self.rng.lognormvariate(mu, sigma), 4)

        elif dist == DistributionType.BETA:
            a = config.alpha if config.alpha is not None else 2.0
            b = config.beta if config.beta is not None else 2.0
            return round(self.rng.betavariate(a, b), 4)

        elif dist == DistributionType.BERNOULLI:
            p = config.probability if config.probability is not None else 0.5
            return self.rng.random() < p

        elif dist == DistributionType.CATEGORICAL:
            cats = config.categories or [True, False]
            weights = config.weights if config.weights and len(config.weights) == len(cats) else None
            if weights:
                return self.rng.choices(cats, weights=weights, k=1)[0]
            return self.rng.choice(cats)

        return config.minimum
