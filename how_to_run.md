Step 1: Open Your Terminal & Navigate to Project Root
Open PowerShell, Command Prompt, or your IDE terminal and make sure you are in the project folder:

cd d:\Hackathon\Model
Step 2: Install Required Dependencies
Install all required Python libraries:


pip install -r requirements.txt
Step 3: Initialize Database & Generate IoT Data
Initialize the SQLite database (facility.db) and generate 180 days of realistic multi-module IoT sensor data:


python scripts/setup_database.py
(This creates facility_dataset/facility.db containing 16 indexed domain tables).

Step 4: Train & Register Machine Learning Models
Train all 9 domain ML models (Energy, Water, Waste, Air Quality, Traffic, Parking, Equipment Maintenance, Safety, and Carbon Emissions):


python train_all_modules.py
(This builds and serializes model artifacts into the models/ folder).

Step 5: Verify Models & View Performance Metrics
Run the evaluation audit script to verify trained models and export performance metrics:


python scripts/evaluate_models.py
This generates:



reports/model_metrics.csv


reports/model_metrics.json
Step 6: Run Automated Tests (Optional Safety Check)
Verify that all 25 automated unit and pipeline tests pass:


python -m unittest discover tests
You should see: Ran 25 tests ... OK (25/25 PASSED).

Step 7: Launch the Backend API Service (Terminal 1)
Start the FastAPI backend REST server:


uvicorn api.main:app --reload --port 8000
Interactive API Swagger Documentation will be available at: http://127.0.0.1:8000/docs
Step 8: Launch the Streamlit Intelligence Dashboard (Terminal 2)
Open a second terminal window, navigate to d:\Hackathon\Model, and start the dashboard:


streamlit run app.py
The dashboard will automatically open in your browser at: http://localhost:8501

🌐 How to Explore Predictions & Features on the Dashboard
Once the dashboard opens in your browser (http://localhost:8501), use the left sidebar navigation to explore:

📊 Executive Dashboard (Page 1)

View high-level campus metrics, total energy (kWh), water consumption, waste overflow alerts, and the Sustainability Health Score (78.5 - Gold).
Interactive GIS Map showing building coordinates and live alert markers across the campus.
⚡ Energy Intelligence (Page 2)

See short-term Energy kWh Predictions & Forecasts (1h, 4h, 24h ahead).
View detected HVAC Anomalies (e.g. Block B Hostel surge).
🔍 SHAP Explainable AI (Page 10)

Visualizes feature contribution force plots showing why the model made a specific energy or equipment prediction (e.g. temperature and occupancy drivers).
🗑️ Waste Overflow Prediction (Page 4)

View estimated 2-hour overflow probabilities for campus waste bins and automated collection dispatch alerts.
⚙️ Equipment Maintenance Risk (Page 7)

Monitors chiller vibration and thermal telemetry to predict equipment failure risk before breakdown occurs.
🧪 What-If Scenario Simulation (Page 14)

Adjust operational sliders (e.g. reduce HVAC load by 15% or increase solar capacity) and see instant simulated energy & CO₂e savings predictions.
🤖 AI Assistant & Decision Support (Page 13)

Ask natural language questions like "Why is energy consumption high in Block B Hostel?" or "Which waste bins need emptying?". Works online or with built-in offline fallback.