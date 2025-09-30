# Generator Documentation

## Overview

The generator simulates realistic datacenter metrics with configurable anomaly injection.

## Architecture

```
src/generator/
├── models.py          # AnomalyType enum, GeneratorConfig dataclass
├── server_state.py    # Server state & hardware metrics generation
├── service_state.py   # Service state & application metrics generation
├── generator.py       # Main DatacenterGenerator orchestrator
├── config.py          # 6 predefined configurations
└── generate.py        # CLI entry point with argparse
```

## Usage

### CLI

```bash
# Predefined configs
python -m src.generator.generate --config normal
python -m src.generator.generate --config chaos --duration 300

# Custom settings
python -m src.generator.generate \
  --servers 50 \
  --services 10 \
  --anomaly-prob 0.1 \
  --interval 1.0

# Specific anomalies only
python -m src.generator.generate \
  --anomalies cpu_spike memory_leak temperature_high

# Full options
python -m src.generator.generate --help
```

### Programmatic

```python
from src.generator import DatacenterGenerator, CHAOS_CONFIG

generator = DatacenterGenerator(CHAOS_CONFIG)
generator.run(duration_seconds=300)
```

### Custom Config

```python
from src.generator import GeneratorConfig, AnomalyType

config = GeneratorConfig(
    kafka_bootstrap_servers="localhost:9092",
    num_servers=20,
    num_services=10,
    anomaly_probability=0.08,
    enabled_anomalies=[
        AnomalyType.CPU_SPIKE,
        AnomalyType.TEMPERATURE_HIGH
    ],
    zones=["marseille-1", "marseille-2", "marseille-3"]
)
```

## Predefined Configs

| Config | Servers | Services | Anomaly % | Use Case |
|--------|---------|----------|-----------|----------|
| `normal` | 10 | 5 | 2% | Normal operation |
| `chaos` | 15 | 8 | 15% | Stress testing |
| `temperature` | 10 | 5 | 10% | Temperature focus |
| `network` | 12 | 6 | 8% | Network stress |
| `production` | 20 | 12 | 1% | Production-like |
| `dev` | 3 | 2 | 5% | Fast dev testing |

## Anomaly Types

| Type | Affects | Impact |
|------|---------|--------|
| `CPU_SPIKE` | Server | High CPU, temp, power |
| `MEMORY_LEAK` | Server | Growing memory usage |
| `TEMPERATURE_HIGH` | Server | High temp, power surge |
| `POWER_SURGE` | Server | Power consumption spike |
| `NETWORK_SATURATION` | Server | Network traffic maxed |
| `LATENCY_SPIKE` | Service | High response times |
| `ERROR_BURST` | Service | Error rate spike |
| `DISK_IO_BOTTLENECK` | Server | Disk I/O saturated |

## Metrics Generated

### Server Metrics
- CPU usage %
- Memory usage %
- Disk I/O (read/write MB/s)
- Network traffic (RX/TX MB/s)
- CPU temperature °C
- Power consumption watts

### Application Metrics
- Request rate per second
- Response times (p50, p95, p99)
- Error rate %
- Active connections
- Queue depth
- Endpoint path
