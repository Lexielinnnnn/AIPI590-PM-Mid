# Rental Radar XGBoost model card

## Intended use

Prioritize which source-linked property reports deserve closer human follow-up. The model estimates whether a selected BBL will receive a new Class C HPD violation within 90 days. It does not certify safety, establish landlord fault, or recommend whether to rent a property.

## Data and split

The training pipeline uses monthly BBL observations derived from NYC 311, HPD violation, and bedbug filing records. Features only use timestamps before the observation date. The train, validation, and test sets are separated chronologically.

Prepared-data SHA-256: `8af00a84c9a1af5b0cf899cf92bd6c5d491944d6249fa41f778d6ef59d39db52`

## Preliminary test results

| Metric | XGBoost | Logistic regression baseline |
|---|---:|---:|
| PR-AUC | 0.8971 | 0.9163 |
| ROC-AUC | 0.8428 | 0.8568 |
| F1 | 0.8695 | 0.8581 |
| Precision | 0.8254 | 0.7731 |
| Recall | 0.9185 | 0.9640 |
| Brier score | 0.1456 | 0.1564 |
| Recall at top 10% | 0.1439 | 0.1511 |

These are preliminary results from an activity-stratified sample of buildings with HPD history. They do not estimate performance for every NYC rental building.

## Highest-importance features

- `borough_staten_island`: 0.1708
- `hpd_class_c_365d`: 0.1351
- `borough_bronx`: 0.0925
- `complaints_30d`: 0.0704
- `borough_queens`: 0.0598
- `complaints_365d`: 0.0490
- `borough_manhattan`: 0.0452
- `hpd_total_365d`: 0.0430

## Known limitations

- The sampling frame starts from buildings with recorded HPD activity and excludes buildings with no HPD violation during collection.
- BBL selection uses HPD activity across the full collection window, including the later evaluation dates, so the split tests temporal prediction within a preselected cohort rather than independent cohort selection.
- Complaint volume reflects reporting access and behavior as well as property conditions.
- BBLs can contain multiple buildings or entrances.
- Bedbug filings are annual and owner reported.
- Records and reporting practices can change over time, so drift monitoring is required.
- The current probability is not calibrated for public display. The product should show source records and neutral follow-up language instead.
