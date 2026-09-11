# Gaussian Copula

- What it does: Uses empirical marginal distributions with a Gaussian correlation structure.
- Why included: it gives Phase 4 a candidate method to compare against alternatives.
- Strengths: Lightweight statistical candidate for mixed tabular data.
- Weaknesses: Pure-Python fallback; may weaken complex categorical dependencies.
- Expected data types: categorical, continuous, integer, ordinal.
- Important parameters: generator profile, seed, selected variables, constraints version, and model-specific config.
- Known limitations: candidate only; Phase 4 must validate fidelity before downstream policy simulation.
