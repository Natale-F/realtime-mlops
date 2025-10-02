"""
PostgreSQL operations specific to the storage consumer.
Handles batch insertions for server and application metrics.
"""

from typing import Any

import psycopg2.extras
import structlog

from src.core.database import PostgresConnection

from .models import ConsumerConfig

logger = structlog.get_logger(__name__)


class StorageDatabase(PostgresConnection):
    """Database operations for storage consumer with batch insert capabilities"""

    def __init__(self, config: ConsumerConfig):
        super().__init__(
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_database,
            user=config.postgres_user,
            password=config.postgres_password,
        )

    def insert_batch_server_metrics(self, metrics: list[dict[str, Any]]) -> int:
        """Batch insert server metrics for better performance"""
        if not metrics:
            return 0

        query = """
            INSERT INTO server_metrics (
                timestamp, server_id, cpu_usage_percent, memory_usage_percent,
                memory_available_gb, disk_usage_percent, disk_read_mbps, disk_write_mbps,
                network_rx_mbps, network_tx_mbps, cpu_temperature_celsius,
                power_consumption_watts, rack_id, datacenter_zone
            ) VALUES (
                %(timestamp)s, %(server_id)s, %(cpu_usage_percent)s, %(memory_usage_percent)s,
                %(memory_available_gb)s, %(disk_usage_percent)s, %(disk_read_mbps)s, %(disk_write_mbps)s,
                %(network_rx_mbps)s, %(network_tx_mbps)s, %(cpu_temperature_celsius)s,
                %(power_consumption_watts)s, %(rack_id)s, %(datacenter_zone)s
            )
        """
        inserted = 0
        try:
            with self.get_cursor() as cursor:
                psycopg2.extras.execute_batch(cursor, query, metrics, page_size=100)
                inserted = len(metrics)
        except Exception as e:
            logger.error("Failed to batch insert server metrics", count=len(metrics), error=str(e))
        return inserted

    def insert_batch_application_metrics(self, metrics: list[dict[str, Any]]) -> int:
        """Batch insert application metrics for better performance"""
        if not metrics:
            return 0

        query = """
            INSERT INTO application_metrics (
                timestamp, service_name, request_rate_per_sec,
                response_time_p50_ms, response_time_p95_ms, response_time_p99_ms,
                error_rate_percent, error_count, active_connections,
                queue_depth, server_id, endpoint
            ) VALUES (
                %(timestamp)s, %(service_name)s, %(request_rate_per_sec)s,
                %(response_time_p50_ms)s, %(response_time_p95_ms)s, %(response_time_p99_ms)s,
                %(error_rate_percent)s, %(error_count)s, %(active_connections)s,
                %(queue_depth)s, %(server_id)s, %(endpoint)s
            )
        """
        inserted = 0
        try:
            with self.get_cursor() as cursor:
                psycopg2.extras.execute_batch(cursor, query, metrics, page_size=100)
                inserted = len(metrics)
        except Exception as e:
            logger.error(
                "Failed to batch insert application metrics", count=len(metrics), error=str(e)
            )
        return inserted
