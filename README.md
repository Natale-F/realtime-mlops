# Realtime mlops

A hands-on tutorial project to do some **real-time MLOps** by building a monitoring platform connected to a Kafka event stream.
I will create a generator to simulate events in the kafka topic.

The project evolves in **two phases**:
1. **Tutorial** – educational resource to understand Kafka + MLOps end-to-end  
2. **Platform** – simple monitoring system that can be plugged into any Kafka event stream

---

## Project Goals

- Show how to combine **streaming + MLOps** in a clear iterative way  
- Provide a plug-and-play environment (`docker-compose up`) for learning and demos  
- Serve as a foundation for a future lightweight **monitoring platform** for datacenter-like events  

---

## Architecture

```text
        ┌─────────────────┐
        │   Generator     │
        │ (synthetic data)│
        └───────┬─────────┘
                ↓
      ┌───────────────────────┐
      │      Kafka Topic       │
      │   "datacenter-metrics" │
      └───┬───────────┬───────┘
          │           │
   ┌──────▼───┐ ┌─────▼─────┐ ┌───────────┐
   │ Consumer │ │ Predictor  │ │ Anomaly   │
   │ Storage  │ │ (ML model) │ │ Detector  │
   └─────┬────┘ └─────┬─────┘ └────┬──────┘
         │            │            │
         ↓            ↓            ↓
   ┌──────────────────────────────────────────┐
   │               PostgreSQL                 │
   │  - metrics (history)                     │
   │  - predictions (real-time)               │
   │  - anomalies (real-time)                 │
   └───────────────────┬──────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ↓                           ↓
 ┌───────────────────┐        ┌──────────────────────┐
 │ Drift Detection   │        │  Model Retraining    │
 │ (batch, alerts)   │        │ (batch, daily ML)    │
 └─────────┬─────────┘        └──────────┬──────────┘
           │                              │
           ↓                              ↓
     ┌──────────────┐              ┌──────────────┐
     │   Grafana    │◄─────────────┤   MLflow     │
     │ (alerting)   │              │ (model store)│
     └──────────────┘              └──────────────┘

```

---

## Components

- **Kafka + Zookeeper** → event streaming backbone  
- **TimescaleDB** → time-series database for metrics storage (PostgreSQL extension with hypertables, compression, continuous aggregates)
- **Grafana** → real-time dashboards & alerting
- **MLflow** → model training & versioning  
- **scikit-learn** → ML models (regression + anomaly detection)  
- **Docker Compose** → easy local deployment

> **Note**: Currently using TimescaleDB (PostgreSQL + time-series optimizations). Future migration to ClickHouse planned for Phase 2 to handle 100M+ events/day.  

---

## Quickstart

Clone the repo and start everything with Docker Compose:

```bash
git clone https://github.com/Natale-F/realtime-mlops.git
cd realtime-mlops
docker-compose up --build
```

Once running:

