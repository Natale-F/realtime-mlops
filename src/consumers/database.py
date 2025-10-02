"""
PostgreSQL database connection and operations.
"""

from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras
import structlog

from .models import ConsumerConfig

logger = structlog.get_logger(__name__)


class DatabaseConnection:
    """Manages PostgreSQL connection and data insertion"""

    def __init__(self, config: ConsumerConfig):
        self.config = config
        self.connection = None
        self._connect()

    def _connect(self):
        """Establish connection to PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_database,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
                connect_timeout=10,
            )
            logger.info(
                "PostgreSQL connection established",
                host=self.config.postgres_host,
                database=self.config.postgres_database,
            )
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error("Database operation failed", error=str(e))
            raise
        finally:
            cursor.close()

    def insert_server_metric(self, metric: dict[str, Any]) -> bool:
        """Insert a server metric into the database

        Note: fan_speed_rpm is optional and will be NULL if not provided by the generator
        """
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
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, metric)
            return True
        except Exception as e:
            logger.error(
                "Failed to insert server metric",
                server_id=metric.get("server_id"),
                error=str(e),
            )
            return False

    def insert_application_metric(self, metric: dict[str, Any]) -> bool:
        """Insert an application metric into the database"""
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
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, metric)
            return True
        except Exception as e:
            logger.error(
                "Failed to insert application metric",
                service_name=metric.get("service_name"),
                error=str(e),
            )
            return False

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

    def check_health(self) -> bool:
        """Check if database connection is healthy"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0] == 1
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")
