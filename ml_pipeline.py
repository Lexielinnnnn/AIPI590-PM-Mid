"""Rental Radar ML pipeline.

Collect a bounded historical sample from NYC Open Data, build leakage-aware
monthly building features, train an XGBoost classifier, and save evaluation
artifacts. The model estimates whether a new Class C HPD violation will be
recorded in the next 90 days. It is a follow-up prioritization aid, not a
safety score or lease recommendation.

Python 3.10+. Training dependencies are listed in requirements-ml.txt.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import pathlib
import platform
import time
import urllib.error
import urllib.parse
import urllib.request


ENDPOINTS = {
    "311": "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
    "hpd": "https://data.cityofnewyork.us/resource/wvxf-dwi5.json",
    "bedbug": "https://data.cityofnewyork.us/resource/wz6d-d3jb.json",
}

BOROUGHS = ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]
RANDOM_SEED = 42
TARGET_NAME = "future_class_c_90d"
NON_FEATURE_COLUMNS = {"bbl", "observation_date", TARGET_NAME}


def save_json(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def get_json(url: str, attempts: int = 4):
    headers = {"User-Agent": "RentalRadar-course-prototype/0.3"}
    if os.getenv("SOCRATA_APP_TOKEN"):
        headers["X-App-Token"] = os.environ["SOCRATA_APP_TOKEN"]
    last_error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Request failed after {attempts} attempts: {url}") from last_error


def socrata_url(endpoint: str, params: dict) -> str:
    return endpoint + "?" + urllib.parse.urlencode(params)


def fetch_pages(endpoint: str, select: str, where: str, order: str, page_size: int = 20000):
    rows, urls = [], []
    offset = 0
    while True:
        params = {
            "$select": select,
            "$where": where,
            "$order": order,
            "$limit": page_size,
            "$offset": offset,
        }
        url = socrata_url(endpoint, params)
        page = get_json(url)
        urls.append(url)
        rows.extend(page)
        if len(page) < page_size:
            return rows, urls
        offset += page_size


def valid_bbl(value) -> bool:
    return isinstance(value, str) and len(value) == 10 and value.isdigit()


def evenly_spaced_sample(rows: list[dict], count: int) -> list[dict]:
    """Select across an activity-ranked candidate list, not only its top."""
    if count <= 0 or not rows:
        return []
    if len(rows) <= count:
        return rows
    if count == 1:
        return [rows[len(rows) // 2]]
    indices = [round(i * (len(rows) - 1) / (count - 1)) for i in range(count)]
    return [rows[index] for index in dict.fromkeys(indices)]


def candidate_bbls(start: str, end: str, per_borough: int, candidate_pool: int):
    selected, provenance = [], []
    for borough in BOROUGHS:
        where = (
            f"inspectiondate >= '{start}T00:00:00' AND inspectiondate < '{end}T00:00:00' "
            f"AND boro='{borough}' AND bbl is not null"
        )
        params = {
            "$select": "bbl,count(*) AS n",
            "$where": where,
            "$group": "bbl",
            "$order": "n DESC,bbl ASC",
            "$limit": candidate_pool,
        }
        url = socrata_url(ENDPOINTS["hpd"], params)
        rows = [row for row in get_json(url) if valid_bbl(row.get("bbl"))]
        sample = evenly_spaced_sample(rows, per_borough)
        selected.extend(row["bbl"] for row in sample)
        provenance.append(
            {
                "borough": borough,
                "candidate_count": len(rows),
                "selected_count": len(sample),
                "query_url": url,
                "selection": "evenly spaced across descending HPD-violation activity rank",
            }
        )
    return sorted(set(selected)), provenance


def chunks(values: list[str], size: int):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def bbl_clause(values: list[str]) -> str:
    return "bbl in (" + ",".join(f"'{value}'" for value in values) + ")"


def deduplicate(rows: list[dict], fields: tuple[str, ...]) -> tuple[list[dict], int]:
    kept = {}
    for row in rows:
        key = "|".join(str(row.get(field, "")) for field in fields)
        kept[key] = row
    return list(kept.values()), len(rows) - len(kept)


def write_jsonl_gz(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_jsonl_gz(path: pathlib.Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def collect(output_dir: pathlib.Path, start: str, end: str, per_borough: int, candidate_pool: int):
    if dt.date.fromisoformat(start) >= dt.date.fromisoformat(end):
        raise ValueError("start must precede end")
    bbls, sample_queries = candidate_bbls(start, end, per_borough, candidate_pool)
    if not bbls:
        raise RuntimeError("No BBLs were selected")

    all_rows = {"311": [], "hpd": [], "bedbug": []}
    query_urls = {"311": [], "hpd": [], "bedbug": []}
    for batch in chunks(bbls, 25):
        clause = bbl_clause(batch)
        queries = {
            "311": {
                "select": "unique_key,created_date,complaint_type,borough,bbl,agency",
                "where": (
                    f"{clause} AND agency='HPD' AND created_date >= '{start}T00:00:00' "
                    f"AND created_date < '{end}T00:00:00'"
                ),
                "order": "created_date ASC,unique_key ASC",
            },
            "hpd": {
                "select": "violationid,inspectiondate,class,boro,bbl",
                "where": (
                    f"{clause} AND inspectiondate >= '{start}T00:00:00' "
                    f"AND inspectiondate < '{end}T00:00:00'"
                ),
                "order": "inspectiondate ASC,violationid ASC",
            },
            "bedbug": {
                "select": (
                    "bbl,building_id,filing_date,filling_period_end_date,of_dwelling_units,"
                    "infested_dwelling_unit_count,eradicated_unit_count,re_infested_dwelling_unit"
                ),
                "where": f"{clause} AND filing_date < '{end}T00:00:00'",
                "order": "filing_date ASC,building_id ASC",
            },
        }
        for name, query in queries.items():
            rows, urls = fetch_pages(ENDPOINTS[name], **query)
            all_rows[name].extend(rows)
            query_urls[name].extend(urls)

    all_rows["311"], dup_311 = deduplicate(all_rows["311"], ("unique_key",))
    all_rows["hpd"], dup_hpd = deduplicate(all_rows["hpd"], ("violationid",))
    all_rows["bedbug"], dup_bedbug = deduplicate(
        all_rows["bedbug"], ("bbl", "building_id", "filling_period_end_date", "filing_date")
    )

    raw_dir = output_dir / "raw"
    for name, rows in all_rows.items():
        write_jsonl_gz(raw_dir / f"{name}.jsonl.gz", rows)

    manifest = {
        "schema_version": 1,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": {"start_inclusive": start, "end_exclusive": end},
        "selected_bbl_count": len(bbls),
        "selected_bbl_sha256": hashlib.sha256("\n".join(bbls).encode()).hexdigest(),
        "selected_bbls": bbls,
        "selection_queries": sample_queries,
        "record_counts": {name: len(rows) for name, rows in all_rows.items()},
        "duplicates_removed": {"311": dup_311, "hpd": dup_hpd, "bedbug": dup_bedbug},
        "query_urls": query_urls,
        "known_biases": [
            "The sample starts from buildings with at least one HPD violation in the collection window.",
            "BBL selection uses activity across the full collection window, including dates later used for model evaluation.",
            "Buildings are sampled across an HPD activity ranking, so results do not estimate citywide prevalence.",
            "311 activity reflects reporting behavior and access, not only underlying conditions.",
            "Bedbug filings are annual and owner reported.",
        ],
    }
    save_json(output_dir / "manifest.json", manifest)
    return manifest


def _imports():
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Install requirements-ml.txt before preparing or training") from exc
    return np, pd


def load_raw(data_dir: pathlib.Path):
    _, pd = _imports()
    frames = {}
    for name in ["311", "hpd", "bedbug"]:
        rows = read_jsonl_gz(data_dir / "raw" / f"{name}.jsonl.gz")
        frames[name] = pd.DataFrame(rows)
    return frames


def safe_numeric(series):
    _, pd = _imports()
    return pd.to_numeric(series, errors="coerce")


def prepare(data_dir: pathlib.Path, prepared_path: pathlib.Path):
    np, pd = _imports()
    manifest = json.loads((data_dir / "manifest.json").read_text())
    frames = load_raw(data_dir)
    complaints, hpd, bedbug = frames["311"], frames["hpd"], frames["bedbug"]

    for frame, date_column in [
        (complaints, "created_date"),
        (hpd, "inspectiondate"),
        (bedbug, "filing_date"),
    ]:
        frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
        frame.dropna(subset=["bbl", date_column], inplace=True)
        frame["bbl"] = frame["bbl"].astype(str)
        frame.drop(frame[~frame["bbl"].str.fullmatch(r"\d{10}")].index, inplace=True)

    complaints.drop_duplicates(subset=["unique_key"], keep="last", inplace=True)
    hpd.drop_duplicates(subset=["violationid"], keep="last", inplace=True)
    bedbug.drop_duplicates(
        subset=["bbl", "building_id", "filling_period_end_date", "filing_date"], keep="last", inplace=True
    )
    hpd["class"] = hpd.get("class", "").fillna("").str.upper()
    bedbug["period_end"] = pd.to_datetime(bedbug.get("filling_period_end_date"), errors="coerce")
    bedbug["dwelling_units"] = safe_numeric(bedbug.get("of_dwelling_units"))
    bedbug["infested_units"] = safe_numeric(bedbug.get("infested_dwelling_unit_count"))

    start = pd.Timestamp(manifest["window"]["start_inclusive"])
    end = pd.Timestamp(manifest["window"]["end_exclusive"])
    first_observation = (start + pd.DateOffset(years=1)).to_period("M").to_timestamp()
    last_observation = (end - pd.Timedelta(days=90)).to_period("M").to_timestamp()
    observation_dates = pd.date_range(first_observation, last_observation, freq="MS")
    rows = []

    bbls = manifest["selected_bbls"]
    for bbl in bbls:
        b311 = complaints[complaints["bbl"] == bbl]
        bhpd = hpd[hpd["bbl"] == bbl]
        bbed = bedbug[bedbug["bbl"] == bbl].sort_values("filing_date")
        borough = None
        if not b311.empty and "borough" in b311:
            borough = b311["borough"].dropna().astype(str).str.upper().mode()
            borough = borough.iloc[0] if not borough.empty else None
        if borough is None and not bhpd.empty and "boro" in bhpd:
            values = bhpd["boro"].dropna().astype(str).str.upper().mode()
            borough = values.iloc[0] if not values.empty else "UNKNOWN"

        for observation in observation_dates:
            past_30 = observation - pd.Timedelta(days=30)
            past_90 = observation - pd.Timedelta(days=90)
            past_365 = observation - pd.Timedelta(days=365)
            future_90 = observation + pd.Timedelta(days=90)

            complaints_30 = b311[(b311["created_date"] >= past_30) & (b311["created_date"] < observation)]
            complaints_90 = b311[(b311["created_date"] >= past_90) & (b311["created_date"] < observation)]
            complaints_365 = b311[(b311["created_date"] >= past_365) & (b311["created_date"] < observation)]
            hpd_90 = bhpd[(bhpd["inspectiondate"] >= past_90) & (bhpd["inspectiondate"] < observation)]
            hpd_365 = bhpd[(bhpd["inspectiondate"] >= past_365) & (bhpd["inspectiondate"] < observation)]
            prior_c = bhpd[(bhpd["class"] == "C") & (bhpd["inspectiondate"] < observation)]
            future_c = bhpd[
                (bhpd["class"] == "C")
                & (bhpd["inspectiondate"] >= observation)
                & (bhpd["inspectiondate"] < future_90)
            ]
            available_bedbug = bbed[bbed["filing_date"] < observation]
            bedbug_rate = None
            if not available_bedbug.empty and available_bedbug["period_end"].notna().any():
                latest_period = available_bedbug["period_end"].max()
                latest_period_rows = (
                    available_bedbug[available_bedbug["period_end"] == latest_period]
                    .sort_values("filing_date")
                    .drop_duplicates(subset=["building_id"], keep="last")
                )
                dwelling_units = latest_period_rows["dwelling_units"].sum(min_count=1)
                infested_units = latest_period_rows["infested_units"].sum(min_count=1)
                if pd.notna(dwelling_units) and dwelling_units > 0 and pd.notna(infested_units):
                    bedbug_rate = float(np.clip(infested_units / dwelling_units, 0, 1))
            days_since_c = 730.0
            if not prior_c.empty:
                days_since_c = min(730.0, float((observation - prior_c["inspectiondate"].max()).days))

            row = {
                "bbl": bbl,
                "observation_date": observation.date().isoformat(),
                "complaints_30d": len(complaints_30),
                "complaints_90d": len(complaints_90),
                "complaints_365d": len(complaints_365),
                "hpd_total_90d": len(hpd_90),
                "hpd_class_a_90d": int((hpd_90["class"] == "A").sum()),
                "hpd_class_b_90d": int((hpd_90["class"] == "B").sum()),
                "hpd_class_c_90d": int((hpd_90["class"] == "C").sum()),
                "hpd_total_365d": len(hpd_365),
                "hpd_class_c_365d": int((hpd_365["class"] == "C").sum()),
                "days_since_class_c": days_since_c,
                "bedbug_infested_rate": bedbug_rate if bedbug_rate is not None else 0.0,
                "bedbug_rate_missing": int(bedbug_rate is None),
                "month": observation.month,
                TARGET_NAME: int(not future_c.empty),
            }
            for value in BOROUGHS:
                row["borough_" + value.lower().replace(" ", "_")] = int(borough == value)
            rows.append(row)

    dataset = pd.DataFrame(rows).sort_values(["observation_date", "bbl"])
    prepared_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(prepared_path, index=False, quoting=csv.QUOTE_MINIMAL)
    dictionary = {
        "observation_unit": "One selected BBL at the first day of a month",
        "target": "1 when at least one Class C HPD violation has an inspection date in [observation date, observation date + 90 days)",
        "leakage_control": "Every feature uses a timestamp strictly before the observation date; status fields are excluded because current status can reflect later events.",
        "missing_data": "Missing bedbug rates are set to 0 with a separate missingness indicator; invalid or zero dwelling-unit denominators are treated as missing.",
        "columns": list(dataset.columns),
        "row_count": len(dataset),
        "positive_count": int(dataset[TARGET_NAME].sum()),
        "positive_rate": float(dataset[TARGET_NAME].mean()),
    }
    save_json(prepared_path.with_suffix(".dictionary.json"), dictionary)
    return dictionary


def recall_at_fraction(y_true, probabilities, fraction: float) -> float:
    np, _ = _imports()
    y = np.asarray(y_true)
    p = np.asarray(probabilities)
    positives = int(y.sum())
    if positives == 0:
        return 0.0
    count = max(1, math.ceil(len(y) * fraction))
    top = np.argsort(-p)[:count]
    return float(y[top].sum() / positives)


def choose_threshold(y_true, probabilities) -> float:
    np, _ = _imports()
    from sklearn.metrics import f1_score

    candidates = np.linspace(0.05, 0.95, 91)
    scores = [(f1_score(y_true, probabilities >= threshold, zero_division=0), threshold) for threshold in candidates]
    return float(max(scores, key=lambda item: (item[0], -item[1]))[1])


def score(y_true, probabilities, threshold: float):
    np, _ = _imports()
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y = np.asarray(y_true)
    p = np.asarray(probabilities)
    predicted = p >= threshold
    matrix = confusion_matrix(y, predicted, labels=[0, 1]).tolist()
    return {
        "rows": int(len(y)),
        "positives": int(y.sum()),
        "prevalence": float(y.mean()),
        "threshold": float(threshold),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)) if len(set(y.tolist())) == 2 else None,
        "accuracy": float(accuracy_score(y, predicted)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "brier": float(brier_score_loss(y, p)),
        "recall_at_top_10_percent": recall_at_fraction(y, p, 0.10),
        "confusion_matrix_tn_fp_fn_tp": matrix,
    }


def calibration_bins(y_true, probabilities, bins: int = 10):
    np, pd = _imports()
    frame = pd.DataFrame({"y": y_true, "p": probabilities})
    frame["bin"] = pd.cut(frame["p"], bins=np.linspace(0, 1, bins + 1), include_lowest=True)
    result = []
    for interval, group in frame.groupby("bin", observed=False):
        if group.empty:
            continue
        result.append(
            {
                "probability_interval": str(interval),
                "rows": int(len(group)),
                "mean_predicted_probability": float(group["p"].mean()),
                "observed_positive_rate": float(group["y"].mean()),
            }
        )
    return result


def purged_splits(data, train_months, validation_months, test_months):
    """Keep every earlier split's full target window before the next split."""
    _, pd = _imports()
    label_end = data["observation_date"] + pd.Timedelta(days=90)
    return {
        "train": data[data["observation_date"].isin(train_months) & (label_end <= min(validation_months))],
        "validation": data[data["observation_date"].isin(validation_months) & (label_end <= min(test_months))],
        "test": data[data["observation_date"].isin(test_months)],
    }


