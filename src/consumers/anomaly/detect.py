"""
CLI for real-time anomaly detection consumer.

Usage:
    python -m src.consumers.anomaly.detect [options]
"""

import argparse
import logging
import os
import sys

import structlog

from src.core.logger import setup_logging

from .consumer import AnomalyConsumer
from .models import AnomalyConfig

logger = structlog.get_logger(__name__)


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Real-time anomaly detection consumer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        # Basic usage
        python -m src.consumers.anomaly.detect

        # Custom configuration
        python -m src.consumers.anomaly.detect \\
            --kafka-servers kafka:9092 \\
            --method stl_zscore \\
            --z-score-threshold 3.5

        # Test run for 5 minutes
        python -m src.consumers.anomaly.detect --duration 300
        """,
    )

    # Kafka settings
    parser.add_argument(
        "--kafka-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        help="Kafka bootstrap servers (default: localhost:9092)",
    )
    parser.add_argument(
        "--topic",
        default=os.getenv("KAFKA_TOPIC", "datacenter-metrics"),
        help="Kafka topic (default: datacenter-metrics)",
    )
    parser.add_argument(
        "--group-id",
        default="anomaly-detection-consumer-group",
        help="Kafka consumer group ID",
    )
    parser.add_argument(
        "--offset-reset",
        choices=["earliest", "latest"],
        default="latest",
        help="Auto offset reset (default: latest - only new messages)",
    )

    # Method configuration
    parser.add_argument(
        "--method",
        default="stl_zscore",
        choices=["stl_zscore"],
        help="Detection method (default: stl_zscore)",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=["cpu_usage_percent", "memory_usage_percent", "cpu_temperature_celsius"],
        help="Metrics to monitor (default: cpu, memory, temperature)",
    )

    # Method parameters
    parser.add_argument(
        "--z-score-threshold",
        type=float,
        default=3.0,
        help="Z-score threshold for STL method (default: 3.0)",
    )

    # PostgreSQL settings
    parser.add_argument(
        "--postgres-host",
        default=os.getenv("POSTGRES_HOST", "localhost"),
        help="PostgreSQL host",
    )
    parser.add_argument(
        "--postgres-port",
        type=int,
        default=int(os.getenv("POSTGRES_PORT", "5432")),
        help="PostgreSQL port",
    )
    parser.add_argument(
        "--postgres-db",
        default=os.getenv("POSTGRES_DB", "mlops_db"),
        help="PostgreSQL database",
    )
    parser.add_argument(
        "--postgres-user",
        default=os.getenv("POSTGRES_USER", "mlops"),
        help="PostgreSQL user",
    )
    parser.add_argument(
        "--postgres-password",
        default=os.getenv("POSTGRES_PASSWORD", "mlops_password"),
        help="PostgreSQL password",
    )

    # Redis configuration
    parser.add_argument(
        "--redis-host",
        default=os.getenv("REDIS_HOST", "localhost"),
        help="Redis host (default: localhost or REDIS_HOST env var)",
    )

    # Runtime settings
    parser.add_argument(
        "--duration",
        type=int,
        help="Run for N seconds then stop (default: infinite)",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO)",
    )

    return parser.parse_args()


def build_config(args) -> AnomalyConfig:
    """Build configuration from arguments"""
    return AnomalyConfig(
        method_name=args.method,
        method_config={
            "z_score_threshold": args.z_score_threshold,
        },
        metrics=args.metrics,
        kafka_bootstrap_servers=args.kafka_servers,
        kafka_topic=args.topic,
        kafka_group_id=args.group_id,
        kafka_auto_offset_reset=args.offset_reset,
        postgres_host=args.postgres_host,
        postgres_port=args.postgres_port,
        postgres_database=args.postgres_db,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
        redis_host=args.redis_host,
    )


def main():
    """Main entry point"""
    args = parse_arguments()

    # Setup logging
    log_level = getattr(logging, args.log_level)
    setup_logging(level=log_level)

    logger.info("Starting anomaly detection consumer")

    try:
        config = build_config(args)

        consumer = AnomalyConsumer(config)
        consumer.run(duration_seconds=args.duration)

        logger.info("Consumer completed successfully")
        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0

    except Exception as e:
        logger.error("Consumer failed", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
