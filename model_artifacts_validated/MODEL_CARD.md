# Rental Radar XGBoost model card

## Intended use

Prioritize which source-linked property reports deserve closer human follow-up. The model estimates whether a selected BBL will receive a new Class C HPD violation within 90 days. It does not certify safety, establish landlord fault, or recommend whether to rent a property.

## Data and split

The training pipeline uses monthly BBL observations derived from NYC 311, HPD violation, and bedbug filing records. Features only use timestamps before the observation date. The train, validation, and test sets are separated chronologically.

Prepared-data SHA-256: `924e47daea25fcecbeb06fa155a36a2e2c156bb1cc8169386247542669dff4a4`

## Preliminary test results

| Metric | XGBoost | Logistic regression baseline |
|---|---:|---:|
| PR-AUC | 0.8988 | 0.9175 |
| ROC-AUC | 0.8453 | 0.8595 |
| F1 | 0.8555 | 0.8581 |
| Precision | 0.8322 | 0.7685 |
| Recall | 0.8801 | 0.9712 |
| Brier score | 0.1485 | 0.1522 |
| Recall at top 10% | 0.1439 | 0.1511 |

These are preliminary results from an activity-stratified sample of buildings with HPD history. They do not estimate performance for every NYC rental building.

## Highest-importance features

- `borough_staten_island`: 0.1309
- `hpd_class_c_365d`: 0.1298
- `hpd_total_365d`: 0.0998
- `borough_bronx`: 0.0701
- `borough_queens`: 0.0663
- `complaints_30d`: 0.0655
- `borough_manhattan`: 0.0422
- `bedbug_infested_rate`: 0.0395

## Known limitations

- The sampling frame starts from buildings with recorded HPD activity and excludes buildings with no HPD violation during collection.
- BBL selection uses HPD activity across the full collection window, including the later evaluation dates, so the split tests temporal prediction within a preselected cohort rather than independent cohort selection.
- Complaint volume reflects reporting access and behavior as well as property conditions.
- BBLs can contain multiple buildings or entrances.
- Bedbug filings are annual and owner reported.
- Records and reporting practices can change over time, so drift monitoring is required.
- The current probability is not calibrated for public display. The product should show source records and neutral follow-up language instead.

Evaluation update: a 90-day target-window purge removes overlapping labels across train/validation/test boundaries. Cohort selection still uses full-window activity; this remains a preliminary within-cohort evaluation.
