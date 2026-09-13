# TVAE

- What it does: Uses SDV TVAESynthesizer on the Phase 3 selected person-level variables.
- Why included: it gives Phase 4 a candidate method to compare against alternatives.
- Strengths: Variational neural candidate with a different inductive bias from CTGAN.
- Weaknesses: Stochastic training; quality and policy suitability remain Phase 4 responsibilities.
- Expected data types: categorical, continuous, integer, ordinal.
- Important parameters: generator profile, seed, selected variables, constraints version, and model-specific config.
- Known limitations: candidate only; Phase 4 must validate fidelity before downstream policy simulation.
