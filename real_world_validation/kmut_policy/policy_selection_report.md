# Real-World Policy Selection Report: Kalaignar Magalir Urimai Thogai (KMUT)

## 1. Executive Summary
This document presents the candidate evaluation, official source verification, variable compatibility analysis, and selection justification for conducting a historical backtesting and validation experiment on the **SOP Project (Synthetic Population-Based Policy Simulation for Tamil Nadu)**.

Following rigorous research across official Tamil Nadu government portals, policy notes, legislative assembly documents, budget speeches, and departmental reports, **Kalaignar Magalir Urimai Thogai (KMUT)** (Women's Rights Grant Scheme) was selected as the primary policy for real-world validation.

---

## 2. Policy Candidate Evaluation Matrix

| Policy | Eligibility Rules Available | Benefit Defined | Actual Beneficiaries | Actual Expenditure | District Data | Required Variables Available | Source Reliability | Selection Decision |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Kalaignar Magalir Urimai Thogai (KMUT)** | ✅ YES (G.O. Ms No. 34) | ₹1,000/mo | 11.60 Million | ₹13,720 Cr | ✅ YES (38 Dist.) | ✅ YES (`gender`, `age`, `expenditure`, `head`) | Primary (TN Govt Dept) | **SELECTED** |
| **Old Age Pension Scheme (IGNOAPS / State OAP)** | ✅ YES | ₹1,000/mo | 3.58 Million | ₹4,300 Cr | Partial | ✅ YES (`age`, `income`, `employment`) | Primary (Social Welfare) | Candidate |
| **Pudhumai Penn Scheme (Higher Ed Assurance)** | ✅ YES | ₹1,000/mo | 0.48 Million | ₹480 Cr | Partial | ⚠️ Partial (School type proxy) | Primary (Higher Ed Dept) | Candidate |
| **CM Comprehensive Health Insurance (CMCHIS)** | ✅ YES | ₹5L Coverage | 14.00 Million | ₹1,400 Cr | Partial | ❌ Partial (Insurance missing) | Primary (Health Dept) | Rejected |
| **CM Breakfast Scheme (Primary Schools)** | ✅ YES | Free Meal | 1.70 Million | ₹500 Cr | Partial | ⚠️ Partial (School type proxy) | Primary (Edu Dept) | Rejected |

---

## 3. Justification for Selecting KMUT
1. **Targeting Clarity & Rule Definition**: KMUT's eligibility rules are formally codified in Government Order (G.O. Ms. No. 34, Special Programme Implementation Department, dated 10.07.2023). It targets women heads of eligible households.
2. **Data Availability & Ground Truth**: KMUT has comprehensive, official public records on total applications (1.63 Crore), initial approved beneficiaries (1.065 Crore), expanded approvals (1.16 Crore), budget allocation (₹13,720 Crore FY24-25), and district-level distribution across all 38 districts of Tamil Nadu.
3. **High Synthetic Population Compatibility**: All core eligibility variables (`gender` = Female, `age` $\ge 21$, `consumption_expenditure` as proxy for household annual income $\le ₹250,000$, `relationship_to_head` = Head/Spouse) are directly available in our calibrated synthetic microdata.
4. **Targeting Unit**: KMUT targets households via a designated woman head, allowing us to evaluate household-level microdata structure.

---

## 4. Summary of Inspected Official Sources
- **G.O. Ms. No. 34, Special Programme Implementation Dept** (Govt of Tamil Nadu, 10 July 2023)
- **Tamil Nadu Budget Speech 2023-24 & 2024-25** (Finance Minister, Govt of Tamil Nadu)
- **Policy Note 2023-24 & 2024-25**, Special Programme Implementation Department
- **Tamil Nadu Legislative Assembly Answers & Departmental Releases** (2023-2024)
