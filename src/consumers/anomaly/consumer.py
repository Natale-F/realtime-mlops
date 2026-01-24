"""
Real-time anomaly detection consumer.

Consumes metrics from Kafka and detects anomalies using pre-trained models.
"""

import json
import time
from datetime import datetime
from typing import Any

import structlog
from kafka import KafkaConsumer

from .cache import RedisCache
from .database import AnomalyDatabase
from .methods import get_method
from .models import AnomalyConfig, AnomalyRecord

logger = structlog.get_logger(__name__)


class AnomalyConsumer:
    """Real-time anomaly detection consumer"""

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

        # Initialize Kafka consumer
        try:
            self.consumer = KafkaConsumer(
                config.kafka_topic,
                bootstrap_servers=config.kafka_bootstrap_servers,
                group_id=config.kafka_group_id,
                auto_offset_reset=config.kafka_auto_offset_reset,
                enable_auto_commit=config.enable_auto_commit,
                max_poll_records=config.max_poll_records,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            logger.info(
                "Kafka consumer initialized",
                bootstrap_servers=config.kafka_bootstrap_servers,
                topic=config.kafka_topic,
                group_id=config.kafka_group_id,
            )
        except Exception as e:
            logger.error("Failed to initialize Kafka consumer", error=str(e))
            raise

        self.stats = {
            "total_consumed": 0,
            "total_analyzed": 0,
            "anomalies_detected": 0,
            "models_not_found": 0,
            "parse_errors": 0,
        }

        logger.info(
            "Consumer initialized",
            method=config.method_name,
            metrics=config.metrics,
        )

    def run(self, duration_seconds: int = None):
        """Run the consumer

        Args:
            duration_seconds: Optional duration in seconds. If None, runs indefinitely.
        """
        logger.info(
            "Starting anomaly detection consumer",
            topic=self.config.kafka_topic,
            duration=duration_seconds if duration_seconds else "indefinite",
        )

        start_time = time.time()
        last_log_time = start_time

        try:
            for message in self.consumer:
                self.stats["total_consumed"] += 1

                # Process message
                self._process_message(message.value)

                # Log stats every 30 seconds
                elapsed = time.time() - start_time
                if time.time() - last_log_time >= 30:
                    rate = self.stats["total_consumed"] / elapsed if elapsed > 0 else 0
                    detection_rate = (
                        self.stats["anomalies_detected"] / self.stats["total_analyzed"] * 100
                        if self.stats["total_analyzed"] > 0
                        else 0
                    )

                    logger.info(
                        "Consumer stats",
                        total_consumed=self.stats["total_consumed"],
                        total_analyzed=self.stats["total_analyzed"],
                        anomalies_detected=self.stats["anomalies_detected"],
                        detection_rate_percent=round(detection_rate, 2),
                        models_not_found=self.stats["models_not_found"],
                        parse_errors=self.stats["parse_errors"],
                        rate_per_sec=round(rate, 1),
                        elapsed_sec=round(elapsed, 1),
                    )
                    last_log_time = time.time()

                # Check duration limit
                if duration_seconds and elapsed >= duration_seconds:
                    logger.info("Duration limit reached", duration_seconds=duration_seconds)
                    break

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping consumer")

        except Exception as e:
            logger.error("Consumer error", error=str(e), exc_info=True)
            raise

        finally:
            self.consumer.close()
            self.db.close()

            elapsed = time.time() - start_time
            rate = self.stats["total_consumed"] / elapsed if elapsed > 0 else 0

            logger.info(
                "Consumer stopped",
                total_consumed=self.stats["total_consumed"],
                total_analyzed=self.stats["total_analyzed"],
                anomalies_detected=self.stats["anomalies_detected"],
                elapsed_sec=round(elapsed, 1),
                avg_rate_per_sec=round(rate, 1),
            )

    def _process_message(self, message: dict[str, Any]):
        """Process a single Kafka message"""
        try:
            msg_type = message.get("type")

            # Only process server metrics for now
            if msg_type != "server_metric":
                return

            entity_id = message.get("server_id")
            timestamp = datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00"))

            # Check each configured metric
            for metric_name in self.config.metrics:
                if metric_name not in message:
                    continue

                self._detect_anomaly(
                    entity_id=entity_id,
                    metric_name=metric_name,
                    value=message[metric_name],
                    timestamp=timestamp,
                )

        except Exception as e:
            logger.error("Failed to process message", error=str(e), message=message)
            self.stats["parse_errors"] += 1

    def _detect_anomaly(self, entity_id: str, metric_name: str, value: float, timestamp: datetime):
        """Detect anomaly for a single metric value"""
        self.stats["total_analyzed"] += 1

        # Load model from cache
        model = self.cache.load_model(entity_id, metric_name, self.method.name)

        if model is None:
            self.stats["models_not_found"] += 1
            return

        # Predict
        result = self.method.predict(value, timestamp, model)

        # If anomaly detected, save it
        if result.is_anomaly:
            self.stats["anomalies_detected"] += 1

            anomaly = AnomalyRecord(
                timestamp=timestamp.isoformat(),
                entity_type="server",
                entity_id=entity_id,
                metric_name=metric_name,
                anomaly_type=self.method.name,
                severity=AnomalyRecord.calculate_severity(result.score),
                anomaly_score=result.score,
                actual_value=result.actual_value,
                expected_value=result.expected_value,
                details=result.details,
                detection_method=self.method.name,
            )

            self.db.insert_anomaly(anomaly)

            logger.info(
                "Anomaly detected",
                entity_id=entity_id,
                metric=metric_name,
                severity=anomaly.severity,
                score=round(result.score, 3),
                actual=round(result.actual_value, 2),
                expected=round(result.expected_value, 2) if result.expected_value else None,
                z_score=result.details.get("z_score"),
            )
