# Phase 5 Calibration Target Report

## gender

- Target ID: gender_official_marginal
- Status: USABLE_WITH_WARNINGS
- Source file: data/calibration/gender_marginals.csv
- Warning: Synthetic categories not directly targeted: Other.

| Category | Synthetic categories | Target proportion | Official count | Source |
| --- | --- | ---: | ---: | --- |
| Male | Male | 0.500893 | 36137975.0 | SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011 |
| Female | Female | 0.499107 | 36009055.0 | SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011 |

## urban_rural

- Target ID: urban_rural_official_marginal
- Status: USABLE
- Source file: data/calibration/urban_rural_marginals.csv

| Category | Synthetic categories | Target proportion | Official count | Source |
| --- | --- | ---: | ---: | --- |
| Urban | Urban | 0.483976 | 34917440.0 | SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011 |
| Rural | Rural | 0.516024 | 37229590.0 | SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011 |

## social_group

- Target ID: social_group_official_marginal_grouped
- Status: USABLE_WITH_WARNINGS
- Source file: data/calibration/social_group_marginals.csv
- Warning: Non-SC/ST target is an official residual grouping, not an official OBC/Others split.

| Category | Synthetic categories | Target proportion | Official count | Source |
| --- | --- | ---: | ---: | --- |
| Scheduled Caste | Scheduled Caste | 0.200125 | 14438445.0 | SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011 |
| Scheduled Tribe | Scheduled Tribe | 0.011015 | 794697.0 | SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011 |
| Non-SC/ST | Other Backward Class, Others | 0.78886 | 56913888.0 | SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011 |