- Grafana → [http://localhost:3000](http://localhost:3000)  
- PostgreSQL → `localhost:5432`  
- Kafka broker → `localhost:9092`  

---

## Example Workflow

1. **Synthetic generator** produces events:
   ```json
   {
     "time": "2025-09-30T12:34:56Z",
     "server_id": "srv-42",
     "cpu_usage": 75.2,
     "temperature": 63.1,
     "power_kw": 2.3,
     "network_gbps": 0.7
   }
   ```

2. **Consumers** process events:
   - Store raw metrics  
   - Run real-time ML predictions (expected power usage)  
   - Detect anomalies (e.g., overheating, spikes)  

3. **TimescaleDB** stores everything in hypertables optimized for time-series queries.

4. **Grafana** dashboards display live metrics with auto-refresh every 5 seconds.  

---

## Machine Learning

The focus of this project is **not to design state-of-the-art ML models.**

Instead, the goal is to demonstrate how to i**ntegrate and operate ML in production** within a **real-time streaming system**.

For simplicity, I chose scikit-learn as the baseline library:

- Power prediction model: **RandomForestRegressor**
- Anomaly detection model: **IsolationForest**

Models are intentionally simple so that the complexity stays on the MLOps side:
- packaging the models,
- serving them in real-time consumers,
- monitoring drift,
- retraining and redeploying automatically.

### Current workflow

Models are trained in batch once per day on the historical data stored in PostgreSQL.
A basic training script handles the whole process:

```bash
docker-compose run --rm ml-trainer
```

Trained models are **logged and versioned with MLflow**, then reloaded by the streaming consumers.

### Future improvements  

- **Retraining on demand**: add an API that allows the system to retrain when needed, for example after drift detection triggers an alert.
- **Push-to-MLflow**: once retrained, the new version is pushed to MLflow and automatically picked up by the consumers.
- **Continuous deployment of models**: the consumers will reload the latest “production” model seamlessly without restart.

👉 In short: the data science part is kept simple on purpose.

The project is about showing how to **industrialize the ML lifecycle** (training → versioning → serving → monitoring → retraining).

---

## Project Structure

```
realtime-mlops/
├── docker-compose.yml
├── requirements.txt
├── src/
│   ├── generator/          # ✨ Modular event generator
│   │   ├── models.py       # Data models & configs
│   │   ├── server_state.py # Server metrics
│   │   ├── service_state.py# Application metrics
│   │   ├── generator.py    # Main orchestrator
│   │   ├── config.py       # 6 predefined configs
│   │   └── generate.py     # CLI entry point
│   ├── consumers/          # 🚧 Kafka consumers (coming soon)
│   ├── ml/                 # 🚧 ML models (coming soon)
│   └── core/               # Shared utilities (logger)
├── tests/                  # Unit tests
├── Makefile               # Dev shortcuts
└── pyproject.toml         # Project config

```

### ✨ Generator Features

**New in Phase 1**: Modular, production-ready generator

- **8 Anomaly Types**: CPU spike, memory leak, temperature, network saturation, etc.
- **6 Predefined Configs**: normal, chaos, temperature, network, production, dev
- **Structured Logging**: with `structlog`
- **CLI Interface**: Easy configuration via command line
- **Code Quality**: Ruff linter, type hints, modular architecture

**Quick Usage**:
```bash
# Install
pip install -r requirements.txt

# Run with predefined config
python -m src.generator.generate --config normal

# Custom config
python -m src.generator.generate --servers 20 --anomaly-prob 0.05 --duration 300

# See all options
python -m src.generator.generate --help
```

**Development Tools**:
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Code quality
make lint        # Check code style with ruff
make fix         # Auto-fix issues
make format      # Format code

# Testing
make test        # Run 46 tests
make test-cov    # Run with coverage (69%)

# Or use tools directly
ruff check src/
pytest tests/ -v
```

**Testing**: 46 tests covering models, state management, and generator logic with Kafka mocking.

See [`docs/`](docs/) for detailed guides on each component.

---

## 🌍 Roadmap

**Phase 1 - MLOps Foundation (Current)**
- [x] Production-ready event generator with anomaly injection
- [x] Kafka → TimescaleDB storage consumer with batch optimization
- [x] Real-time Grafana dashboards with TimescaleDB integration
- [ ] Real-time predictions & anomaly detection consumers
- [ ] Model drift detection with MLflow

**Phase 2 - Production Scale**
- [ ] Migrate TimescaleDB → **ClickHouse** for ultra-high throughput (100M+ events/day)
- [ ] Kubernetes Helm charts  
- [ ] Multi-datacenter support  
- [ ] Transform into a plug-and-play monitoring platform  

---

## Reset database

If you want to completly reset the PostgreSQL data, you can run the following command

```bash
docker-compose down -v 
```

## Contributing

This project starts as a **tutorial**, but contributions are welcome to grow it into a **real platform**.  

Open an issue or submit a PR.

---

## License

MIT License – free to use, modify and share.
