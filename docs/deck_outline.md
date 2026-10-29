# Deck outline: Wayside Detector Intelligence for Norfolk Southern (business audience)

1. Outcome first: fewer unplanned stops and wasted set-outs, earlier warning, safer network.
2. The problem today: fixed-threshold detector alerts are late and noisy (synthetic baseline: 940 set-outs, 62% false alarms).
3. What we built: one governed data journey, risk queue for the mechanical desk.
4. Proof: model vs threshold on held-out cars (precision 0.90 vs 0.31, false alarms 4 vs 95; recall 0.56 vs 0.66).
5. Impact in the buyer's KPIs (illustrative, assumptions stated): avoided false set-outs x assumed cost per set-out; earlier lead time.
6. Executive sponsor view: operating ratio, velocity, safety record. Domain owner view: prioritized queue, fewer wasted inspections.
7. Risk and governance: human in the loop, row-level access, audit trail in Lakebase, drift monitoring via write-back labels.
8. Roadmap: pilot one division -> add wheel-impact and dragging-equipment detectors -> integrate with existing systems.
9. Ask: pilot scope, success metrics, timeline.

Be explicit that all figures come from synthetic data and are not Norfolk Southern actuals.
