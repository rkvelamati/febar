# Databricks notebook source
# MAGIC %md
# MAGIC # Bearing failure risk model
# MAGIC Predicts P(failure within 14 days) per car from detector trend features and compares it
# MAGIC to the fixed 70F-above-ambient threshold rule. Runs locally (pandas) or on Databricks (MLflow logs if available).

# COMMAND ----------
import json, os, sys
import numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

DATA = os.environ.get("DATA_DIR", "data")
HORIZON = 14
SNAPSHOTS = list(range(45, 166, 10))
START = pd.Timestamp("2026-01-01")

cars = pd.read_csv(f"{DATA}/cars.csv")
rd = pd.read_csv(f"{DATA}/detector_readings.csv", parse_dates=["reading_ts"])
rd["day"] = (rd.reading_ts - START).dt.days

# COMMAND ----------
def features_at(T):
    w = rd[rd.day <= T]
    g7 = w[w.day > T - 7].groupby("car_id").temp_above_ambient_f.agg(avg_7d="mean", max_7d="max")
    g30 = w[w.day > T - 30].groupby("car_id").temp_above_ambient_f.agg(avg_30d="mean", max_30d="max")
    w14 = w[w.day > T - 14].groupby("car_id").temp_above_ambient_f.median().rename("median_14d")
    f = g7.join(g30, how="outer").join(w14, how="left")
    f["trend_delta"] = f.avg_7d - f.avg_30d
    w21 = w[w.day > T - 21]
    def slope(g):
        if len(g) < 4 or g.day.nunique() < 3: return 0.0
        return float(np.polyfit(g.day, g.temp_above_ambient_f, 1)[0])
    f = f.merge(w21.groupby("car_id").apply(slope, include_groups=False).rename("slope_21d").reset_index(),
                on="car_id", how="left")
    hi = w21.assign(hi=w21.temp_above_ambient_f > 55).groupby("car_id").hi.sum().rename("n_hi_21d")
    f = f.merge(hi.reset_index(), on="car_id", how="left")
    f = f.reset_index().merge(cars[["car_id", "age_years", "will_fail", "fail_day"]], on="car_id")
    f = f[~(f.will_fail & (f.fail_day <= T))]            # drop cars already failed
    f["label"] = (f.will_fail & (f.fail_day > T) & (f.fail_day <= T + HORIZON)).astype(int)
    f["snapshot_day"] = T
    return f.fillna(f.median(numeric_only=True))

df = pd.concat([features_at(T) for T in SNAPSHOTS], ignore_index=True)
FEATS = ["avg_7d", "max_7d", "avg_30d", "max_30d", "median_14d", "trend_delta", "slope_21d", "n_hi_21d", "age_years"]

# COMMAND ----------
gss = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=42)
tr, te = next(gss.split(df, groups=df.car_id))
train, test = df.iloc[tr], df.iloc[te]

model = GradientBoostingClassifier(random_state=42).fit(train[FEATS], train.label)
p = model.predict_proba(test[FEATS])[:, 1]
pred = (p >= 0.5).astype(int)
base_pred = (test.max_7d > 70).astype(int)

metrics = {
    "train_rows": len(train), "test_rows": len(test), "test_positive_rate": round(float(test.label.mean()), 4),
    "model_auc": round(float(roc_auc_score(test.label, p)), 4),
    "model_precision": round(float(precision_score(test.label, pred, zero_division=0)), 4),
    "model_recall": round(float(recall_score(test.label, pred, zero_division=0)), 4),
    "threshold_precision": round(float(precision_score(test.label, base_pred, zero_division=0)), 4),
    "threshold_recall": round(float(recall_score(test.label, base_pred, zero_division=0)), 4),
    "model_false_alarms": int(((pred == 1) & (test.label == 0)).sum()),
    "threshold_false_alarms": int(((base_pred == 1) & (test.label == 0)).sum()),
}
print(json.dumps(metrics, indent=2))

# COMMAND ----------
# Score the latest snapshot for serving (-> Delta table ns_wayside.ml.car_risk_scores / Lakebase sync)
latest = features_at(max(SNAPSHOTS)).copy()
latest["risk_score"] = model.predict_proba(latest[FEATS])[:, 1].round(4)
latest = latest.merge(cars[["car_id", "division", "car_type"]], on="car_id")
latest.sort_values("risk_score", ascending=False)[
    ["car_id", "division", "car_type", "risk_score", "avg_7d", "max_7d", "trend_delta", "age_years"]
].to_csv(f"{DATA}/car_risk_scores.csv", index=False)
print("top 5 scored cars:\n", latest.nlargest(5, "risk_score")[["car_id", "division", "risk_score", "trend_delta"]])

try:  # MLflow when running on Databricks
    import mlflow, mlflow.sklearn
    with mlflow.start_run(run_name="bearing_risk_gbm"):
        mlflow.log_params({"horizon_days": HORIZON, "model": "GradientBoosting"})
        mlflow.log_metrics({k: v for k, v in metrics.items() if isinstance(v, (int, float))})
        mlflow.sklearn.log_model(model, "model", registered_model_name="ns_wayside.ml.bearing_risk")
except Exception as e:
    print("MLflow logging skipped:", type(e).__name__)
