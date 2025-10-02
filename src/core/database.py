"""
Generic PostgreSQL connection management.
Reusable across all consumers and services.
"""

from contextlib import contextmanager
from typing import Any

import psycopg2
import structlog

logger = structlog.get_logger(__name__)


class PostgresConnection:
    """Base class for PostgreSQL connection management"""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        self._connect()

    def _connect(self):
        """Establish connection to PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=10,
            )
            logger.info(
                "PostgreSQL connection established",
                host=self.host,
                database=self.database,
            )
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor with automatic commit/rollback"""
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

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> bool:
        """Execute a single query with parameters"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params or {})
            return True
        except Exception as e:
            logger.error("Query execution failed", error=str(e), query=query)
            return False

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
