"""
Server state management and metrics generation.
"""

import random
from datetime import UTC, datetime
from typing import Any

from .models import AnomalyType


class ServerState:
    """Tracks the state of a server over time for realistic evolution"""

    def __init__(self, server_id: str, rack_id: str, zone: str):
        self.server_id = server_id
        self.rack_id = rack_id
        self.zone = zone

        # Base values (these evolve slowly)
        self.base_cpu = random.uniform(20, 40)
        self.base_memory = random.uniform(30, 50)
        self.base_disk_usage = random.uniform(40, 70)
        self.base_temp = random.uniform(45, 55)
        self.base_power = random.uniform(200, 300)

        # Current anomaly state
        self.active_anomaly: AnomalyType | None = None
        self.anomaly_duration: int = 0

    def generate_metrics(
        self, inject_anomaly: AnomalyType | None = None, timestamp: datetime | None = None
    ) -> dict[str, Any]:
        """Generate realistic server metrics with optional anomaly injection
        
        Args:
            inject_anomaly: Optional anomaly type to inject
            timestamp: Optional custom timestamp (for backfill mode)
        """

        # Handle anomaly injection
        if inject_anomaly:
            self.active_anomaly = inject_anomaly
            self.anomaly_duration = random.randint(30, 120)  # anomaly lasts 30-120 seconds

        # Apply anomaly effects
        cpu_mult = 1.0
        mem_mult = 1.0
        temp_mult = 1.0
        power_mult = 1.0
        network_mult = 1.0
        disk_mult = 1.0

        if self.active_anomaly:
            if self.active_anomaly == AnomalyType.CPU_SPIKE:
                cpu_mult = random.uniform(2.5, 4.0)
                temp_mult = random.uniform(1.3, 1.6)
                power_mult = random.uniform(1.4, 1.8)
            elif self.active_anomaly == AnomalyType.MEMORY_LEAK:
                mem_mult = random.uniform(1.5, 2.2)
            elif self.active_anomaly == AnomalyType.TEMPERATURE_HIGH:
                temp_mult = random.uniform(1.5, 1.9)
                power_mult = random.uniform(1.2, 1.4)
            elif self.active_anomaly == AnomalyType.POWER_SURGE:
                power_mult = random.uniform(2.0, 3.0)
                cpu_mult = random.uniform(1.3, 1.6)
            elif self.active_anomaly == AnomalyType.NETWORK_SATURATION:
                network_mult = random.uniform(3.0, 5.0)
            elif self.active_anomaly == AnomalyType.DISK_IO_BOTTLENECK:
                disk_mult = random.uniform(3.0, 6.0)

            self.anomaly_duration -= 1
            if self.anomaly_duration <= 0:
                self.active_anomaly = None

        # Add natural variation
        cpu_variation = random.uniform(-5, 5)
        mem_variation = random.uniform(-2, 2)
        temp_variation = random.uniform(-2, 2)

        # Calculate final values with bounds checking
        cpu_usage = min(99.9, max(0.1, (self.base_cpu + cpu_variation) * cpu_mult))
        memory_usage = min(99.9, max(5.0, (self.base_memory + mem_variation) * mem_mult))
        cpu_temp = min(95.0, max(30.0, (self.base_temp + temp_variation) * temp_mult))
        power = max(50.0, self.base_power * power_mult)

        # Correlations: high CPU → more network and disk I/O
        network_base = cpu_usage / 10  # rough correlation
        disk_base = cpu_usage / 15

        return {
            "type": "server_metric",
            "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
            "server_id": self.server_id,
            "rack_id": self.rack_id,
            "datacenter_zone": self.zone,
            "cpu_usage_percent": round(cpu_usage, 2),
            "memory_usage_percent": round(memory_usage, 2),
            "memory_available_gb": round(random.uniform(8, 64), 2),
            "disk_usage_percent": round(self.base_disk_usage + random.uniform(-2, 2), 2),
            "disk_read_mbps": round(disk_base * disk_mult * random.uniform(5, 20), 2),
            "disk_write_mbps": round(disk_base * disk_mult * random.uniform(3, 15), 2),
            "network_rx_mbps": round(network_base * network_mult * random.uniform(10, 100), 2),
            "network_tx_mbps": round(network_base * network_mult * random.uniform(10, 100), 2),
            "cpu_temperature_celsius": round(cpu_temp, 1),
            "power_consumption_watts": round(power, 1),
        }
