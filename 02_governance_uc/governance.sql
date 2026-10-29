-- Unity Catalog governance for Wayside Detector Intelligence
CREATE CATALOG IF NOT EXISTS ns_wayside;
CREATE SCHEMA IF NOT EXISTS ns_wayside.raw;
CREATE SCHEMA IF NOT EXISTS ns_wayside.curated;
CREATE SCHEMA IF NOT EXISTS ns_wayside.ml;
CREATE VOLUME IF NOT EXISTS ns_wayside.raw.landing;

COMMENT ON CATALOG ns_wayside IS 'Synthetic wayside detector data for FE Bar demo; no customer data.';

-- Groups: create in the account console first
GRANT USE CATALOG ON CATALOG ns_wayside TO `mechanical_desk`, `network_ops`, `data_science`;
GRANT SELECT ON SCHEMA ns_wayside.curated TO `mechanical_desk`, `network_ops`;
GRANT ALL PRIVILEGES ON SCHEMA ns_wayside.ml TO `data_science`;

-- Tag operationally sensitive columns
ALTER TABLE ns_wayside.curated.gold_car_features
  ALTER COLUMN division SET TAGS ('domain' = 'operations');

-- Row-level security: a regional mechanical desk sees only its division
CREATE OR REPLACE FUNCTION ns_wayside.curated.division_filter(division STRING)
RETURN is_account_group_member('network_ops') OR is_account_group_member('data_science')
       OR is_account_group_member(CONCAT('desk_', LOWER(division)));

ALTER TABLE ns_wayside.curated.gold_car_features
  SET ROW FILTER ns_wayside.curated.division_filter ON (division);
