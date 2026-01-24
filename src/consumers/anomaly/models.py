"""
Data models and configuration for anomaly detection system.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnomalyConfig:
    """Configuration for the anomaly detection system"""

    method_name: str = "stl_zscore"  

    # Method-specific configuration
    method_config: dict = field(
        default_factory=lambda: {
            "seasonal_period": 288,  # 24h with 5min aggregation (24*60/5 = 288)
            "trend_period": 577,  # ~2 days (2*288 = 576, +1 for odd), must be > seasonal_period
            "z_score_threshold": 3.0,  
            "min_points": 2016,  # 14 days × 288 points/day = 4032, on prend la moitié minimum
        }
    )

    history_days: int = 14  
    aggregation_interval: str = "5min"  

    metrics: list[str] = field(
        default_factory=lambda: [
            "cpu_usage_percent",
            "memory_usage_percent",
            "cpu_temperature_celsius",
        ]
    )

    training_frequency_minutes: int = 10  
    auto_discover_entities: bool = True  

    # Redis cache settings
    cache_ttl_seconds: int = 900 

    # PostgreSQL settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "mlops_db"
    postgres_user: str = "mlops"
    postgres_password: str = "mlops_password"

    # Kafka settings (for real-time consumer)
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "datacenter-metrics"
    kafka_group_id: str = "anomaly-detection-consumer-group"
    kafka_auto_offset_reset: str = "latest"

    # Consumer behavior
    batch_size: int = 50
    commit_interval_seconds: float = 10.0
    max_poll_records: int = 500
    enable_auto_commit: bool = False

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None


@dataclass
class AnomalyRecord:
    """Represents a detected anomaly for database insertion"""

    timestamp: str  
    entity_type: str  
    entity_id: str  
    metric_name: str  
    anomaly_type: str  
    severity: str  
    anomaly_score: float  
    actual_value: float
    expected_value: Optional[float]
    details: dict  
    detection_method: str  

    def to_db_dict(self) -> dict:
        """Convert to dict for database insertion"""
        import json

        return {
            "timestamp": self.timestamp,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "anomaly_type": f"{self.detection_method}_{self.metric_name}",
            "severity": self.severity,
            "anomaly_score": self.anomaly_score,
            "details": json.dumps(
                {
                    "metric_name": self.metric_name,
                    "actual_value": self.actual_value,
                    "expected_value": self.expected_value,
                    **self.details,
                }
            ),
        }

    @staticmethod
    def calculate_severity(score: float) -> str:
        """Calculate severity level from anomaly score"""
        if score >= 0.8:
            return "critical"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
