# Model development and evaluation

## Prediction task

The supervised task estimates whether a BBL will receive at least one new Class C HPD violation during the 90 days after a monthly observation date. This target is measurable in the source data and narrower than an undefined property-safety score.

The prediction only prioritizes records for follow-up. Rental Radar still shows the public evidence and never recommends whether to sign a lease.

## Models

### Logistic regression baseline

A class-weighted logistic regression provides a simple, interpretable baseline. Standardization occurs inside the training pipeline and the classification threshold is selected on the validation period.

### XGBoost candidate

The nonlinear candidate is an `XGBClassifier` using a binary logistic objective, histogram tree construction, class weighting, depth 4 trees, a 0.05 learning rate, and fixed random seed 42. Gradient-boosted trees suit the count, recency, missingness, seasonality, and borough features without requiring a linear relationship.

The native model is stored in `model_artifacts/xgboost_model.json`; the exact feature order and validation-selected threshold are stored separately.

## Evaluation design

The split is chronological to test performance on later records within the selected BBL cohort:

- Training: January 2024 through January 2025, 1,625 rows.
- Validation: February through May 2025, 500 rows.
- Test: June through October 2025, 625 rows.

The primary ranking metric is precision-recall AUC because the positive class is frequent and uneven across time. Secondary metrics are ROC-AUC, precision, recall, F1, accuracy, Brier score, and recall among the top 10% of model-ranked observations. The decision threshold is chosen on validation data, never on the test period.

## Preliminary results

| Test metric | XGBoost | Logistic regression |
|---|---:|---:|
| PR-AUC | 0.8987 | 0.9163 |
| ROC-AUC | 0.8453 | 0.8568 |
| Accuracy | 0.8208 | 0.7872 |
| Precision | 0.8294 | 0.7731 |
| Recall | 0.9209 | 0.9640 |
| F1 | 0.8727 | 0.8581 |
| Brier score | 0.1465 | 0.1564 |
| Recall at top 10% | 0.1439 | 0.1511 |

XGBoost improved accuracy, precision, F1, and Brier score. Logistic regression produced better PR-AUC, ROC-AUC, recall, and recall at the top 10%. The evidence does not justify declaring XGBoost the final winner. The next experiment should broaden the sampling frame, tune both models, calibrate probabilities on a held-out period, and select the model using the product's review-capacity tradeoff.

The test-period positive rate was 66.72%, which reflects the activity-stratified sample. It is not an estimate of Class C violation prevalence across NYC rentals.

The initial BBL cohort was chosen using activity across the full 2023-2025 collection window. This does not leak future values into any row's features, but it does condition the cohort on later activity. A production evaluation must define the building cohort using information available before the training cutoff.

## Reproduce

```bash
python -m pip install -r requirements-ml.txt

python ml_pipeline.py all \
  --data-dir data/ml \
  --prepared data/prepared/model_dataset.csv \
  --artifacts model_artifacts \
  --start 2023-01-01 \
  --end 2026-01-01 \
  --per-borough 25 \
  --candidate-pool 1000
```

On macOS, the XGBoost wheel also requires the OpenMP runtime, commonly installed with `brew install libomp`.

Run the saved model on a validated feature object:

```bash
python ml_pipeline.py predict \
  --features model_artifacts/example_features.json \
  --artifacts model_artifacts
```
