# Realtime MLOps

**A hands-on tutorial/POC** demonstrating real-time anomaly detection for datacenter monitoring using **Kafka streaming** and **ML-powered detection**.

Learn how to build, deploy and operate ML models in a streaming architecture through a working example.

---

## Project Goals

- Educational project to understand **streaming + MLOps** integration
- Working POC with `docker-compose up` for learning and demos
- Foundation for future production-grade monitoring platform

---

## Architecture

```text
        ┌─────────────────┐
        │   Generator     │
        │ (backfill 14d)  │
        └───────┬─────────┘
                ↓
      ┌───────────────────────┐
      │      Kafka Topic       │
      │  "server_metrics"      │
      │  "application_metrics" │
      └───┬───────────┬────────┘
          │           │
   ┌──────▼───┐      │
   │ Consumer │      │
   │ Storage  │      │
   └─────┬────┘      │
         │           │
         ↓           │
   ┌──────────────────────────────┐
   │       TimescaleDB            │
   │  - server_metrics            │
   │  - application_metrics       │◄───┐
   │  - anomalies                 │    │
   └──┬───────────────────────────┘    │
      │                                │
      ↓                                │
   ┌──────────────────┐                │
   │ Anomaly Trainer  │                │
   │ (STL + Z-score)  │                │
   │ - Every 60 min   │                │
   │ - 14d history    │                │
   └─────┬────────────┘                │
         │                             │
         ↓                             │
   ┌──────────────────┐                │
   │      Redis       │                │
   │ (Model Storage)  │                │
   └─────┬────────────┘                │
         │                             │
         ↓                             │
   ┌──────────────────┐                │
   │ Anomaly Detector │                │
   │ (Real-time STL)  │                │
   └─────┬────────────┘                │
         │                             │
         └─────────────────────────────┘
                       │
                       ↓
                ┌──────────────┐
                │   Grafana    │
                │ (Dashboards) │
                └──────────────┘

```

---

## Components

- **Generator** → Synthetic datacenter metrics with backfill (14 days) and real-time streaming
- **Kafka + Zookeeper** → Event streaming (server & application metrics)
- **TimescaleDB** → Time-series PostgreSQL with hypertables for efficient storage
- **Redis** → In-memory cache for trained ML models
- **Anomaly Detection** → STL (Seasonal-Trend decomposition) + Z-score algorithm
- **Grafana** → Real-time dashboards (Infrastructure + ML Anomaly Detection)
- **Docker Compose** → Complete stack deployment

---

## Quickstart

```bash
git clone https://github.com/Natale-F/realtime-mlops.git
cd realtime-mlops
docker-compose up --build
```

