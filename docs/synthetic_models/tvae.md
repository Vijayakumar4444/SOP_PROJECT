# TVAE

- What it does: Variational autoencoder for tabular synthetic data.
- Why included: it gives Phase 4 a candidate method to compare against alternatives.
- Strengths: Alternative neural generator with different inductive bias from CTGAN.
- Weaknesses: Blocked until optional SDV/pandas training dependencies are available.
- Expected data types: categorical, continuous, integer, ordinal.
- Important parameters: generator profile, seed, selected variables, constraints version, and model-specific config.
- Known limitations: candidate only; Phase 4 must validate fidelity before downstream policy simulation.
