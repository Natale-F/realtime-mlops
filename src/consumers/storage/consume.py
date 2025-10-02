"""
Storage Consumer - CLI Entry Point
Consumes datacenter metrics from Kafka and stores them in PostgreSQL
"""

import argparse
import logging
import os
import sys

import structlog

from src.consumers.storage.consumer import StorageConsumer
from src.consumers.storage.models import ConsumerConfig
from src.core.logger import setup_logging

logger = structlog.get_logger(__name__)


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Storage Consumer for Kafka → PostgreSQL ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        # Basic usage with defaults
        python -m src.consumers.consume

        # Custom Kafka and PostgreSQL settings
        python -m src.consumers.consume --kafka-servers kafka:9092 --postgres-host postgres

        # Run for specific duration with custom batch size
        python -m src.consumers.consume --duration 300 --batch-size 200

        # Using environment variables
        export KAFKA_BOOTSTRAP_SERVERS=kafka:9092
        export POSTGRES_HOST=postgres
        python -m src.consumers.consume
        """,
    )

    # Kafka settings
    parser.add_argument(
        "--kafka-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        help="Kafka bootstrap servers (default: localhost:9092 or KAFKA_BOOTSTRAP_SERVERS env var)",
    )
    parser.add_argument(
        "--topic",
        default=os.getenv("KAFKA_TOPIC", "datacenter-metrics"),
        help="Kafka topic name (default: datacenter-metrics or KAFKA_TOPIC env var)",
    )
    parser.add_argument(
        "--group-id",
        default="storage-consumer-group",
        help="Kafka consumer group ID (default: storage-consumer-group)",
    )
    parser.add_argument(
        "--offset-reset",
        choices=["earliest", "latest"],
        default="earliest",
        help="Auto offset reset strategy (default: earliest)",
    )

    # PostgreSQL settings
    parser.add_argument(
        "--postgres-host",
        default=os.getenv("POSTGRES_HOST", "localhost"),
        help="PostgreSQL host (default: localhost or POSTGRES_HOST env var)",
    )
    parser.add_argument(
        "--postgres-port",
        type=int,
        default=int(os.getenv("POSTGRES_PORT", "5432")),
        help="PostgreSQL port (default: 5432 or POSTGRES_PORT env var)",
    )
    parser.add_argument(
        "--postgres-db",
        default=os.getenv("POSTGRES_DB", "mlops_db"),
        help="PostgreSQL database (default: mlops_db or POSTGRES_DB env var)",
    )
    parser.add_argument(
        "--postgres-user",
        default=os.getenv("POSTGRES_USER", "mlops"),
        help="PostgreSQL user (default: mlops or POSTGRES_USER env var)",
    )
    parser.add_argument(
        "--postgres-password",
        default=os.getenv("POSTGRES_PASSWORD", "mlops_password"),
        help="PostgreSQL password (default: mlops_password or POSTGRES_PASSWORD env var)",
    )

    # Consumer behavior
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size before committing (default: 100)",
    )
    parser.add_argument(
        "--commit-interval",
        type=float,
        default=5.0,
        help="Max seconds between commits (default: 5.0)",
    )
    parser.add_argument(
        "--max-poll-records",
        type=int,
        default=500,
        help="Max records per poll (default: 500)",
    )

    # Runtime settings
    parser.add_argument(
        "--duration",
        type=int,
        help="Duration to run in seconds (default: infinite)",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO or LOG_LEVEL env var)",
    )

    return parser.parse_args()


def build_config_from_args(args) -> ConsumerConfig:
    """Build a ConsumerConfig from command-line arguments"""
    config = ConsumerConfig(
        kafka_bootstrap_servers=args.kafka_servers,
        kafka_topic=args.topic,
        kafka_group_id=args.group_id,
        kafka_auto_offset_reset=args.offset_reset,
        postgres_host=args.postgres_host,
        postgres_port=args.postgres_port,
        postgres_database=args.postgres_db,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
        batch_size=args.batch_size,
        commit_interval_seconds=args.commit_interval,
        max_poll_records=args.max_poll_records,
    )

    logger.info("Configuration built from arguments", config=config)
    return config


def main():
    """Main entry point"""
    args = parse_arguments()

    # Setup logging
    log_level = getattr(logging, args.log_level)
    setup_logging(level=log_level)

    logger.info("Starting Storage Consumer")

    try:
        # Build configuration
        config = build_config_from_args(args)

        # Create and run consumer
        consumer = StorageConsumer(config)
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