Once running:
- **Grafana** → [http://localhost:3000](http://localhost:3000) (admin/admin)
  - Infrastructure Dashboard: Real-time metrics
  - ML Anomaly Detection: Detected anomalies & investigation
- **PostgreSQL** → `localhost:5432` (user: postgres, password: postgres)
- **Kafka** → `localhost:9092`
- **Redis** → `localhost:6379`

The system will:
1. Backfill 14 days of historical data (4800 points/server)
2. Train anomaly detection models after 60 seconds
3. Start real-time anomaly detection
4. Display live metrics and anomalies in Grafana

---

## ML Anomaly Detection

**Method**: STL (Seasonal-Trend decomposition using Loess) + Z-score

**Configuration**:
- **History**: 14 days of data
- **Aggregation**: 5-minute buckets
- **Seasonal Period**: 288 (24h cycle in 5-min intervals)
- **Z-Score Threshold**: 3.0 (3 standard deviations)
- **Retraining**: Every 60 minutes

**Monitored Metrics**:
- CPU Usage (%)
- Memory Usage (%)
- CPU Temperature (°C)

**How it works**:
1. **Training**: Every hour, the trainer fetches 14 days of historical data, decomposes it into trend + seasonal + residual components using STL, and stores the model in Redis
2. **Detection**: The detector loads models from Redis and compares real-time values against expected values (trend + seasonal). If |z-score| > 3.0, an anomaly is flagged
3. **Storage**: Detected anomalies are stored in PostgreSQL with severity levels (low, medium, high, critical)
4. **Visualization**: Grafana displays anomalies in real-time with drill-down investigation capabilities

---

## Example Data Flow

**Metric Event**:
```json
{
  "timestamp": "2026-01-24T12:34:56Z",
  "server_id": "srv-001",
  "rack_id": "rack-A",
  "cpu_usage_percent": 85.2,
  "memory_usage_percent": 72.1,
  "cpu_temperature_celsius": 68.5,
  "power_consumption_watts": 450.3,
  "network_rx_mbps": 120.5,
  "network_tx_mbps": 95.7
}
```

**Anomaly Detection**:
```json
{
  "timestamp": "2026-01-24T12:34:56Z",
  "entity_id": "srv-001",
  "entity_type": "server",
  "severity": "high",
  "anomaly_score": 0.89,
  "details": {
    "metric_name": "cpu_usage_percent",
    "actual_value": 95.3,
    "expected_value": 65.2,
    "z_score": 4.2,
    "residual": 30.1
  }
}
```

---

## Project Structure

```
realtime-mlops/
├── docker-compose.yml       # Complete stack orchestration
├── requirements.txt
├── src/
│   ├── generator/           # ✅ Event generator with backfill
│   │   ├── models.py        # Data models & configs
│   │   ├── server_state.py  # Server metrics simulation
│   │   ├── service_state.py # Application metrics simulation
│   │   ├── generator.py     # Main orchestrator
│   │   └── generate.py      # CLI entry point
│   ├── consumers/           # ✅ Kafka consumers
│   │   ├── storage.py       # Metrics → TimescaleDB
│   │   └── anomaly/         # ✅ ML anomaly detection
│   │       ├── train.py     # Model training (STL)
│   │       ├── detect.py    # Real-time detection
│   │       ├── methods/     # Detection algorithms
│   │       ├── database.py  # PostgreSQL queries
│   │       └── models.py    # Data models
│   └── core/                # Shared utilities
├── grafana/                 # ✅ Dashboard provisioning
│   └── provisioning/
│       └── dashboards/
│           ├── datacenter-overview.json
│           └── production-monitoring.json
├── tests/                   # Unit tests
└── Makefile                 # Dev shortcuts
```

---

## Generator Features

**Backfill Mode**: Generate 14 days of historical data (300s interval)
**Real-time Mode**: Stream live metrics (5s interval)
**8 Anomaly Types**: CPU spike, memory leak, temperature, network saturation, power spike, latency spike, error rate spike, crash
**6 Predefined Configs**: normal, chaos, temperature, network, production, dev

**Usage**:
```bash
# Production mode (with backfill)
python -m src.generator.generate --config production --backfill-days 14

# Custom config
python -m src.generator.generate --servers 10 --duration 3600

# See all options
python -m src.generator.generate --help
```

---

## Development

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Code quality
make lint        # Check with ruff
make format      # Auto-format code

# Testing
make test        # Run tests
make test-cov    # With coverage

# Docker commands
docker-compose up --build      # Start all services
docker-compose down            # Stop services
docker-compose down -v         # Stop + remove volumes (full reset)
docker-compose logs -f [service]  # View logs
```

---

## Roadmap

**Phase 1 - Real-time Anomaly Detection (Current)**
- [x] Production-ready event generator with backfill
- [x] Kafka → TimescaleDB storage consumer
- [x] STL-based anomaly detection (training + real-time detection)
- [x] Redis model storage
- [x] Grafana dashboards (Infrastructure + ML Detection)
- [ ] Model drift detection & monitoring
- [ ] Alert notifications (Slack/Email)
- [ ] Production hardening (error handling, monitoring, testing)

**Phase 2 - Production-Ready Platform**
- [ ] Kubernetes deployment
- [ ] ClickHouse for scale (100M+ events/day)
- [ ] Multi-algorithm support (LSTM, Prophet, etc.)
- [ ] Auto-tuning hyperparameters
- [ ] High availability & fault tolerance
- [ ] Complete test coverage & CI/CD
- [ ] Transform into plug-and-play monitoring platform

---

## Troubleshooting

**Reset Everything**:
```bash
docker-compose down -v  # Remove all data
docker-compose up --build
```

**Check Logs**:
```bash
docker-compose logs -f anomaly-trainer
docker-compose logs -f anomaly-detector
```

**Redis Model Check**:
```bash
docker-compose exec redis redis-cli
> KEYS *
> GET model:server:srv-001:cpu_usage_percent
```

**Force Model Rebuild**:
```bash
docker-compose exec redis redis-cli FLUSHALL
docker-compose restart anomaly-trainer
```

---

## Contributing

Contributions welcome! Open an issue or submit a PR.

---

## License

MIT License – free to use, modify and share.
