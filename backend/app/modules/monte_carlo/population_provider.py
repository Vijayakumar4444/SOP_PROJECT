from __future__ import annotations

from typing import Any
from collections import defaultdict
import random

from backend.app.modules.monte_carlo.simulation_model import PopulationConfig, PopulationMode, SamplingStrategy
from backend.app.modules.synthetic_population.generators.bootstrap import BootstrapBaselineGenerator


class PopulationProvider:
    """Provides population samples for Monte Carlo iterations."""

    def __init__(self, base_records: list[dict[str, Any]]) -> None:
        self.base_records = [dict(r) for r in base_records]
        
        # Pre-group households for household-preserving bootstrap
        self.hh_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in self.base_records:
            hh_id = str(r.get("synthetic_household_id", r.get("household_id", r.get("reference_household_id", "HH1"))))
            self.hh_groups[hh_id].append(r)
        self.hh_id_list = sorted(list(self.hh_groups.keys()))

    def get_population_sample(
        self,
        config: PopulationConfig,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        mode = config.mode

        if mode == PopulationMode.FIXED:
            return [dict(r) for r in self.base_records]

        elif mode == PopulationMode.RESAMPLING:
            return self._resample_population(config, seed)

        elif mode == PopulationMode.REGENERATION:
            return self._regenerate_population(config, seed)

        return [dict(r) for r in self.base_records]

    def _resample_population(self, config: PopulationConfig, seed: int | None) -> list[dict[str, Any]]:
        rng = random.Random(seed)
        target_size = config.population_size or len(self.base_records)
        strat = config.sampling_strategy

        if strat == SamplingStrategy.HOUSEHOLD_BOOTSTRAP and config.preserve_households and self.hh_id_list:
            # Household-level bootstrap resampling
            sampled_records: list[dict[str, Any]] = []
            new_hh_counter = 1

            while len(sampled_records) < target_size:
                chosen_hh = rng.choice(self.hh_id_list)
                hh_members = self.hh_groups[chosen_hh]

                new_hh_id = f"SYN-HH-MC-{new_hh_counter:08d}"
                new_hh_counter += 1

                for idx, member in enumerate(hh_members):
                    m_copy = dict(member)
                    m_copy["synthetic_person_id"] = f"SYN-P-MC-{len(sampled_records)+1:08d}"
                    m_copy["synthetic_household_id"] = new_hh_id
                    m_copy["household_id"] = new_hh_id
                    sampled_records.append(m_copy)

                    if len(sampled_records) >= target_size:
                        break

            return sampled_records[:target_size]

        else:
            # Person-level bootstrap resampling with replacement
            sampled_records = []
            for i in range(target_size):
                chosen = dict(rng.choice(self.base_records))
                chosen["synthetic_person_id"] = f"SYN-P-MC-{i+1:08d}"
                sampled_records.append(chosen)

            return sampled_records

    def _regenerate_population(self, config: PopulationConfig, seed: int | None) -> list[dict[str, Any]]:
        # Calls Phase 3 generator
        gen = BootstrapBaselineGenerator()
        gen.fit(self.base_records, metadata={"generator": "bootstrap"}, config={})
        target_size = config.population_size or len(self.base_records)
        samples = gen.sample(size=target_size, seed=seed)
        
        # Format IDs
        for i, r in enumerate(samples):
            r["synthetic_person_id"] = f"SYN-P-REGEN-{i+1:08d}"
            if "synthetic_household_id" not in r:
                r["synthetic_household_id"] = f"SYN-HH-REGEN-{i+1:08d}"
                r["household_id"] = r["synthetic_household_id"]

        return samples
