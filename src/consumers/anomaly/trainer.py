"""
Batch trainer for anomaly detection models.

Periodically trains models on historical data and saves them to cache.
"""

import time

import structlog

from .cache import RedisCache
from .database import AnomalyDatabase
from .methods import get_method
from .models import AnomalyConfig

logger = structlog.get_logger(__name__)


class AnomalyTrainer:
    """Trains anomaly detection models on historical data"""

    def __init__(self, config: AnomalyConfig):
        self.config = config

        # Initialize database
        self.db = AnomalyDatabase(config)
        if not self.db.check_health():
            raise RuntimeError("Database health check failed")

        # Initialize Redis cache
        self.cache = RedisCache(config)

        # Initialize detection method
        self.method = get_method(config.method_name, config.method_config)

        logger.info(
            "Trainer initialized",
            method=config.method_name,
            cache=type(self.cache).__name__,
            history_days=config.history_days,
            aggregation=config.aggregation_interval,
        )

    def train_all(self) -> dict:
        """Train models for all entities and metrics

        Returns:
            Dictionary with training statistics
        """
        logger.info("Starting training for all entities")

        stats = {
            "total_entities": 0,
            "total_models": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
        }

        start_time = time.time()

        # Discover entities
        entities = self.db.discover_entities() if self.config.auto_discover_entities else []

        stats["total_entities"] = len(entities)

        # Train for each entity and metric
        for entity_id in entities:
            for metric_name in self.config.metrics:
                stats["total_models"] += 1

                success = self.train_single(entity_id, metric_name)

                if success:
                    stats["successful"] += 1
                elif success is None:
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1

        elapsed = time.time() - start_time

        logger.info(
            "Training completed",
            entities=stats["total_entities"],
            models=stats["total_models"],
            successful=stats["successful"],
            failed=stats["failed"],
            skipped=stats["skipped"],
            elapsed_sec=round(elapsed, 1),
        )

        return stats

    def train_single(self, entity_id: str, metric_name: str) -> bool | None:
        """Train a single model for an entity-metric pair

        Args:
            entity_id: Entity identifier (server_id)
            metric_name: Metric to train on

        Returns:
            True if successful, False if failed, None if skipped
        """
        logger.debug("Training model", entity_id=entity_id, metric=metric_name)

        try:
            # 1. Query historical data
            df = self.db.query_historical_metrics(
                entity_id=entity_id,
                metric_name=metric_name,
                days=self.config.history_days,
                aggregation=self.config.aggregation_interval,
            )

            # 2. Check if enough data
            min_required = self.config.method_config.get("min_points", 100)
            if len(df) < min_required:
                logger.debug(
                    "Insufficient data, skipping",
                    entity_id=entity_id,
                    metric=metric_name,
                    points=len(df),
                    required=min_required,
                )
                return None

            # 3. Fit model
            model = self.method.fit(df, entity_id, metric_name)

            # 4. Save to cache
            success = self.cache.save_model(model)

            if success:
                logger.info(
                    "Model trained and saved",
                    entity_id=entity_id,
                    metric=metric_name,
                    method=self.method.name,
                )
            else:
                logger.warning(
                    "Model trained but failed to save",
                    entity_id=entity_id,
                    metric=metric_name,
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to train model",
                entity_id=entity_id,
                metric=metric_name,
                error=str(e),
                exc_info=True,
            )
            return False

    def close(self):
        """Clean up resources"""
        self.db.close()
        logger.info("Trainer closed")
