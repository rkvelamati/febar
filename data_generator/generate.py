"""Seeded synthetic data generator for Wayside Detector Intelligence.

All data is synthetic. No customer data is used.
Outputs CSVs: cars, detectors, detector_readings, inspections.
Degrading bearings show a slow upward temperature trend before failing;
healthy cars show noise only, so a trend-aware model beats a fixed threshold.
"""
import argparse, json, os
import numpy as np
import pandas as pd

DIVISIONS = ["Pittsburgh", "Harrisburg", "Atlanta", "Chicago", "Alabama"]
CAR_TYPES = ["Hopper", "Boxcar", "Tank", "Intermodal", "Gondola"]


def build(n_cars, days, seed, out):
    rng = np.random.default_rng(seed)
    os.makedirs(out, exist_ok=True)

    cars = pd.DataFrame({
        "car_id": [f"NS{100000+i}" for i in range(n_cars)],
        "car_type": rng.choice(CAR_TYPES, n_cars),
        "age_years": rng.integers(1, 40, n_cars),
        "division": rng.choice(DIVISIONS, n_cars),
    })
    detectors = pd.DataFrame({
        "detector_id": [f"HBD{i:03d}" for i in range(40)],
        "division": rng.choice(DIVISIONS, 40),
        "milepost": rng.uniform(0, 400, 40).round(1),
    })

    # ~6% of cars have a degrading bearing that fails at a random day
    degrading = rng.random(n_cars) < 0.06
    fail_day = np.where(degrading, rng.integers(days // 2, days, n_cars), -1)
    cars["will_fail"] = degrading
    cars["fail_day"] = fail_day

    start = pd.Timestamp("2026-01-01")
    rows = []
    for idx, car in cars.iterrows():
        n_reads = rng.integers(30, 50)
        read_days = np.sort(rng.integers(0, days, n_reads))
        for d in read_days:
            ambient = 10 + 15 * np.sin(2 * np.pi * d / 365) + rng.normal(0, 3)
            temp_above_ambient = 40 + rng.normal(0, 8) + 0.3 * car.age_years / 10
            if rng.random() < 0.012:
                temp_above_ambient += rng.uniform(25, 40)  # transient spike (sensor/dragging brake)
            if car.will_fail and d < car.fail_day:
                ramp_start = car.fail_day - 25
                if d > ramp_start:
                    temp_above_ambient += (d - ramp_start) * rng.uniform(2.0, 3.5)
            rows.append((car.car_id, rng.choice(detectors.detector_id),
                         (start + pd.Timedelta(days=int(d))).isoformat(),
                         round(float(temp_above_ambient), 1), round(float(ambient), 1)))
    readings = pd.DataFrame(rows, columns=[
        "car_id", "detector_id", "reading_ts", "temp_above_ambient_f", "ambient_f"])

    # Inspections/set-outs: fixed 170F rule triggers set-outs; some are false alarms
    hot = readings[readings.temp_above_ambient_f > 70].copy()
    hot = hot.merge(cars[["car_id", "will_fail"]], on="car_id")
    hot["outcome"] = np.where(hot.will_fail, "confirmed_defect", "false_alarm")
    hot["action"] = "set_out"
    inspections = hot[["car_id", "detector_id", "reading_ts", "action", "outcome"]]

    cars.to_csv(f"{out}/cars.csv", index=False)
    detectors.to_csv(f"{out}/detectors.csv", index=False)
    readings.to_csv(f"{out}/detector_readings.csv", index=False)
    inspections.to_csv(f"{out}/inspections.csv", index=False)

    fr = readings.merge(cars[["car_id", "will_fail", "fail_day"]], on="car_id")
    fr = fr[fr.will_fail & (fr.temp_above_ambient_f > 70)]
    fr["day"] = (pd.to_datetime(fr.reading_ts) - start).dt.days
    first_cross = fr.groupby("car_id").day.min()
    lead = (cars.set_index("car_id").fail_day.loc[first_cross.index] - first_cross)
    summary = {
        "threshold_median_lead_days_before_failure": float(lead.median()),
        "seed": seed, "cars": n_cars, "days": days,
        "readings": len(readings), "degrading_cars": int(degrading.sum()),
        "threshold_set_outs": len(inspections),
        "threshold_false_alarms": int((inspections.outcome == "false_alarm").sum()),
        "threshold_confirmed": int((inspections.outcome == "confirmed_defect").sum()),
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cars", type=int, default=2000)
    p.add_argument("--days", type=int, default=180)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="data")
    a = p.parse_args()
    build(a.cars, a.days, a.seed, a.out)
