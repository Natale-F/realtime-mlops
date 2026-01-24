"""
Redis cache for storing trained anomaly detection models.
"""

import json
from typing import Optional

import redis
import structlog

from .methods.base import ModelComponents
from .models import AnomalyConfig

logger = structlog.get_logger(__name__)


class RedisCache:
    """Redis cache backend for trained models"""

    def __init__(self, config: AnomalyConfig):
        try:
            self.redis = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                password=config.redis_password,
                decode_responses=True,
            )
            self.ttl = config.cache_ttl_seconds
            self.redis.ping()  # Test connection
            logger.info("Redis cache initialized", host=config.redis_host, port=config.redis_port)
        except Exception as e:
            logger.error("Failed to initialize Redis", error=str(e))
            raise

    def save_model(self, model: ModelComponents) -> bool:
        """Save model to Redis"""
        key = self._make_key(model.entity_id, model.metric_name, model.method_name)
        try:
            self.redis.setex(key, self.ttl, json.dumps(model.to_dict()))
            logger.debug("Model saved to Redis", key=key)
            return True
        except Exception as e:
            logger.error("Failed to save model to Redis", key=key, error=str(e))
            return False

    def load_model(
        self, entity_id: str, metric_name: str, method_name: str
    ) -> Optional[ModelComponents]:
        """Load model from Redis"""
        key = self._make_key(entity_id, metric_name, method_name)
        try:
            data = self.redis.get(key)
            if data is None:
                return None

            model_dict = json.loads(data)
            return ModelComponents.from_dict(model_dict)

        except Exception as e:
            logger.error("Failed to load model from Redis", key=key, error=str(e))
            return None

    def _make_key(self, entity_id: str, metric_name: str, method_name: str) -> str:
        """Generate Redis key"""
        return f"anomaly:model:{method_name}:{entity_id}:{metric_name}"
