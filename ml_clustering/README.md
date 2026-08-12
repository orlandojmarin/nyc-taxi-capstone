# NYC Taxi Trip Segmentation Analysis

## Overview

This analysis used K-Means clustering to identify distinct groups of taxi trip behavior patterns. Multiple values of **k** were evaluated, and the **Davies-Bouldin Index (DBI)** was used to measure cluster quality.

Lower DBI values indicate better cluster separation and more cohesive clusters.

---

## Model Evaluation

| Clusters (k) | Davies-Bouldin Index |
|-------------|---------------------|
| 3 | 1.7770 |
| 4 | 1.4220 |
| 5 | 1.4984 |
| 6 | 1.3979 |

### Decision

Although **k=6** produced the lowest DBI score, the improvement over **k=4** was small. The six-cluster solution created additional segments that were more difficult to interpret and explain.

For business usability and interpretability, **k=4** was selected as the final model.

---

## Cluster Characteristics (k = 4)

| Feature | Cluster 1 | Cluster 2 | Cluster 3 | Cluster 4 |
|----------|-----------|-----------|-----------|-----------|
| Average Distance (miles) | 5.0 | 9.1 | 2.4 | 7.6 |
| Average Duration (minutes) | 22.9 | 27.7 | 14.8 | 35.5 |
| Average Fare Amount ($) | 26.8 | 58.4 | 16.8 | 34.4 |
| Average Tip Amount ($) | 1.1 | 6.0 | 2.6 | 0.5 |
| Average Total Amount ($) | 31.8 | 72.3 | 24.8 | 39.2 |
| % Adverse Weather | 0.1 | 0.1 | 0.1 | 0.1 |
| % Night Trips | 0.4 | 0.4 | 0.3 | 0.2 |
| % Rush Hour Trips | 0.2 | 0.1 | 0.2 | 0.2 |
| % Weekend Trips | 0.4 | 0.4 | 0.3 | 0.2 |
| Trip Count | 27,107 | 62,928 | 375,119 | 4,852 |

---

## Cluster Descriptions

### Cluster 1: Standard Trips

**Characteristics**
- Medium trip distance
- Medium trip duration
- Moderate fares and total cost
- Represents typical taxi ride behavior

**Metrics**
- Avg Distance: 5.0 miles
- Avg Duration: 22.9 minutes
- Avg Fare: $26.80
- Avg Total: $31.80

**Business Interpretation**
Standard everyday taxi trips that make up a significant portion of overall demand.

---

### Cluster 2: High-Value Long Trips

**Characteristics**
- Longest average distance
- Highest fares and total charges
- Largest average tips
- Premium revenue-generating trips

**Metrics**
- Avg Distance: 9.1 miles
- Avg Duration: 27.7 minutes
- Avg Fare: $58.40
- Avg Total: $72.30

**Business Interpretation**
High-revenue customers taking longer trips that contribute disproportionately to overall earnings.

---

### Cluster 3: Short Everyday Trips

**Characteristics**
- Shortest distance traveled
- Shortest trip duration
- Lowest fares
- Highest trip volume

**Metrics**
- Avg Distance: 2.4 miles
- Avg Duration: 14.8 minutes
- Avg Fare: $16.80
- Avg Total: $24.80
- Trip Count: 375,119

**Business Interpretation**
Represents the majority of taxi activity. These short trips generate consistent demand but lower revenue per ride.

---

### Cluster 4: Slow/Long-Duration Trips

**Characteristics**
- Similar distances to Cluster 2
- Longest trip durations
- Moderate fare levels
- Low average tips

**Metrics**
- Avg Distance: 7.6 miles
- Avg Duration: 35.5 minutes
- Avg Fare: $34.40
- Avg Total: $39.20

**Business Interpretation**
Trips that cover relatively fewer miles per minute than Cluster 2, potentially influenced by traffic congestion, urban routing, or operational delays.

---

## Key Findings

1. **Distance and duration were major differentiators** between clusters.
2. **Cluster 3 (Short Everyday Trips)** accounts for the largest share of trips by a substantial margin.
3. **Cluster 2 (High-Value Long Trips)** generates the highest revenue per trip.
4. **Cluster 4 (Slow/Long-Duration Trips)** highlights situations where trip duration increases without a proportional increase in distance or revenue.
5. Weather-related variables showed minimal variation across clusters and were not major factors in segmentation.

---

## Conclusion

The final K-Means model with **k=4** provides a balance between statistical quality and business interpretability. The identified segments represent four distinct rider behaviors:

1. **Standard Trips**
2. **High-Value Long Trips**
3. **Short Everyday Trips**
4. **Slow/Long-Duration Trips**

These segments can be used to support pricing analysis, operational planning, demand forecasting, and customer behavior insights.