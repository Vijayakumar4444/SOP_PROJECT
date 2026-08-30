# Synthetic Data Library Review

- Python runtime used by project scripts: PostgreSQL pgAdmin bundled Python 3.13.12.
- Installed synthetic-data libraries: none detected.
- Checked libraries: SDV, NumPy, pandas, SciPy, scikit-learn.
- Result: none are available in the current environment.
- Dependency action: no package was installed silently.
- Implementation decision: provide a pure-Python Gaussian Copula fallback for Phase 3 development continuity.
- Limitation: the fallback is a project-local candidate generator, not a replacement for a maintained synthetic-data library. A later environment with SDV or equivalent should replace or complement it.
