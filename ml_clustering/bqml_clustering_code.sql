-- k = 3
CREATE OR REPLACE MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k3`
OPTIONS(
  model_type = 'KMEANS',
  num_clusters = 3,
  distance_type = 'EUCLIDEAN',
  standardize_features = TRUE
) AS
SELECT
  trip_count,
  avg_total_amount,
  avg_fare_amount,
  avg_tip_amount,
  avg_duration_minutes,
  avg_distance,
  pct_rush_hour,
  pct_night,
  pct_weekend,
  pct_adverse_weather

FROM `bq-sandbox-ariana.nyc_taxi_ml.mart_zone_clustering`;

-- k = 4
CREATE OR REPLACE MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k4`
OPTIONS(
  model_type = 'KMEANS',
  num_clusters = 4,
  distance_type = 'EUCLIDEAN',
  standardize_features = TRUE
) AS
SELECT
  trip_count,
  avg_total_amount,
  avg_fare_amount,
  avg_tip_amount,
  avg_duration_minutes,
  avg_distance,
  pct_rush_hour,
  pct_night,
  pct_weekend,
  pct_adverse_weather

FROM `bq-sandbox-ariana.nyc_taxi_ml.mart_zone_clustering`;

-- k = 5
CREATE OR REPLACE MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k5`
OPTIONS(
  model_type = 'KMEANS',
  num_clusters = 5,
  distance_type = 'EUCLIDEAN',
  standardize_features = TRUE
) AS
SELECT
  trip_count,
  avg_total_amount,
  avg_fare_amount,
  avg_tip_amount,
  avg_duration_minutes,
  avg_distance,
  pct_rush_hour,
  pct_night,
  pct_weekend,
  pct_adverse_weather

FROM `bq-sandbox-ariana.nyc_taxi_ml.mart_zone_clustering`;

-- k = 6
CREATE OR REPLACE MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k6`
OPTIONS(
  model_type = 'KMEANS',
  num_clusters = 6,
  distance_type = 'EUCLIDEAN',
  standardize_features = TRUE
) AS
SELECT
  trip_count,
  avg_total_amount,
  avg_fare_amount,
  avg_tip_amount,
  avg_duration_minutes,
  avg_distance,
  pct_rush_hour,
  pct_night,
  pct_weekend,
  pct_adverse_weather

FROM `bq-sandbox-ariana.nyc_taxi_ml.mart_zone_clustering`;


--checking data quality
SELECT 'k=3' AS model, davies_bouldin_index FROM ML.EVALUATE(MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k3`)
UNION ALL
SELECT 'k=4', davies_bouldin_index FROM ML.EVALUATE(MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k4`)
UNION ALL
SELECT 'k=5', davies_bouldin_index FROM ML.EVALUATE(MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k5`)
UNION ALL
SELECT 'k=6', davies_bouldin_index FROM ML.EVALUATE(MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k6`);

--checking cluster info, k=4
SELECT
  feature,
  ROUND(MAX(IF(centroid_id = 1, numerical_value, NULL)), 1) AS cluster_1,
  ROUND(MAX(IF(centroid_id = 2, numerical_value, NULL)), 1) AS cluster_2,
  ROUND(MAX(IF(centroid_id = 3, numerical_value, NULL)), 1) AS cluster_3,
  ROUND(MAX(IF(centroid_id = 4, numerical_value, NULL)), 1) AS cluster_4
FROM ML.CENTROIDS(MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k4`)
GROUP BY feature
ORDER BY feature

--checking cluster info, k=6
SELECT
  feature,
  ROUND(MAX(IF(centroid_id = 1, numerical_value, NULL)), 1) AS cluster_1,
  ROUND(MAX(IF(centroid_id = 2, numerical_value, NULL)), 1) AS cluster_2,
  ROUND(MAX(IF(centroid_id = 3, numerical_value, NULL)), 1) AS cluster_3,
  ROUND(MAX(IF(centroid_id = 4, numerical_value, NULL)), 1) AS cluster_4,
  ROUND(MAX(IF(centroid_id = 5, numerical_value, NULL)), 1) AS cluster_5,
  ROUND(MAX(IF(centroid_id = 6, numerical_value, NULL)), 1) AS cluster_6
FROM ML.CENTROIDS(MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k6`)
GROUP BY feature
ORDER BY feature;

--running ml.predict on k=4
SELECT *
FROM ML.PREDICT(
  MODEL `bq-sandbox-ariana.nyc_taxi_ml.zone_clusters_k4`,
  (
    SELECT
      trip_count,
      avg_total_amount,
      avg_fare_amount,
      avg_tip_amount,
      avg_duration_minutes,
      avg_distance,
      pct_rush_hour,
      pct_night,
      pct_weekend,
      pct_adverse_weather
    FROM `bq-sandbox-ariana.nyc_taxi_ml.mart_zone_clustering`
  )
);
