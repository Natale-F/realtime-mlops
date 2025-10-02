# Storage Consumer

Production-ready Kafka consumer that ingests datacenter metrics into PostgreSQL.

## Overview

The storage consumer reads events from the `datacenter-metrics` Kafka topic and stores them in PostgreSQL tables (`server_metrics` and `application_metrics`).

## Features

- **Batch Processing**: Configurable batch size for optimal database performance
- **Automatic Routing**: Routes messages to appropriate tables based on event type
- **Error Handling**: Robust error handling with automatic retries and logging
- **Health Checks**: Database health monitoring
- **Manual Commit Control**: Ensures data consistency with manual offset commits
- **Structured Logging**: Clear operational visibility with `structlog`
- **Graceful Shutdown**: Proper cleanup on interrupt signals

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure (Kafka + PostgreSQL)
make docker-up-infra

# Run consumer
make consumer-storage

# Or with custom settings
python -m src.consumers.consume --kafka-servers localhost:9092 --postgres-host localhost
```

### Docker Deployment

```bash
# Start everything (infrastructure + generator + consumer)
docker compose up --build

# View consumer logs
make docker-logs-consumer
```

## Configuration

### Environment Variables

- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers (default: `localhost:9092`)
- `KAFKA_TOPIC`: Kafka topic name (default: `datacenter-metrics`)
- `POSTGRES_HOST`: PostgreSQL host (default: `localhost`)
- `POSTGRES_PORT`: PostgreSQL port (default: `5432`)
- `POSTGRES_DB`: Database name (default: `mlops_db`)
- `POSTGRES_USER`: Database user (default: `mlops`)
- `POSTGRES_PASSWORD`: Database password (default: `mlops_password`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

### CLI Options

```bash
python -m src.consumers.consume --help
```

Key options:

- `--batch-size`: Number of messages to batch before committing (default: 100)
- `--commit-interval`: Max seconds between commits (default: 5.0)
- `--max-poll-records`: Max records per Kafka poll (default: 500)
- `--duration`: Run for specific duration in seconds (default: infinite)
- `--offset-reset`: Auto offset reset strategy: `earliest` or `latest`

## Architecture

```text
┌─────────────────┐
│   Kafka Topic   │
│ datacenter-     │
│   metrics       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Storage Consumer│
│  - Parse JSON   │
│  - Route events │
│  - Batch writes │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│  - server_      │
│    metrics      │
│  - application_ │
│    metrics      │
└─────────────────┘
```

## Event Types

### Server Metric

```json
{
  "type": "server_metric",
  "timestamp": "2025-10-02T12:34:56Z",
  "server_id": "srv-001",
  "cpu_usage_percent": 75.2,
  "memory_usage_percent": 62.5,
  "cpu_temperature_celsius": 68.3,
  "power_consumption_watts": 245.7,
  "rack_id": "R01",
  "datacenter_zone": "marseille-1",
  ...
}
```

### Application Metric

```json
{
  "type": "application_metric",
  "timestamp": "2025-10-02T12:34:56Z",
  "service_name": "api-gateway-1",
  "server_id": "srv-001",
  "request_rate_per_sec": 456.2,
  "response_time_p95_ms": 125.3,
  "error_rate_percent": 0.5,
  ...
}
```

## Performance

- **Throughput**: 1000+ events/second with batch inserts
- **Latency**: < 5 seconds from Kafka to PostgreSQL (configurable)
- **Memory**: ~100-200 MB under normal load

## Module Structure

```text
consumers/
├── __init__.py           # Package exports
├── models.py             # Configuration models
├── database.py           # PostgreSQL connection & operations
├── storage_consumer.py   # Main consumer logic
└── consume.py            # CLI entry point
```

## Error Handling

- **Parse errors**: Logged and counted, consumer continues
- **Database errors**: Logged and counted, batch is retried
- **Connection loss**: Automatic reconnection attempts
- **Unknown event types**: Logged as warnings, not inserted

## Monitoring

Key metrics logged every 10 seconds:

- `total_consumed`: Total messages consumed
- `server_metrics`: Number of server metrics inserted
- `application_metrics`: Number of application metrics inserted
- `parse_errors`: Number of unparseable messages
- `insert_errors`: Number of failed insertions
- `rate_per_sec`: Throughput rate

## Examples

### High-throughput production setup

```bash
python -m src.consumers.consume \
  --batch-size 500 \
  --commit-interval 10.0 \
  --max-poll-records 1000
```

### Low-latency real-time setup

```bash
python -m src.consumers.consume \
  --batch-size 50 \
  --commit-interval 1.0
```

### Debug mode with latest messages only

```bash
python -m src.consumers.consume \
  --log-level DEBUG \
  --offset-reset latest
```

