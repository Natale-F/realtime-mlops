"""
Data models and enums for the datacenter event generator.
"""

from dataclasses import dataclass
from enum import Enum


class AnomalyType(Enum):
    """Types of anomalies that can be injected"""

    CPU_SPIKE = "cpu_spike"
    MEMORY_LEAK = "memory_leak"
    TEMPERATURE_HIGH = "temperature_high"
    POWER_SURGE = "power_surge"
    NETWORK_SATURATION = "network_saturation"
    LATENCY_SPIKE = "latency_spike"
    ERROR_BURST = "error_burst"
    DISK_IO_BOTTLENECK = "disk_io_bottleneck"


@dataclass
class GeneratorConfig:
    """Configuration for the event generator"""

    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "datacenter-metrics"

    # Generation settings
    num_servers: int = 10
    num_services: int = 5
    event_interval_seconds: float = 1.0

    # Anomaly settings
    anomaly_probability: float = 0.05  # 5% chance of anomaly per event
    enabled_anomalies: list[AnomalyType] | None = None

    # Datacenter topology
    racks: list[str] | None = None
    zones: list[str] | None = None

    def __post_init__(self):
        if self.enabled_anomalies is None:
            self.enabled_anomalies = list(AnomalyType)
        if self.racks is None:
            self.racks = [f"R{i:02d}" for i in range(1, 6)]  # R01 to R05
        if self.zones is None:
            self.zones = ["marseille-1", "marseille-2"]
