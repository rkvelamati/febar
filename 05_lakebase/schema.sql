-- Lakebase (Postgres) operational schema. Risk scores are synced from the lakehouse
-- (synced table of ns_wayside.ml.car_risk_scores); the app writes alert actions here.
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.alert_actions (
  action_id    BIGSERIAL PRIMARY KEY,
  car_id       TEXT NOT NULL,
  action       TEXT NOT NULL CHECK (action IN ('acknowledged','dispatch_inspection','dismissed')),
  actor        TEXT NOT NULL,
  note         TEXT,
  outcome      TEXT CHECK (outcome IN ('confirmed_defect','false_alarm')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_actions_car ON ops.alert_actions(car_id, created_at DESC);

-- Live queue = latest score per car joined to its latest action
CREATE OR REPLACE VIEW ops.alert_queue AS
SELECT s.car_id, s.division, s.risk_score, s.explanation,
       a.action AS last_action, a.created_at AS last_action_at
FROM ops.car_risk_scores s
LEFT JOIN LATERAL (
  SELECT action, created_at FROM ops.alert_actions x
  WHERE x.car_id = s.car_id ORDER BY created_at DESC LIMIT 1) a ON true
ORDER BY s.risk_score DESC;
