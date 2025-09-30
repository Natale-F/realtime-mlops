"""
Predefined configurations for different operational scenarios.
"""

from .models import AnomalyType, GeneratorConfig

# Normal operation (low anomaly rate)
NORMAL_CONFIG = GeneratorConfig(
    num_servers=10,
    num_services=5,
    anomaly_probability=0.02,  # 2%
    event_interval_seconds=1.0,
)


# Chaos mode (high anomaly rate, all types)
CHAOS_CONFIG = GeneratorConfig(
    num_servers=15,
    num_services=8,
    anomaly_probability=0.15,  # 15%
    event_interval_seconds=0.5,
)


# Focus on temperature issues only
TEMPERATURE_FOCUS_CONFIG = GeneratorConfig(
    num_servers=10,
    num_services=5,
    anomaly_probability=0.10,
    enabled_anomalies=[AnomalyType.TEMPERATURE_HIGH, AnomalyType.CPU_SPIKE],
    event_interval_seconds=1.0,
)


# Network stress testing
NETWORK_STRESS_CONFIG = GeneratorConfig(
    num_servers=12,
    num_services=6,
    anomaly_probability=0.08,
    enabled_anomalies=[
        AnomalyType.NETWORK_SATURATION,
        AnomalyType.LATENCY_SPIKE,
        AnomalyType.ERROR_BURST,
    ],
    event_interval_seconds=0.8,
)


# Production-like (minimal anomalies)
PRODUCTION_CONFIG = GeneratorConfig(
    num_servers=20,
    num_services=12,
    anomaly_probability=0.01,  # 1%
    event_interval_seconds=1.0,
)


# Development/Testing (fast and small)
DEV_CONFIG = GeneratorConfig(
    num_servers=3, num_services=2, anomaly_probability=0.05, event_interval_seconds=2.0
)
