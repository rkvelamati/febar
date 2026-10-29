"""Dispatcher console (Databricks App, Streamlit).
Reads the ranked queue and writes actions to Lakebase (Postgres). Falls back to local CSV + SQLite
when PGHOST is not set, so it can be demoed without a workspace."""
import os, sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Wayside Detector Intelligence", layout="wide")
DATA = os.environ.get("DATA_DIR", "data")
USE_PG = bool(os.environ.get("PGHOST"))

def pg_conn():
    import psycopg
    return psycopg.connect(host=os.environ["PGHOST"], dbname=os.environ.get("PGDATABASE", "databricks_postgres"),
                           user=os.environ["PGUSER"], password=os.environ.get("PGPASSWORD", ""), sslmode="require")

@st.cache_data(ttl=30)
def load_queue():
    if USE_PG:
        with pg_conn() as c:
            return pd.read_sql("SELECT * FROM ops.alert_queue LIMIT 200", c)
    return pd.read_csv(f"{DATA}/car_risk_explained.csv")[["car_id", "division", "risk_score", "explanation"]]

def record_action(car_id, action, note):
    if USE_PG:
        with pg_conn() as c:
            c.execute("INSERT INTO ops.alert_actions(car_id, action, actor, note) VALUES (%s,%s,%s,%s)",
                      (car_id, action, os.environ.get("USER_EMAIL", "app_user"), note))
    else:
        db = sqlite3.connect(f"{DATA}/actions.db")
        db.execute("CREATE TABLE IF NOT EXISTS alert_actions(car_id, action, note, ts DEFAULT CURRENT_TIMESTAMP)")
        db.execute("INSERT INTO alert_actions(car_id, action, note) VALUES (?,?,?)", (car_id, action, note)); db.commit()

st.title("Wayside Detector Intelligence")
st.caption("Decision support for the mechanical desk. A qualified inspector makes the final call.")
q = load_queue()
div = st.sidebar.multiselect("Division", sorted(q.division.unique()), default=sorted(q.division.unique()))
min_risk = st.sidebar.slider("Minimum risk", 0.0, 1.0, 0.5, 0.05)
view = q[q.division.isin(div) & (q.risk_score >= min_risk)]
c1, c2, c3 = st.columns(3)
c1.metric("Cars flagged", len(view)); c2.metric("Critical (>=0.9)", int((view.risk_score >= 0.9).sum()))
c3.metric("Divisions affected", view.division.nunique())
st.dataframe(view[["car_id", "division", "risk_score"]], use_container_width=True, hide_index=True)

if len(view):
    car = st.selectbox("Select a car", view.car_id)
    row = view[view.car_id == car].iloc[0]
    st.info(row.get("explanation", "No explanation available."))
    note = st.text_input("Note (optional)")
    a, b, d = st.columns(3)
    if a.button("Acknowledge"): record_action(car, "acknowledged", note); st.success("Logged")
    if b.button("Dispatch inspection"): record_action(car, "dispatch_inspection", note); st.success("Dispatched")
    if d.button("Dismiss"): record_action(car, "dismissed", note); st.success("Dismissed")
