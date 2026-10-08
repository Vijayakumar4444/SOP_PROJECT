# Tamil Nadu Policy Recommendation Engine Scenario Analysis

**Recommendation Scenario ID**: `tn_rec_001_policy_comparison`  
**Generated At**: `2026-10-08T12:24:12.147069+00:00`  
**Total Candidates Evaluated**: `3` (Feasible: `0`)  

## Executive Summary & Recommendation Rationale

- RECOMMENDATION WARNING: Top-scoring Policy Option 'Option B: Clean Cooking Subsidy (Parameter Uncertainty)' (tn_exp_002_param_uncertainty) violates one or more feasibility constraints. Review lower-ranked feasible options.
- KEY METRICS SUMMARY FOR RANK #1: Expected Fiscal Cost = ₹3,556,855.66, Expected Beneficiary Coverage = 152 households/individuals, Budget Exceedance Risk Probability = 0.0%.
- FEASIBILITY EXCLUSION: 'Option A: Elderly Pension Policy (Population Uncertainty)' (tn_exp_001_pop_uncertainty) marked INFEASIBLE due to constraint violations: Mean total cost (₹132,677,735.57) exceeds budget cap (₹60,000,000.00).
- FEASIBILITY EXCLUSION: 'Option B: Clean Cooking Subsidy (Parameter Uncertainty)' (tn_exp_002_param_uncertainty) marked INFEASIBLE due to constraint violations: Beneficiary count (152) is below minimum target coverage (1,500).
- FEASIBILITY EXCLUSION: 'Option C: Youth Skilling Stipend (Combined Uncertainty)' (tn_exp_003_combined_uncertainty) marked INFEASIBLE due to constraint violations: Beneficiary count (1) is below minimum target coverage (1,500).; Monte Carlo standard error (10.40%) exceeds convergence threshold (5.00%).
- PARETO FRONTIER STATUS: The non-dominated Pareto frontier candidates are: Option A: Elderly Pension Policy (Population Uncertainty), Option B: Clean Cooking Subsidy (Parameter Uncertainty), Option C: Youth Skilling Stipend (Combined Uncertainty). These options represent optimal trade-offs where no single metric can be improved without sacrificing another.
- TRADE-OFF INSIGHT: 'Option A: Elderly Pension Policy (Population Uncertainty)' incurs ₹+129,120,879.91 cost difference for +1,682 beneficiary headcount difference compared to 'Option B: Clean Cooking Subsidy (Parameter Uncertainty)' (Marginal ratio: ₹76,743.47 per additional beneficiary).
- STAKEHOLDER SENSITIVITY WARNING: Top policy ranking shifts across different stakeholder weight profiles. Decision-makers should review stakeholder preference weightings.
- DEMOGRAPHIC FAIRNESS ASSESSMENT: Rank #1 Option 'Option B: Clean Cooking Subsidy (Parameter Uncertainty)' achieved an overall fairness score of 0.812 (District Disparity Ratio: 2.20, Gender Disparity Ratio: 1.04).

## Policy Candidate Ranking Results

| Rank | TOPSIS Rank | Feasible | Candidate Display Name | WSM Score | TOPSIS Score | Expected Cost (₹) | Beneficiaries | Risk Prob |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | ❌ NO | Option B: Clean Cooking Subsidy (Parameter Uncertainty) | 0.7103 | 0.5748 | ₹3,556,855.66 | 152 | 0.0% |
| 2 | 2 | ❌ NO | Option C: Youth Skilling Stipend (Combined Uncertainty) | 0.7000 | 0.5602 | ₹5,972.12 | 1 | 0.0% |
| 3 | 3 | ❌ NO | Option A: Elderly Pension Policy (Population Uncertainty) | 0.5000 | 0.4398 | ₹132,677,735.57 | 1,835 | 0.0% |

## Pareto Frontier Dominance Status

| Candidate | Pareto Optimal? | Dominated By | Dominates |
| --- | --- | --- | --- |
| Option A: Elderly Pension Policy (Population Uncertainty) | ⭐ Non-Dominated | None | None |
| Option B: Clean Cooking Subsidy (Parameter Uncertainty) | ⭐ Non-Dominated | None | None |
| Option C: Youth Skilling Stipend (Combined Uncertainty) | ⭐ Non-Dominated | None | None |

## Stakeholder Profile Weight Sensitivity

### Profile: Fiscal Conservative
- **Rank 1**: Option C: Youth Skilling Stipend (Combined Uncertainty) (Infeasible) — Score: 0.8500
- **Rank 2**: Option B: Clean Cooking Subsidy (Parameter Uncertainty) (Infeasible) — Score: 0.8422
- **Rank 3**: Option A: Elderly Pension Policy (Population Uncertainty) (Infeasible) — Score: 0.3000
### Profile: Equity & Coverage Focus
- **Rank 1**: Option A: Elderly Pension Policy (Population Uncertainty) (Infeasible) — Score: 0.7000
- **Rank 2**: Option B: Clean Cooking Subsidy (Parameter Uncertainty) (Infeasible) — Score: 0.4867
- **Rank 3**: Option C: Youth Skilling Stipend (Combined Uncertainty) (Infeasible) — Score: 0.4500
### Profile: Risk Averse Governance
- **Rank 1**: Option B: Clean Cooking Subsidy (Parameter Uncertainty) (Infeasible) — Score: 0.8009
- **Rank 2**: Option C: Youth Skilling Stipend (Combined Uncertainty) (Infeasible) — Score: 0.8000
- **Rank 3**: Option A: Elderly Pension Policy (Population Uncertainty) (Infeasible) — Score: 0.5000
### Profile: Balanced Governance
- **Rank 1**: Option B: Clean Cooking Subsidy (Parameter Uncertainty) (Infeasible) — Score: 0.7103
- **Rank 2**: Option C: Youth Skilling Stipend (Combined Uncertainty) (Infeasible) — Score: 0.7000
- **Rank 3**: Option A: Elderly Pension Policy (Population Uncertainty) (Infeasible) — Score: 0.5000

## Demographic Fairness & District Equity Assessment

| Candidate | District Disparity Ratio | Gender Disparity Ratio | Overall Fairness Score |
| --- | --- | --- | --- |
| Option A: Elderly Pension Policy (Population Uncertainty) | 1.75 | 1.08 | 0.871 |
| Option B: Clean Cooking Subsidy (Parameter Uncertainty) | 2.20 | 1.04 | 0.812 |
| Option C: Youth Skilling Stipend (Combined Uncertainty) | 2.25 | 1.02 | 0.808 |
