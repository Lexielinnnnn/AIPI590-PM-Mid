# Data collection and preparation

## Sources and collection

The ML pipeline uses three NYC Open Data datasets:

1. 311 Service Requests from 2020 to Present for HPD complaint activity.
2. HPD Housing Maintenance Code Violations for dated A, B, and C violations.
3. HPD Bedbug Reporting for annual owner-reported infestation data.

`ml_pipeline.py collect` first queries HPD violation counts by BBL and borough. For the preliminary run it considered the 1,000 most active BBLs in each borough and selected 25 evenly spaced across each activity ranking. This produced 125 BBLs covering all five boroughs. It then retrieved the minimum fields needed from each source for January 1, 2023 through January 1, 2026.

The saved manifest records every query URL. The October 14, 2026 run retrieved 32,342 HPD-related 311 complaints, 45,278 HPD violations, and 1,253 bedbug filing rows before monthly aggregation.

## Cleaning

The preparation step:

- rejects missing or malformed 10-digit BBLs;
- parses source timestamps and removes rows with invalid dates;
- deduplicates 311 records by `unique_key` and HPD violations by `violationid`;
- keeps bedbug submissions distinct by BBL, building, reporting period, and filing date;
- converts dwelling-unit and infestation fields to numeric values;
- treats zero or invalid dwelling-unit denominators as missing;
- caps reported infestation rates to the valid interval from 0 to 1;
- excludes mutable current-status fields from predictive features.

The committed training table has 2,750 monthly BBL observations. Each feature uses a timestamp strictly before the observation date. The target equals 1 when a new Class C HPD violation has an inspection date in the following 90 days.

## Features

The current features include 311 complaint counts over 30, 90, and 365 days; HPD violation counts by class over 90 and 365 days; days since the most recent Class C violation; the latest available bedbug infestation rate; a bedbug missingness indicator; month; and borough indicators.

## Missing data and bias

- Bedbug data are annual and owner reported. Missing rates become 0 only alongside an explicit missingness indicator.
- 311 volume reflects reporting behavior, language access, tenant knowledge, and service access as well as building conditions.
- The sampling frame requires recorded HPD activity. It excludes buildings without an HPD violation in the collection window.
- BBL selection uses HPD activity across the full collection window, including the later evaluation dates. The time split therefore measures prediction within a preselected cohort, not an independently selected future cohort.
- Selecting across an HPD activity ranking improves variation but does not produce a representative citywide sample.
- A BBL may contain several buildings or entrances. The model predicts at the tax-lot level until BIN-level identity is implemented.
- Source records can be revised. The manifest timestamps the extraction and the model card requires drift monitoring.

These limitations prevent the preliminary metrics from being interpreted as citywide performance or a property-safety estimate.
