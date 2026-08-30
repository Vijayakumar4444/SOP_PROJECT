from __future__ import annotations

from backend.app.modules.synthetic_population.generators.base import UnsupportedGeneratorError
from backend.app.modules.synthetic_population.generators.bootstrap import BootstrapBaselineGenerator
from backend.app.modules.synthetic_population.generators.gaussian_copula import GaussianCopulaGenerator
from backend.app.modules.synthetic_population.generators.neural import CTGANGenerator, TVAEGenerator


GENERATOR_REGISTRY = {
    "bootstrap": BootstrapBaselineGenerator,
    "gaussian_copula": GaussianCopulaGenerator,
    "ctgan": CTGANGenerator,
    "tvae": TVAEGenerator,
}


def get_generator_class(name: str):
    if name not in GENERATOR_REGISTRY:
        raise UnsupportedGeneratorError(f"Unsupported generator: {name}")
    return GENERATOR_REGISTRY[name]
