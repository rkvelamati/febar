# Lakeflow Declarative Pipeline (Python). Source CSVs are written by data_generator/generate.py
# and uploaded to /Volumes/<catalog>/raw/landing/. Configure pipeline target catalog = ns_wayside.
import dlt
from pyspark.sql import functions as F, Window

LANDING = "/Volumes/ns_wayside/raw/landing"

@dlt.table(comment="Bronze: raw detector readings (Auto Loader)")
def bronze_readings():
    return (spark.readStream.format("cloudFiles").option("cloudFiles.format", "csv")
            .option("header", True).option("cloudFiles.inferColumnTypes", True)
            .load(f"{LANDING}/detector_readings"))

@dlt.table(comment="Bronze: car master")
def bronze_cars():
    return spark.read.option("header", True).option("inferSchema", True).csv(f"{LANDING}/cars.csv")

@dlt.table(comment="Bronze: detector master")
def bronze_detectors():
    return spark.read.option("header", True).option("inferSchema", True).csv(f"{LANDING}/detectors.csv")

@dlt.table(comment="Bronze: inspections / set-out outcomes")
def bronze_inspections():
    return spark.read.option("header", True).option("inferSchema", True).csv(f"{LANDING}/inspections.csv")

@dlt.table(comment="Silver: cleaned readings joined to car and detector context")
@dlt.expect_or_drop("valid_temp", "temp_above_ambient_f BETWEEN -50 AND 400")
@dlt.expect_or_drop("has_car", "car_id IS NOT NULL")
def silver_readings():
    r = dlt.read_stream("bronze_readings").withColumn("reading_ts", F.to_timestamp("reading_ts"))
    c = dlt.read("bronze_cars").select("car_id", "car_type", "age_years", "division")
    d = dlt.read("bronze_detectors").select("detector_id", "milepost")
    return r.join(c, "car_id").join(d, "detector_id")

@dlt.table(comment="Gold: per-car trend features (7d / 30d) used by the model and the app")
def gold_car_features():
    s = dlt.read("silver_readings")
    max_ts = s.agg(F.max("reading_ts")).first()[0]
    w7 = s.filter(F.col("reading_ts") >= F.lit(max_ts) - F.expr("INTERVAL 7 DAYS"))
    w30 = s.filter(F.col("reading_ts") >= F.lit(max_ts) - F.expr("INTERVAL 30 DAYS"))
    a7 = w7.groupBy("car_id").agg(F.avg("temp_above_ambient_f").alias("avg_temp_7d"),
                                 F.max("temp_above_ambient_f").alias("max_temp_7d"))
    a30 = w30.groupBy("car_id").agg(F.avg("temp_above_ambient_f").alias("avg_temp_30d"))
    base = s.groupBy("car_id", "car_type", "age_years", "division").agg(F.count("*").alias("n_readings"))
    return (base.join(a7, "car_id", "left").join(a30, "car_id", "left")
            .withColumn("trend_delta", F.col("avg_temp_7d") - F.col("avg_temp_30d")))
