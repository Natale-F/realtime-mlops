"""
Predefined configurations for different operational scenarios.
"""

from .models import AnomalyType, GeneratorConfig

# Normal operation (low anomaly rate)
NORMAL_CONFIG = GeneratorConfig(
    num_servers=100,
    num_services=25,
    anomaly_probability=0.002,  # 0.2%
    event_interval_seconds=5.0,
)


# Chaos mode (high anomaly rate, all types)
CHAOS_CONFIG = GeneratorConfig(
    num_servers=150,
    num_services=40,
    anomaly_probability=0.08,  # 8%
    event_interval_seconds=1.0,
)


# Focus on temperature issues only
TEMPERATURE_FOCUS_CONFIG = GeneratorConfig(
    num_servers=80,
    num_services=20,
    anomaly_probability=0.01,
    enabled_anomalies=[AnomalyType.TEMPERATURE_HIGH, AnomalyType.CPU_SPIKE],
    event_interval_seconds=5.0,
)


# Network stress testing
NETWORK_STRESS_CONFIG = GeneratorConfig(
    num_servers=120,
    num_services=30,
    anomaly_probability=0.03,
    enabled_anomalies=[
        AnomalyType.NETWORK_SATURATION,
        AnomalyType.LATENCY_SPIKE,
        AnomalyType.ERROR_BURST,
    ],
    event_interval_seconds=0.8,
)


# Production-like (minimal anomalies)
PRODUCTION_CONFIG = GeneratorConfig(
    num_servers=300,
    num_services=60,
    anomaly_probability=0.001,  # 1%
    event_interval_seconds=10.0,
)


# Development/Testing (fast and small)
DEV_CONFIG = GeneratorConfig(
    num_servers=5, num_services=3, anomaly_probability=0.02, event_interval_seconds=2.0
)
