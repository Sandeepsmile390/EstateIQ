# ESTATEIQ — KNOWN LIMITATIONS & DISCLAIMERS

## 1. Hardware Integration Disclaimer
- **Simulated IoT Telemetry**: Sensor feeds (electricity sub-meters, pipe flow rates, IoT bin fill level sensors, AQI monitors) operate on **SIMULATED IoT** telemetry generated via statistical distributions modeling real campus behavior.
- **Physical Hardware Interfaces**: Production integration with BACnet, Modbus, MQTT, or SCADA gateways requires hardware adapter setup.

## 2. Financial & ML Predictions
- **Model Estimates**: All financial ROI savings ($/yr, ₹/mo) and carbon reduction figures are **MODEL ESTIMATES** derived from CatBoost, Random Forest, and Isolation Forest algorithms. They represent analytical optimization targets rather than guaranteed contractual savings.
- **SHAP Feature Contributions**: SHAP values explain model feature importance for given predictions and do not constitute direct physical causation proofs.

## 3. Grounded AI Co-Pilot
- **LLM Fallback**: If no external OpenAI/GenAI API key is present in `.env`, the system seamlessly utilizes a deterministic rule-based NLP query engine grounded strictly in active EstateIQ dataset context.