def train(prepared_path: pathlib.Path, artifact_dir: pathlib.Path):
    np, pd = _imports()
    try:
        import sklearn
        import xgboost
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("Install requirements-ml.txt before training") from exc

    data = pd.read_csv(prepared_path)
    data["observation_date"] = pd.to_datetime(data["observation_date"])
    months = sorted(data["observation_date"].unique())
    if len(months) < 10:
        raise ValueError("At least 10 observation months are required")
    train_end = max(1, int(len(months) * 0.60))
    validation_end = max(train_end + 1, int(len(months) * 0.80))
    train_months = months[:train_end]
    validation_months = months[train_end:validation_end]
    test_months = months[validation_end:]
    splits = purged_splits(data, train_months, validation_months, test_months)
    feature_columns = [column for column in data.columns if column not in NON_FEATURE_COLUMNS]
    for name, frame in splits.items():
        if frame.empty or frame[TARGET_NAME].nunique() < 2:
            raise ValueError(f"{name} split must contain both target classes")

    X_train = splits["train"][feature_columns]
    y_train = splits["train"][TARGET_NAME]
    X_validation = splits["validation"][feature_columns]
    y_validation = splits["validation"][TARGET_NAME]
    X_test = splits["test"][feature_columns]
    y_test = splits["test"][TARGET_NAME]
    negative, positive = np.bincount(y_train, minlength=2)
    scale_pos_weight = float(negative / max(positive, 1))

    baseline = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_SEED),
    )
    baseline.fit(X_train, y_train)
    xgb = XGBClassifier(
        objective="binary:logistic",
        eval_metric="aucpr",
        n_estimators=400,
        max_depth=4,
        learning_rate=0.05,
        min_child_weight=4,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        random_state=RANDOM_SEED,
        n_jobs=4,
        tree_method="hist",
    )
    xgb.fit(X_train, y_train, eval_set=[(X_validation, y_validation)], verbose=False)

    probabilities = {
        "baseline_validation": baseline.predict_proba(X_validation)[:, 1],
        "baseline_test": baseline.predict_proba(X_test)[:, 1],
        "xgboost_validation": xgb.predict_proba(X_validation)[:, 1],
        "xgboost_test": xgb.predict_proba(X_test)[:, 1],
    }
    thresholds = {
        "baseline": choose_threshold(y_validation, probabilities["baseline_validation"]),
        "xgboost": choose_threshold(y_validation, probabilities["xgboost_validation"]),
    }
    metrics = {
        "schema_version": 1,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "prepared_data_sha256": hashlib.sha256(prepared_path.read_bytes()).hexdigest(),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
        },
        "target": TARGET_NAME,
        "target_definition": "New Class C HPD violation recorded in the next 90 days",
        "random_seed": RANDOM_SEED,
        "label_horizon_days": 90,
        "split_policy": "Purge rows whose 90-day labels cross the next split. Full-window cohort selection bias remains.",
        "feature_columns": feature_columns,
        "split": {
            name: {
                "rows": len(frame),
                "start": frame["observation_date"].min().date().isoformat(),
                "end": frame["observation_date"].max().date().isoformat(),
            }
            for name, frame in splits.items()
        },
        "models": {
            "logistic_regression": {
                "validation": score(y_validation, probabilities["baseline_validation"], thresholds["baseline"]),
                "test": score(y_test, probabilities["baseline_test"], thresholds["baseline"]),
            },
            "xgboost": {
                "validation": score(y_validation, probabilities["xgboost_validation"], thresholds["xgboost"]),
                "test": score(y_test, probabilities["xgboost_test"], thresholds["xgboost"]),
            },
        },
        "calibration_bins_xgboost_test": calibration_bins(y_test, probabilities["xgboost_test"]),
        "model_selection_status": "open; XGBoost and logistic regression lead on different test metrics",
        "interpretation": "Preliminary results on an activity-stratified HPD sample; not a citywide performance estimate.",
    }

    artifact_dir.mkdir(parents=True, exist_ok=True)
    xgb.save_model(artifact_dir / "xgboost_model.json")
    save_json(artifact_dir / "metrics.json", metrics)
    save_json(
        artifact_dir / "feature_schema.json",
        {
            "feature_columns": feature_columns,
            "target": TARGET_NAME,
            "target_horizon_days": 90,
            "threshold": thresholds["xgboost"],
            "boundary": "Follow-up prioritization only; not a safety score or lease recommendation.",
        },
    )

    importance = pd.DataFrame(
        {"feature": feature_columns, "importance": xgb.feature_importances_.astype(float)}
    ).sort_values("importance", ascending=False)
    importance.to_csv(artifact_dir / "feature_importance.csv", index=False)
    predictions = splits["test"][["bbl", "observation_date", TARGET_NAME]].copy()
    predictions["xgboost_probability"] = probabilities["xgboost_test"]
    predictions["xgboost_prediction"] = (predictions["xgboost_probability"] >= thresholds["xgboost"]).astype(int)
    predictions.to_csv(artifact_dir / "test_predictions.csv", index=False)
    write_model_card(artifact_dir / "MODEL_CARD.md", metrics, importance)
    return metrics


