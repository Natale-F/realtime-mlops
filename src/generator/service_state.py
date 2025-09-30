"""
Service state management and application metrics generation.
"""

import random
from datetime import UTC, datetime
from typing import Any

from .models import AnomalyType


class ServiceState:
    """Tracks the state of an application service"""

    def __init__(self, service_name: str, server_id: str):
        self.service_name = service_name
        self.server_id = server_id

        # Base values
        self.base_request_rate = random.uniform(100, 1000)
        self.base_latency = random.uniform(10, 50)
        self.base_error_rate = random.uniform(0.1, 1.0)

        # Active anomaly
        self.active_anomaly: AnomalyType | None = None
        self.anomaly_duration: int = 0

    def generate_metrics(self, inject_anomaly: AnomalyType | None = None) -> dict[str, Any]:
        """Generate realistic application metrics"""

        if inject_anomaly:
            self.active_anomaly = inject_anomaly
            self.anomaly_duration = random.randint(20, 90)

        latency_mult = 1.0
        error_mult = 1.0

        if self.active_anomaly:
            if self.active_anomaly == AnomalyType.LATENCY_SPIKE:
                latency_mult = random.uniform(5.0, 15.0)
            elif self.active_anomaly == AnomalyType.ERROR_BURST:
                error_mult = random.uniform(10.0, 50.0)

            self.anomaly_duration -= 1
            if self.anomaly_duration <= 0:
                self.active_anomaly = None

        # Time-based pattern (more traffic during "business hours")
        hour = datetime.now().hour
        time_multiplier = 1.0 + 0.5 * (1 if 9 <= hour <= 18 else 0)

        request_rate = self.base_request_rate * time_multiplier * random.uniform(0.8, 1.2)
        p50_latency = self.base_latency * latency_mult * random.uniform(0.9, 1.1)
        p95_latency = p50_latency * random.uniform(2.0, 3.5)
        p99_latency = p95_latency * random.uniform(1.5, 2.5)
        error_rate = min(50.0, self.base_error_rate * error_mult * random.uniform(0.8, 1.5))

        return {
            "type": "application_metric",
            "timestamp": datetime.now(UTC).isoformat(),
            "service_name": self.service_name,
            "server_id": self.server_id,
            "request_rate_per_sec": round(request_rate, 2),
            "response_time_p50_ms": round(p50_latency, 2),
            "response_time_p95_ms": round(p95_latency, 2),
            "response_time_p99_ms": round(p99_latency, 2),
            "error_rate_percent": round(error_rate, 3),
            "error_count": int(request_rate * error_rate / 100),
            "active_connections": random.randint(50, 500),
            "queue_depth": random.randint(0, 100),
            "endpoint": random.choice(["/api/users", "/api/products", "/api/orders", "/health"]),
        }
