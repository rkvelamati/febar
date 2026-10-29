# Wayside Detector Intelligence (FE Bar build, Norfolk Southern)

**Customer problem:** Wayside detector alerts (hot bearing, etc.) fire on fixed thresholds, so warnings come late and many
set-outs are false alarms. Result: avoidable unplanned stops, wasted inspections, and lost network velocity.

**Solution:** An integrated Databricks data journey that predicts bearing failures from detector trends, explains each alert
in plain language, answers questions via Genie, and gives the mechanical desk a live alert queue with write-back.

> All data is synthetic (seeded). No Norfolk Southern or customer data is used. Impact figures are illustrative.

## Architecture
Synthetic sources -> **Lakeflow** (bronze/silver/gold) -> **Unity Catalog** governance -> **ML + Gen AI** and **Genie** ->
**Lakebase** (live queue + action write-back) -> **Databricks App** (dispatcher console).

| Stage | Where |
|---|---|
| Synthetic data | `data_generator/generate.py` |
| Lakeflow | `01_ingest_lakeflow/pipeline.py` |
| Unity Catalog | `02_governance_uc/governance.sql` |
| ML and Gen AI | `03_ml_and_genai/train_model.py`, `explain.py` |
| Genie | `04_genie/genie_setup.md` |
| Lakebase | `05_lakebase/schema.sql` |
| App | `06_app/` |
| Deck outline | `docs/deck_outline.md` |

## Run it
```
pip install -r requirements.txt
python data_generator/generate.py          # writes data/*.csv
python 03_ml_and_genai/train_model.py      # trains, compares to threshold, writes data/car_risk_scores.csv
python 03_ml_and_genai/explain.py          # writes data/car_risk_explained.csv
streamlit run 06_app/app.py                # local demo (SQLite fallback); on Databricks it uses Lakebase
```

## Execution evidence (text, committed in `evidence/`)
- `generator_run.log`: data summary and the **threshold baseline** (940 set-outs, 586 false alarms, median 12 days lead).
- `model_run.log`: held-out results, model vs fixed threshold:

| Metric | Fixed threshold | ML model |
|---|---|---|
| Precision | 0.31 | 0.90 |
| Recall | 0.66 | 0.56 |
| False alarms (test set) | 95 | 4 |

The model sharply cuts false alarms and raises precision, at some cost to recall. Next step is tuning the alert cutoff by
cost of a missed defect vs cost of a false set-out.
- `explain_run.log`: sample explanations. Locally they use the template fallback; on Databricks they use a Foundation Model endpoint.

### Still to add from your Databricks workspace (the evaluator needs real run output as text)
- [ ] Lakeflow pipeline run output / event log -> `evidence/lakeflow_run.md`
- [ ] Unity Catalog grants and row-filter verification -> `evidence/uc_verification.md`
- [ ] MLflow run + registered model output -> `evidence/mlflow_run.md`
- [ ] Genie sample questions with SQL and results -> `04_genie/genie_sample_outputs.md`
- [ ] Lakebase synced table + `alert_actions` rows after using the app -> `evidence/lakebase_rows.md`
- [ ] App deployment log and a few UI-driven actions -> `evidence/app_run.md`
