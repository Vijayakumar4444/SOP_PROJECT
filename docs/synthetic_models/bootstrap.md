# Weighted Bootstrap

- What it does: Resamples supported reference rows with configured weights and strata.
- Why included: it gives Phase 4 a candidate method to compare against alternatives.
- Strengths: Simple benchmark; preserves observed combinations.
- Weaknesses: Duplicates reference feature rows and is not privacy-preserving.
- Expected data types: categorical, continuous, integer, ordinal.
- Important parameters: generator profile, seed, selected variables, constraints version, and model-specific config.
- Known limitations: candidate only; Phase 4 must validate fidelity before downstream policy simulation.
