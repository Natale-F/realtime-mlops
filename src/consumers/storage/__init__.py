"""
Storage Consumer - Kafka to PostgreSQL ingestion.
"""

from .consumer import StorageConsumer
from .models import ConsumerConfig

__all__ = ["StorageConsumer", "ConsumerConfig"]
