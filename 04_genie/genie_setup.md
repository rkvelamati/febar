# Genie space: Wayside Detector Intelligence

Create in the workspace: Genie > New > data sources:
`ns_wayside.curated.gold_car_features`, `ns_wayside.ml.car_risk_scores`, `ns_wayside.curated.silver_readings`, `ns_wayside.curated.bronze_inspections`.

## General instructions (paste into the space)
- "Risk" means `risk_score` (probability a car fails within 14 days). Critical = `risk_score >= 0.9`.
- "False alarm" means an inspection row with `outcome = 'false_alarm'`.
- Temperatures are degrees F above ambient. Divisions: Pittsburgh, Harrisburg, Atlanta, Chicago, Alabama.

## Sample questions to commit with outputs
1. Which cars in the Pittsburgh division have risk above 0.8?
2. How many threshold set-outs were false alarms, by division?
3. Show cars whose 7-day average temperature rose more than 10F versus their 30-day baseline.
4. What share of set-outs were confirmed defects?
5. Which detectors recorded the most readings above 70F?

After running each in the Genie space, paste the generated SQL and result tables into `04_genie/genie_sample_outputs.md`
(text, not screenshots).
