"""
Main datacenter generator orchestrating server and application metrics.
"""

import json
import random
import time
from datetime import UTC, datetime, timedelta

import structlog
from kafka import KafkaProducer

from .models import AnomalyType, GeneratorConfig
from .server_state import ServerState
from .service_state import ServiceState

logger = structlog.get_logger(__name__)


class DatacenterGenerator:
    """Main generator orchestrating server and application metrics"""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        logger.info("Initializing datacenter generator", config=config)

        # Initialize Kafka producer
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=config.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type="gzip",
            )
            logger.info(
                "Kafka producer initialized",
                bootstrap_servers=config.kafka_bootstrap_servers,
                topic=config.kafka_topic,
            )
        except Exception as e:
            logger.error("Failed to initialize Kafka producer", error=str(e))
            raise

        # Initialize servers
        self.servers: list[ServerState] = []
        for i in range(config.num_servers):
            server_id = f"srv-{i + 1:03d}"
            rack_id = random.choice(config.racks)
            zone = random.choice(config.zones)
            self.servers.append(ServerState(server_id, rack_id, zone))

        logger.info(
            "Servers initialized", count=len(self.servers), racks=config.racks, zones=config.zones
        )

        # Initialize services
        self.services: list[ServiceState] = []
        service_names = [
            "api-gateway",
            "user-service",
            "product-service",
            "order-service",
            "payment-service",
            "notification-service",
            "cache-redis",
            "database-primary",
            "search-engine",
        ]

        for i in range(config.num_services):
            service_name = service_names[i % len(service_names)]
            server = random.choice(self.servers)
            self.services.append(ServiceState(f"{service_name}-{i + 1}", server.server_id))

        logger.info("Services initialized", count=len(self.services))
        logger.info(
            "Anomaly configuration",
            probability=config.anomaly_probability,
            enabled_anomalies=[a.value for a in config.enabled_anomalies],
        )

    def generate_event(self, timestamp: datetime | None = None):
        """Generate and send one round of metrics
        
        Args:
            timestamp: Optional custom timestamp for backfill mode
        """

        # Generate server metrics
        for server in self.servers:
            anomaly = None
            if random.random() < self.config.anomaly_probability:
                # Pick a server-related anomaly
                server_anomalies = [
                    a
                    for a in self.config.enabled_anomalies
                    if a not in [AnomalyType.LATENCY_SPIKE, AnomalyType.ERROR_BURST]
                ]
                if server_anomalies:
                    anomaly = random.choice(server_anomalies)

            metrics = server.generate_metrics(inject_anomaly=anomaly, timestamp=timestamp)
            self.producer.send(self.config.kafka_topic, value=metrics)

            if anomaly:
                logger.warning(
                    "Anomaly injected",
                    anomaly_type=anomaly.value,
                    server_id=server.server_id,
                    rack_id=server.rack_id,
                    zone=server.zone,
                )

        # Generate application metrics
        for service in self.services:
            anomaly = None
            if random.random() < self.config.anomaly_probability:
                # Pick an application-related anomaly
                app_anomalies = [AnomalyType.LATENCY_SPIKE, AnomalyType.ERROR_BURST]
                anomaly = random.choice(
                    [a for a in app_anomalies if a in self.config.enabled_anomalies]
                )

            metrics = service.generate_metrics(inject_anomaly=anomaly, timestamp=timestamp)
            self.producer.send(self.config.kafka_topic, value=metrics)

            if anomaly:
                logger.warning(
                    "Anomaly injected",
                    anomaly_type=anomaly.value,
                    service_name=service.service_name,
                    server_id=service.server_id,
                )

        self.producer.flush()

    def run(self, duration_seconds: int = None):
        """Run the generator continuously or for a specified duration

        Args:
            duration_seconds: Optional duration in seconds. If None, runs indefinitely.
        """

        logger.info(
            "Starting generator",
            topic=self.config.kafka_topic,
            duration=duration_seconds if duration_seconds else "indefinite",
        )

        start_time = time.time()
        event_count = 0
        last_log_time = start_time

        try:
            while True:
                self.generate_event()
                event_count += len(self.servers) + len(self.services)

                elapsed = time.time() - start_time

                # Log stats every 10 seconds
                if time.time() - last_log_time >= 10:
                    rate = event_count / elapsed if elapsed > 0 else 0
                    logger.info(
                        "Generator stats",
                        total_events=event_count,
                        rate_per_sec=round(rate, 1),
                        elapsed_sec=round(elapsed, 1),
                    )
                    last_log_time = time.time()

                if duration_seconds and elapsed >= duration_seconds:
                    logger.info("Duration limit reached", duration_seconds=duration_seconds)
                    break

                time.sleep(self.config.event_interval_seconds)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping generator")

        except Exception as e:
            logger.error("Generator error", error=str(e), exc_info=True)
            raise

        finally:
            elapsed = time.time() - start_time
            rate = event_count / elapsed if elapsed > 0 else 0

            self.producer.close()
            logger.info(
                "Generator stopped",
                total_events=event_count,
                elapsed_sec=round(elapsed, 1),
                avg_rate_per_sec=round(rate, 1),
            )

    def run_backfill(self):
        """Generate historical data quickly for testing
        
        Generates backfill_days worth of data with backfill_interval_seconds spacing.
        Much faster than real-time generation.
        """
        logger.info(
            "Starting backfill mode",
            days=self.config.backfill_days,
            interval_seconds=self.config.backfill_interval_seconds,
            servers=len(self.servers),
            services=len(self.services),
        )

        start_time = time.time()
        end_timestamp = datetime.now(UTC)
        start_timestamp = end_timestamp - timedelta(days=self.config.backfill_days)
        
        total_points = int(
            self.config.backfill_days * 24 * 3600 / self.config.backfill_interval_seconds
        )
        
        logger.info(
            "Backfill plan",
            start_timestamp=start_timestamp.isoformat(),
            end_timestamp=end_timestamp.isoformat(),
            total_points=total_points,
            estimated_events=total_points * (len(self.servers) + len(self.services)),
        )

        current_timestamp = start_timestamp
        point_count = 0
        event_count = 0
        last_log_time = time.time()

        try:
            while current_timestamp <= end_timestamp:
                # Generate events with historical timestamp
                self.generate_event(timestamp=current_timestamp)
                
                point_count += 1
                event_count += len(self.servers) + len(self.services)
                
                # Move to next timestamp
                current_timestamp += timedelta(seconds=self.config.backfill_interval_seconds)
                
                # Log progress every 10 seconds of real time
                if time.time() - last_log_time >= 10:
                    progress = (point_count / total_points) * 100
                    elapsed = time.time() - start_time
                    rate = event_count / elapsed if elapsed > 0 else 0
                    
                    logger.info(
                        "Backfill progress",
                        progress_percent=round(progress, 1),
                        points=point_count,
                        total_points=total_points,
                        events=event_count,
                        rate_per_sec=round(rate, 0),
                        current_timestamp=current_timestamp.isoformat(),
                    )
                    last_log_time = time.time()
            
            elapsed = time.time() - start_time
            logger.info(
                "Backfill completed",
                total_points=point_count,
                total_events=event_count,
                elapsed_sec=round(elapsed, 1),
                avg_rate_per_sec=round(event_count / elapsed, 0),
            )

        except KeyboardInterrupt:
            logger.info("Backfill interrupted by user")
        
        except Exception as e:
            logger.error("Backfill failed", error=str(e), exc_info=True)
            raise

        finally:
            self.producer.close()
