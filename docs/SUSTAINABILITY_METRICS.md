# 🌱 Sustainability & ESG Metrics Documentation

Documentation of sustainability framework, UN Sustainable Development Goals (SDGs) alignment, Indian Central Electricity Authority (CEA) grid conversion factors, and transparent facility sustainability index calculation.

---

## 🎯 UN Sustainable Development Goals (SDGs) Alignment

Our platform directly supports three key UN SDGs:

1. **SDG 7: Affordable and Clean Energy**:
   - Reduces wasted electricity through AI anomaly detection, HVAC schedule optimization, and rooftop solar offset tracking.
2. **SDG 9: Industry, Innovation, and Infrastructure**:
   - Modernizes legacy institutional facilities with IoT smart sensors, predictive maintenance, and Explainable AI (XAI).
3. **SDG 11: Sustainable Cities and Communities**:
   - Optimizes civic waste collection routes, monitors campus AQI, manages traffic congestion, and supports climate resilience.

---

## 🏭 Documented Carbon Emission Conversion Factors

Carbon emissions are calculated using standard conversion constants sourced from the **Indian Central Electricity Authority (CEA) Baseline Database** and **IPCC Guidelines**:

| Emission Source | Conversion Factor | Source Standard |
| :--- | :--- | :--- |
| **Grid Electricity** | $0.82 \text{ kg CO}_2\text{e} / \text{kWh}$ | CEA India Grid Emission Factor (v18.0) |
| **Diesel Generator Fuel** | $2.68 \text{ kg CO}_2\text{e} / \text{Liter}$ | IPCC Guidelines for National GHG Inventories |
| **Passenger Car Transport** | $0.14 \text{ kg CO}_2\text{e} / \text{km}$ | Fleet Mix Weighted Average |
| **Bus / Shuttle Transport** | $0.85 \text{ kg CO}_2\text{e} / \text{km}$ | Indian Commercial Vehicle Baseline |
| **Two-Wheeler Transport** | $0.04 \text{ kg CO}_2\text{e} / \text{km}$ | 2-Wheeler Indian Emissions Benchmark |

⚠️ **Mandatory Disclaimer**: Estimated $\text{CO}_2\text{e}$ outputs are internal operational decision-support indicators and do NOT constitute official statutory carbon audit measurements.

---

## 📊 Transparent Facility Sustainability Score (0 to 100)

The composite **Facility Intelligence Sustainability Score** is calculated across 7 weighted dimensions using normalized sub-scores ($0\text{--}100$):

$$\text{Sustainability Score} = \sum_{i=1}^{7} w_i \times \text{SubScore}_i$$

### Configurable Weights (`config/scoring_weights.json`):

```json
{
  "weights": {
    "energy_efficiency": 0.20,
    "water_efficiency": 0.15,
    "waste_management": 0.15,
    "air_quality": 0.15,
    "renewable_energy": 0.10,
    "emissions": 0.15,
    "occupancy_efficiency": 0.10
  }
}
```

### Performance Rating Bands:
- **85.0 to 100.0**: `PLATINUM (LEADERSHIP)`
- **70.0 to 84.9**: `GOLD (EFFICIENT)`
- **50.0 to 69.9**: `SILVER (MODERATE)`
- **Below 50.0**: `BRONZE (REQUIRES ACTION)`

⚠️ **Mandatory Disclaimer**: Internal benchmarking metric; not an official government GRI/LEED certification.
