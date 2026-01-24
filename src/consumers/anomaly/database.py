"""
PostgreSQL operations for anomaly detection system.

Handles:
- Querying historical metrics for training
- Inserting detected anomalies
- Storing/loading trained models (if using PostgreSQL as cache)
"""


import pandas as pd
import structlog

from src.core.database import PostgresConnection

from .models import AnomalyConfig, AnomalyRecord

logger = structlog.get_logger(__name__)


class AnomalyDatabase(PostgresConnection):
    """Database operations for anomaly detection"""

    def __init__(self, config: AnomalyConfig):
        super().__init__(
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_database,
            user=config.postgres_user,
            password=config.postgres_password,
        )
        self.config = config

    def query_historical_metrics(
        self,
        entity_id: str,
        metric_name: str,
        days: int,
        aggregation: str = "5min",
    ) -> pd.DataFrame:
        """Query historical metrics for training

        Args:
            entity_id: Server ID or service name
            metric_name: Name of the metric
            days: Number of days of history
            aggregation: Time bucket aggregation (e.g., '5min')

        Returns:
            DataFrame with columns ['timestamp', 'value']
        """
        # Convert aggregation string to PostgreSQL interval
        interval_map = {
            "1min": "1 minute",
            "5min": "5 minutes",
            "10min": "10 minutes",
            "15min": "15 minutes",
            "1hour": "1 hour",
        }
        pg_interval = interval_map.get(aggregation, "5 minutes")

        query = f"""
            SELECT
                time_bucket('{pg_interval}', timestamp) as timestamp,
                AVG({metric_name}) as value
            FROM server_metrics
            WHERE server_id = %s
              AND timestamp > NOW() - INTERVAL '{days} days'
              AND {metric_name} IS NOT NULL
            GROUP BY time_bucket('{pg_interval}', timestamp)
            ORDER BY timestamp
        """

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (entity_id,))
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                df = pd.DataFrame(rows, columns=columns)
                logger.debug(
                    "Queried historical metrics",
                    entity_id=entity_id,
                    metric_name=metric_name,
                    days=days,
                    rows=len(df),
                )
                return df

        except Exception as e:
            logger.error(
                "Failed to query historical metrics",
                entity_id=entity_id,
                metric_name=metric_name,
                error=str(e),
            )
            return pd.DataFrame(columns=["timestamp", "value"])

    def discover_entities(self) -> list[str]:
        """Discover all unique server IDs from the database

        Returns:
            List of server IDs
        """
        query = """
            SELECT DISTINCT server_id
            FROM server_metrics
            ORDER BY server_id
        """

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query)
                entities = [row[0] for row in cursor.fetchall()]
                logger.info("Discovered entities", count=len(entities))
                return entities
        except Exception as e:
            logger.error("Failed to discover entities", error=str(e))
            return []

    def insert_anomaly(self, anomaly: AnomalyRecord) -> bool:
        """Insert a detected anomaly

        Args:
            anomaly: AnomalyRecord to insert

        Returns:
            True if successful, False otherwise
        """
        query = """
            INSERT INTO anomalies (
                timestamp, entity_type, entity_id, anomaly_type,
                severity, anomaly_score, details
            ) VALUES (
                %(timestamp)s, %(entity_type)s, %(entity_id)s, %(anomaly_type)s,
                %(severity)s, %(anomaly_score)s, %(details)s
            )
        """

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, anomaly.to_db_dict())
                logger.debug(
                    "Anomaly inserted",
                    entity_id=anomaly.entity_id,
                    metric=anomaly.metric_name,
                    severity=anomaly.severity,
                )
                return True
        except Exception as e:
            logger.error(
                "Failed to insert anomaly",
                entity_id=anomaly.entity_id,
                metric=anomaly.metric_name,
                error=str(e),
            )
            return False

    # ========================================
    # Model storage (PostgreSQL as cache)
    # ========================================

    def save_model(self, model_data: dict) -> bool:
        """Save trained model components to PostgreSQL

        Args:
            model_data: Dictionary with model components

        Returns:
            True if successful
        """
        query = """
            INSERT INTO anomaly_models (
                entity_id, metric_name, method_name,
                components, metadata, trained_at
            ) VALUES (
                %(entity_id)s, %(metric_name)s, %(method_name)s,
                %(components)s, %(metadata)s, %(trained_at)s
            )
            ON CONFLICT (entity_id, metric_name, method_name)
            DO UPDATE SET
                components = EXCLUDED.components,
                metadata = EXCLUDED.metadata,
                trained_at = EXCLUDED.trained_at
        """

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, model_data)
                logger.debug(
                    "Model saved",
                    entity_id=model_data["entity_id"],
                    metric=model_data["metric_name"],
                    method=model_data["method_name"],
                )
                return True
        except Exception as e:
            logger.error("Failed to save model", error=str(e), model=model_data)
            return False

    def load_model(self, entity_id: str, metric_name: str, method_name: str) -> dict | None:
        """Load trained model from PostgreSQL

        Args:
            entity_id: Entity identifier
            metric_name: Metric name
            method_name: Detection method name

        Returns:
            Model data dict or None if not found
        """
        query = """
            SELECT entity_id, metric_name, method_name,
                   components, metadata, trained_at
            FROM anomaly_models
            WHERE entity_id = %s
              AND metric_name = %s
              AND method_name = %s
            ORDER BY trained_at DESC
            LIMIT 1
        """

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (entity_id, metric_name, method_name))
                row = cursor.fetchone()

                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row, strict=False))
                return None

        except Exception as e:
            logger.error(
                "Failed to load model",
                entity_id=entity_id,
                metric=metric_name,
                method=method_name,
                error=str(e),
            )
            return None

    def ensure_model_table_exists(self):
        """Create anomaly_models table if it doesn't exist"""
        query = """
            CREATE TABLE IF NOT EXISTS anomaly_models (
                id SERIAL PRIMARY KEY,
                entity_id VARCHAR(100) NOT NULL,
                metric_name VARCHAR(50) NOT NULL,
                method_name VARCHAR(50) NOT NULL,
                components JSONB NOT NULL,
                metadata JSONB,
                trained_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(entity_id, metric_name, method_name)
            );

            CREATE INDEX IF NOT EXISTS idx_anomaly_models_lookup
            ON anomaly_models(entity_id, metric_name, method_name);
        """

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query)
                logger.info("Ensured anomaly_models table exists")
        except Exception as e:
            logger.error("Failed to create anomaly_models table", error=str(e))
