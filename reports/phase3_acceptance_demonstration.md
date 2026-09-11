# Phase 3 Acceptance Demonstration

Phase 3 does not select a best model. Candidate populations must be evaluated in Phase 4 population validation before policy simulation use.

- Reference Template rows: 12000
- Selected Variables: 16
- Target population size per successful model: 12000

- bootstrap: TRAINED population=SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE rows=12000 duration=0.0976 hard_violations=0 reason=None
- ctgan: BLOCKED population=None rows=0 duration=n/a hard_violations=n/a reason=ctgan training is blocked because optional dependencies are missing: sdv, pandas.
- gaussian_copula: TRAINED population=SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-12000-144-ACCEPTANCE rows=12000 duration=0.8295 hard_violations=0 reason=None
- tvae: BLOCKED population=None rows=0 duration=n/a hard_violations=n/a reason=tvae training is blocked because optional dependencies are missing: sdv, pandas.
