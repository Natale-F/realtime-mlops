# Docker Guide

## Quick Start

```bash
# Start all services
docker compose up --build

# Or start in background
docker compose up -d
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `zookeeper` | 2181 | Kafka coordination |
| `kafka` | 9092 | Kafka broker |
| `postgres` | 5432 | Database |
| `generator` | - | Event generator |
| `kafka-ui` | 8080 | Kafka web UI |

## Generator Configuration

### Using different configs

```bash
# Normal config (default)
docker compose up generator

# Chaos config
docker compose run --rm generator \
  python -m src.generator.generate --config chaos --kafka-servers kafka:29092

# Custom config
docker compose run --rm generator \
  python -m src.generator.generate \
  --servers 20 --services 10 --anomaly-prob 0.1 --kafka-servers kafka:29092
```

### Environment variables

Edit `docker-compose.yaml`:

```yaml
generator:
  environment:
    KAFKA_BOOTSTRAP_SERVERS: kafka:29092
    KAFKA_TOPIC: datacenter-metrics
    LOG_LEVEL: DEBUG  # Change log level
```

## Docker Architecture

### Single Base Image

The project uses a **single base image** (`realtime-mlops:latest`) for all services.

**Dockerfile** (neutral):
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
ENV PYTHONPATH=/app
# No CMD - defined per service in docker-compose
```

**Benefits**:
- ✅ Single image to build
- ✅ Same environment for all services
- ✅ Shared build cache (fast)
- ✅ Easy to add new services

### Current Services

```yaml
# Generator - uses base image
generator:
  image: realtime-mlops:latest
  command: ["python", "-m", "src.generator.generate", "--config", "normal"]

# ML Consumer (coming soon - example)
ml-consumer:
  image: realtime-mlops:latest
  command: ["python", "-m", "src.consumers.ml_consumer"]
```

## Useful Commands

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f generator
docker compose logs -f kafka
```

### Check status

```bash
docker compose ps
```

### Stop services

```bash
# Stop all
docker compose down

# Stop and remove volumes (reset data)
docker compose down -v
```

### Rebuild

```bash
# Rebuild generator after code changes
docker compose build generator
docker compose up generator

# Or rebuild all
docker compose up --build
```

## Kafka UI

Access Kafka UI at [http://localhost:8080](http://localhost:8080) to:
- View topics
- See messages in real-time
- Monitor consumer groups
- Check broker health

## Healthchecks

Services have healthchecks:

```yaml
kafka:
  healthcheck:
    test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Generator waits for Kafka to be healthy before starting:

```yaml
generator:
  depends_on:
    kafka:
      condition: service_healthy
```

## Troubleshooting

### Generator can't connect to Kafka

```bash
# Check Kafka is running
docker compose ps kafka

# Check Kafka logs
docker compose logs kafka

# Wait for Kafka to be ready (takes ~30s)
docker compose up kafka
# Wait for "started" message, then start generator
docker compose up generator
```

### Reset everything

```bash
docker compose down -v
docker compose up --build
```

### View generator metrics in Kafka

1. Open Kafka UI: http://localhost:8080
2. Click "Topics"
3. Click "datacenter-metrics"
4. View messages in real-time
