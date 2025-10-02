"""
Kafka consumers for datacenter metrics processing.
"""

# Storage consumer (Kafka → PostgreSQL)
from .storage import ConsumerConfig, StorageConsumer

__all__ = ["StorageConsumer", "ConsumerConfig"]
