"""
Storage consumer that ingests Kafka events into PostgreSQL.
"""

import json
import time
from typing import Any

import structlog
from kafka import KafkaConsumer

from .database import StorageDatabase
from .models import ConsumerConfig

logger = structlog.get_logger(__name__)


class StorageConsumer:
    """Consumes datacenter metrics from Kafka and stores them in PostgreSQL"""

    def __init__(self, config: ConsumerConfig):
        self.config = config
        logger.info("Initializing storage consumer", config=config)

        self.db = StorageDatabase(config)

        if not self.db.check_health():
            raise RuntimeError("Database health check failed")

        try:
            self.consumer = KafkaConsumer(
                config.kafka_topic,
                bootstrap_servers=config.kafka_bootstrap_servers,
                group_id=config.kafka_group_id,
                auto_offset_reset=config.kafka_auto_offset_reset,
                enable_auto_commit=config.enable_auto_commit,
                max_poll_records=config.max_poll_records,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                # No consumer_timeout for continuous consumption
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

        # Batching state
        self.server_metrics_batch: list[dict[str, Any]] = []
        self.application_metrics_batch: list[dict[str, Any]] = []
        self.last_commit_time = time.time()

        self.stats = {
            "total_consumed": 0,
            "server_metrics": 0,
            "application_metrics": 0,
            "unknown_type": 0,
            "parse_errors": 0,
            "insert_errors": 0,
        }

    def _parse_and_route_message(self, message: dict[str, Any]) -> bool:
        """Parse message and add to appropriate batch"""
        try:
            msg_type = message.get("type")

            if msg_type == "server_metric":
                self.server_metrics_batch.append(message)
                self.stats["server_metrics"] += 1
                return True

            elif msg_type == "application_metric":
                self.application_metrics_batch.append(message)
                self.stats["application_metrics"] += 1
                return True

            else:
                logger.warning("Unknown message type", type=msg_type, message=message)
                self.stats["unknown_type"] += 1
                return False

        except Exception as e:
            logger.error("Failed to parse message", error=str(e), message=message)
            self.stats["parse_errors"] += 1
            return False

    def _flush_batches(self):
        """Flush accumulated batches to database"""
        inserted_server = 0
        inserted_app = 0

        if self.server_metrics_batch:
            inserted_server = self.db.insert_batch_server_metrics(self.server_metrics_batch)
            if inserted_server < len(self.server_metrics_batch):
                self.stats["insert_errors"] += len(self.server_metrics_batch) - inserted_server
            self.server_metrics_batch.clear()

        if self.application_metrics_batch:
            inserted_app = self.db.insert_batch_application_metrics(self.application_metrics_batch)
            if inserted_app < len(self.application_metrics_batch):
                self.stats["insert_errors"] += len(self.application_metrics_batch) - inserted_app
            self.application_metrics_batch.clear()

        if inserted_server > 0 or inserted_app > 0:
            logger.debug(
                "Batch flushed",
                server_metrics=inserted_server,
                application_metrics=inserted_app,
            )

        return inserted_server + inserted_app

    def _should_commit(self) -> bool:
        """Check if we should commit based on batch size or time"""
        batch_size = len(self.server_metrics_batch) + len(self.application_metrics_batch)
        time_elapsed = time.time() - self.last_commit_time

        return (
            batch_size >= self.config.batch_size
            or time_elapsed >= self.config.commit_interval_seconds
        )

    def run(self, duration_seconds: int = None):
        """Run the consumer continuously or for a specified duration

        Args:
            duration_seconds: Optional duration in seconds. If None, runs indefinitely.
        """
        logger.info(
            "Starting storage consumer",
            topic=self.config.kafka_topic,
            duration=duration_seconds if duration_seconds else "indefinite",
        )

        start_time = time.time()
        last_log_time = start_time

        try:
            for message in self.consumer:
                self.stats["total_consumed"] += 1

                self._parse_and_route_message(message.value)

                if self._should_commit():
                    self._flush_batches()
                    if not self.config.enable_auto_commit:
                        self.consumer.commit()
                    self.last_commit_time = time.time()

                # Log stats every 10 seconds
                elapsed = time.time() - start_time
                if time.time() - last_log_time >= 10:
                    rate = self.stats["total_consumed"] / elapsed if elapsed > 0 else 0
                    logger.info(
                        "Consumer stats",
                        total_consumed=self.stats["total_consumed"],
                        server_metrics=self.stats["server_metrics"],
                        application_metrics=self.stats["application_metrics"],
                        parse_errors=self.stats["parse_errors"],
                        insert_errors=self.stats["insert_errors"],
                        rate_per_sec=round(rate, 1),
                        elapsed_sec=round(elapsed, 1),
                    )
                    last_log_time = time.time()

                if duration_seconds and elapsed >= duration_seconds:
                    logger.info("Duration limit reached", duration_seconds=duration_seconds)
                    break

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping consumer")

        except Exception as e:
            logger.error("Consumer error", error=str(e), exc_info=True)
            raise

        finally:
            logger.info("Flushing remaining batches")
            self._flush_batches()
            if not self.config.enable_auto_commit:
                self.consumer.commit()

            elapsed = time.time() - start_time
            rate = self.stats["total_consumed"] / elapsed if elapsed > 0 else 0

            self.consumer.close()
            self.db.close()

            logger.info(
                "Consumer stopped",
                total_consumed=self.stats["total_consumed"],
                server_metrics=self.stats["server_metrics"],
                application_metrics=self.stats["application_metrics"],
                parse_errors=self.stats["parse_errors"],
                insert_errors=self.stats["insert_errors"],
                elapsed_sec=round(elapsed, 1),
                avg_rate_per_sec=round(rate, 1),
            )
