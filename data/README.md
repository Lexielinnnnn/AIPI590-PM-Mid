# ML data artifacts

`prepared/model_dataset.csv` is the committed, aggregate training table used for the preliminary model run. It contains one row per selected BBL and observation month. It does not contain complaint descriptions, apartment numbers, or free-text fields.

`ml/manifest.json` records the public API queries, collection timestamp, selected BBLs, record counts, duplicate counts, and known sampling limitations.

The raw public records are deliberately excluded from Git with `data/ml/raw/`. Recreate them with:

```bash
python ml_pipeline.py collect \
  --data-dir data/ml \
  --start 2023-01-01 \
  --end 2026-01-01 \
  --per-borough 25 \
  --candidate-pool 1000

python ml_pipeline.py prepare \
  --data-dir data/ml \
  --output data/prepared/model_dataset.csv
```

The collection is a bounded course-project sample, not a citywide census. See `docs/data_collection_and_preparation.md` before interpreting the model results.
