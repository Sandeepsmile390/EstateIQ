# EstateIQ FastAPI REST Backend API

This directory houses the primary REST backend and real-time streaming services for the **EstateIQ Facility Decision Intelligence Platform**.

---

## 🚀 Key Modules

| Module | Description |
|---|---|
| `main.py` | Primary FastAPI application definition, lifecycle handlers, CORS middleware, global error handling, and router registration. |
| `canonical_routes.py` | Canonical IoT ingestion routes (`/api/v1/iot/*`), SSE real-time telemetry stream, device registry integration, and backward-compatible endpoints. |

---

## 🌐 Endpoint Reference

### 1. Canonical IoT Telemetry & Edge Streaming (`/api/v1/iot/*`)
- **`POST /api/v1/iot/telemetry`**: Ingests single telemetry JSON object or JSON array batch. Validates schemas, tags data provenance (`[REAL SENSOR]` vs `[SIMULATED DATA]`), updates device registry, and broadcasts to live SSE subscribers.
- **`GET /api/v1/iot/telemetry/stream`**: Returns a JSON snapshot of recent telemetry records and registry statistics. The current dashboard refreshes by polling; this route is not an SSE/WebSocket stream.
- **`GET /api/v1/iot/telemetry/recent`**: Retrieves the most recent telemetry readings filtered by `device_id` or `building_id`.
- **`GET /api/v1/iot/devices`**: Returns inventory of registered hardware meters and simulated device profiles, current health status (`ONLINE`, `STREAMING`, `STALE`, `OFFLINE`), and last sample.
- **`POST /api/v1/iot/devices/register`**: Registers or updates device profile specifications.
- **`POST /api/v1/iot/simulators/pair`**: Exchanges single-use pairing codes (`IQ-DEMO`) for LAN simulator authorization tokens.
- **`POST /api/v1/iot/simulators/{instance_id}/heartbeat`**: Ingests periodic keep-alive heartbeats from edge nodes.

### 2. Backward Compatibility Endpoints
- `POST /api/v1/ingestion/telemetry` ➔ Maps directly to canonical ingestion.
- `POST /api/v1/ingestion/batch` ➔ Maps directly to canonical batch ingestion.
- `GET /api/v1/devices` ➔ Returns device list from central registry.
- `GET /api/v1/devices/{device_id}/health` ➔ Returns device health state.

### 3. Core System & AI Endpoints
- **`GET /health`**: Health check probe returning server version and database connectivity status.
- **`GET /api/v1/ai/health`**: AI subsystem status and Groq Cloud LPU connection check.
- **`POST /api/v1/ai/copilot/query`**: Grounded AI Copilot assistant answering facility inquiries grounded in structured JSON Evidence Packets.

---

## 🔐 Security & Gateway Authentication

Edge devices and gateways authenticate via HTTP request headers:
- `X-Gateway-Key`: Must match `GATEWAY_API_KEY` (default: `ESTATEIQ-GATEWAY-SECRET-KEY`).
- `X-API-Key`: Alternative API key header.
- `Authorization`: `Bearer <JWT_TOKEN>` for user role-based access control (`administrator`, `operations`, `sustainability`, `viewer`).

---

## 🛠️ Running the Backend

From the repository root:
```bash
# Using uvicorn directly
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Or on Windows using batch runner
run_api.bat

# Or on Linux/macOS
./run_api.sh
```

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc UI: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- SSE Live Stream: [http://localhost:8000/api/v1/iot/telemetry/stream](http://localhost:8000/api/v1/iot/telemetry/stream)
