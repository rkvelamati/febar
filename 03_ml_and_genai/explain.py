# Databricks notebook source
# MAGIC %md Generates a grounded, plain-language explanation per high-risk car.
# MAGIC Uses a Databricks Foundation Model endpoint when available; falls back to a deterministic template offline.
# COMMAND ----------
import os, json
import pandas as pd

DATA = os.environ.get("DATA_DIR", "data")
ENDPOINT = os.environ.get("LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")
scores = pd.read_csv(f"{DATA}/car_risk_scores.csv")
top = scores[scores.risk_score >= 0.5].copy()

SYSTEM = ("You advise a railroad mechanical desk. Using ONLY the facts given, write 2 sentences: "
          "what the data shows and one recommended action. Never invent numbers. This is decision support; "
          "a qualified inspector makes the final call.")

def template(r):
    action = "Inspect at the next yard" if r.risk_score < 0.9 else "Prioritize inspection at the next opportunity"
    return (f"Car {r.car_id} ({r.division}) has a 7-day average of {r.avg_7d:.0f}F above ambient "
            f"with a trend of {r.trend_delta:+.1f}F versus its 30-day baseline (risk {r.risk_score:.2f}). {action}.")

def llm(r):
    from databricks.sdk import WorkspaceClient   # only available on Databricks
    w = WorkspaceClient()
    facts = r[["car_id", "division", "car_type", "risk_score", "avg_7d", "max_7d", "trend_delta", "age_years"]].to_dict()
    out = w.serving_endpoints.query(name=ENDPOINT, messages=[
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(facts, default=float)}], max_tokens=150)
    return out.choices[0].message.content

def explain(r):
    try: return llm(r), "llm"
    except Exception: return template(r), "template_fallback"

res = top.apply(lambda r: pd.Series(explain(r), index=["explanation", "source"]), axis=1)
top = pd.concat([top, res], axis=1)
top.to_csv(f"{DATA}/car_risk_explained.csv", index=False)
print(f"explained {len(top)} cars; sources: {top.source.value_counts().to_dict()}")
for _, r in top.head(3).iterrows():
    print("-", r.explanation)