def predict(feature_path: pathlib.Path, artifact_dir: pathlib.Path):
    """Score one precomputed feature object with the saved native model."""
    _, pd = _imports()
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("Install requirements-ml.txt before prediction") from exc

    schema = json.loads((artifact_dir / "feature_schema.json").read_text())
    supplied = json.loads(feature_path.read_text())
    missing = [name for name in schema["feature_columns"] if name not in supplied]
    extra = sorted(set(supplied) - set(schema["feature_columns"]))
    if missing:
        raise ValueError("Missing model features: " + ", ".join(missing))
    if extra:
        raise ValueError("Unknown model features: " + ", ".join(extra))
    values = {}
    for name in schema["feature_columns"]:
        try:
            values[name] = float(supplied[name])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Feature {name} must be numeric") from exc
    frame = pd.DataFrame([values], columns=schema["feature_columns"])
    model = XGBClassifier()
    model.load_model(artifact_dir / "xgboost_model.json")
    probability = float(model.predict_proba(frame)[0, 1])
    return {
        "probability_of_new_class_c_violation_within_90_days": probability,
        "validation_selected_threshold": schema["threshold"],
        "priority_follow_up": probability >= schema["threshold"],
        "boundary": schema["boundary"],
    }


def write_model_card(path: pathlib.Path, metrics: dict, importance) -> None:
    test = metrics["models"]["xgboost"]["test"]
    baseline = metrics["models"]["logistic_regression"]["test"]
    top_features = "\n".join(
        f"- `{row.feature}`: {row.importance:.4f}" for row in importance.head(8).itertuples()
    )
    text = f"""# Rental Radar XGBoost model card

## Intended use

Prioritize which source-linked property reports deserve closer human follow-up. The model estimates whether a selected BBL will receive a new Class C HPD violation within 90 days. It does not certify safety, establish landlord fault, or recommend whether to rent a property.

## Data and split

The training pipeline uses monthly BBL observations derived from NYC 311, HPD violation, and bedbug filing records. Features only use timestamps before the observation date. The train, validation, and test sets are separated chronologically.

Prepared-data SHA-256: `{metrics['prepared_data_sha256']}`

## Preliminary test results

| Metric | XGBoost | Logistic regression baseline |
|---|---:|---:|
| PR-AUC | {test['pr_auc']:.4f} | {baseline['pr_auc']:.4f} |
| ROC-AUC | {test['roc_auc']:.4f} | {baseline['roc_auc']:.4f} |
| F1 | {test['f1']:.4f} | {baseline['f1']:.4f} |
| Precision | {test['precision']:.4f} | {baseline['precision']:.4f} |
| Recall | {test['recall']:.4f} | {baseline['recall']:.4f} |
| Brier score | {test['brier']:.4f} | {baseline['brier']:.4f} |
| Recall at top 10% | {test['recall_at_top_10_percent']:.4f} | {baseline['recall_at_top_10_percent']:.4f} |

These are preliminary results from an activity-stratified sample of buildings with HPD history. They do not estimate performance for every NYC rental building.

## Highest-importance features

{top_features}

## Known limitations

- The sampling frame starts from buildings with recorded HPD activity and excludes buildings with no HPD violation during collection.
- BBL selection uses HPD activity across the full collection window, including the later evaluation dates, so the split tests temporal prediction within a preselected cohort rather than independent cohort selection.
- Complaint volume reflects reporting access and behavior as well as property conditions.
- BBLs can contain multiple buildings or entrances.
- Bedbug filings are annual and owner reported.
- Records and reporting practices can change over time, so drift monitoring is required.
- The current probability is not calibrated for public display. The product should show source records and neutral follow-up language instead.
"""
    path.write_text(text + "\nEvaluation update: a 90-day target-window purge removes overlapping labels across train/validation/test boundaries. Cohort selection still uses full-window activity; this remains a preliminary within-cohort evaluation.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--data-dir", default="data/ml")
    collect_parser.add_argument("--start", default="2023-01-01")
    collect_parser.add_argument("--end", default="2026-01-01")
    collect_parser.add_argument("--per-borough", type=int, default=25)
    collect_parser.add_argument("--candidate-pool", type=int, default=100)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--data-dir", default="data/ml")
    prepare_parser.add_argument("--output", default="data/prepared/model_dataset.csv")

    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--data", default="data/prepared/model_dataset.csv")
    train_parser.add_argument("--artifacts", default="model_artifacts")

    predict_parser = subparsers.add_parser("predict")
    predict_parser.add_argument("--features", required=True)
    predict_parser.add_argument("--artifacts", default="model_artifacts")

    all_parser = subparsers.add_parser("all")
    all_parser.add_argument("--data-dir", default="data/ml")
    all_parser.add_argument("--prepared", default="data/prepared/model_dataset.csv")
    all_parser.add_argument("--artifacts", default="model_artifacts")
    all_parser.add_argument("--start", default="2023-01-01")
    all_parser.add_argument("--end", default="2026-01-01")
    all_parser.add_argument("--per-borough", type=int, default=25)
    all_parser.add_argument("--candidate-pool", type=int, default=100)

    args = parser.parse_args()
    if args.command == "collect":
        result = collect(pathlib.Path(args.data_dir), args.start, args.end, args.per_borough, args.candidate_pool)
    elif args.command == "prepare":
        result = prepare(pathlib.Path(args.data_dir), pathlib.Path(args.output))
    elif args.command == "train":
        result = train(pathlib.Path(args.data), pathlib.Path(args.artifacts))
    elif args.command == "predict":
        result = predict(pathlib.Path(args.features), pathlib.Path(args.artifacts))
    else:
        data_dir = pathlib.Path(args.data_dir)
        collect(data_dir, args.start, args.end, args.per_borough, args.candidate_pool)
        prepare(data_dir, pathlib.Path(args.prepared))
        result = train(pathlib.Path(args.prepared), pathlib.Path(args.artifacts))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
