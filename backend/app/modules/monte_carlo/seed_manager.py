from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass
class IterationSeedBundle:
    iteration_number: int
    base_seed: int
    iteration_seed: int
    population_seed: int
    calibration_seed: int
    parameter_seed: int
    take_up_seed: int
    policy_seed: int


class SeedManager:
    """Hierarchical seed generator for reproducible Monte Carlo simulation."""

    def __init__(self, base_seed: int = 20260913) -> None:
        self.base_seed = base_seed

    def get_iteration_seed_bundle(self, iteration_number: int) -> IterationSeedBundle:
        # Stable integer derivation without platform-dependent hash()
        iter_seed = self._derive_seed(self.base_seed, f"ITER_{iteration_number}")
        pop_seed = self._derive_seed(iter_seed, "POPULATION")
        calib_seed = self._derive_seed(iter_seed, "CALIBRATION")
        param_seed = self._derive_seed(iter_seed, "PARAMETER")
        takeup_seed = self._derive_seed(iter_seed, "TAKEUP")
        policy_seed = self._derive_seed(iter_seed, "POLICY")

        return IterationSeedBundle(
            iteration_number=iteration_number,
            base_seed=self.base_seed,
            iteration_seed=iter_seed,
            population_seed=pop_seed,
            calibration_seed=calib_seed,
            parameter_seed=param_seed,
            take_up_seed=takeup_seed,
            policy_seed=policy_seed,
        )

    def _derive_seed(self, parent_seed: int, label: str) -> int:
        raw_str = f"{parent_seed}:{label}"
        digest = hashlib.sha256(raw_str.encode("utf-8")).digest()
        # Convert first 4 bytes to integer
        int_val = int.from_bytes(digest[:4], byteorder="big", signed=False)
        return int_val % (2**31 - 1)
