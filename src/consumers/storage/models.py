"""
Data models and configuration for Kafka consumers.
"""

from dataclasses import dataclass


@dataclass
class ConsumerConfig:
    """Configuration for the storage consumer"""

    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "datacenter-metrics"
    kafka_group_id: str = "storage-consumer-group"
    kafka_auto_offset_reset: str = "earliest"  # 'earliest' or 'latest'

    # PostgreSQL settings (Display here only for educational purposes - In production, use env/secrets variables)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "mlops_db"
    postgres_user: str = "mlops"
    postgres_password: str = "mlops_password"

    # Consumer behavior
    batch_size: int = 100  # Number of messages to batch before committing
    commit_interval_seconds: float = 5.0  # Max time between commits
    max_poll_records: int = 500  # Max records per poll
    enable_auto_commit: bool = False  # Manual commit for better control
