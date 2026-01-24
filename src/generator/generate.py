"""
Datacenter Event Generator - CLI Entry Point
Simulates realistic server and application metrics with configurable anomalies
"""

import argparse
import sys

import structlog

from src.core.logger import setup_logging
from src.generator import (
    CHAOS_CONFIG,
    DEV_CONFIG,
    NETWORK_STRESS_CONFIG,
    NORMAL_CONFIG,
    PRODUCTION_CONFIG,
    TEMPERATURE_FOCUS_CONFIG,
    AnomalyType,
    DatacenterGenerator,
    GeneratorConfig,
)

logger = structlog.get_logger(__name__)


# Predefined configurations
CONFIGS = {
    "normal": NORMAL_CONFIG,
    "chaos": CHAOS_CONFIG,
    "temperature": TEMPERATURE_FOCUS_CONFIG,
    "network": NETWORK_STRESS_CONFIG,
    "production": PRODUCTION_CONFIG,
    "dev": DEV_CONFIG,
}


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Datacenter Event Generator for Kafka",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            # Use predefined normal config
            python -m src.generator.generate --config normal

            # Use chaos config for 300 seconds
            python -m src.generator.generate --config chaos --duration 300

            # Custom configuration
            python -m src.generator.generate --servers 20 --services 10 --anomaly-prob 0.05

            # Specify Kafka settings
            python -m src.generator.generate --kafka-servers kafka:9092 --topic metrics
        """,
    )

    # Predefined config
    parser.add_argument(
        "--config", choices=list(CONFIGS.keys()), help="Use a predefined configuration"
    )

    # Kafka settings
    parser.add_argument(
        "--kafka-servers",
        default="localhost:9092",
        help="Kafka bootstrap servers (default: localhost:9092)",
    )
    parser.add_argument(
        "--topic",
        default="datacenter-metrics",
        help="Kafka topic name (default: datacenter-metrics)",
    )

    # Generation settings
    parser.add_argument("--servers", type=int, help="Number of servers to simulate")
    parser.add_argument("--services", type=int, help="Number of services to simulate")
    parser.add_argument("--interval", type=float, help="Interval between events in seconds")

    # Anomaly settings
    parser.add_argument(
        "--anomaly-prob", type=float, help="Probability of anomaly injection (0.0 to 1.0)"
    )
    parser.add_argument(
        "--anomalies",
        nargs="+",
        choices=[a.value for a in AnomalyType],
        help="Specific anomaly types to enable",
    )

    # Runtime settings
    parser.add_argument(
        "--duration", type=int, help="Duration to run in seconds (default: infinite)"
    )

    # Backfill mode settings
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Enable backfill mode (generate historical data quickly)",
    )
    parser.add_argument(
        "--backfill-days",
        type=int,
        default=7,
        help="Days of historical data to generate in backfill mode (default: 7)",
    )
    parser.add_argument(
        "--backfill-interval",
        type=int,
        default=300,
        help="Seconds between backfill data points (default: 300 = 5min)",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    return parser.parse_args()


def build_config_from_args(args) -> GeneratorConfig:
    """Build a GeneratorConfig from command-line arguments"""

    # Start with predefined config if specified
    if args.config:
        config = CONFIGS[args.config]
        logger.info("Using predefined configuration", config_name=args.config)
    else:
        config = GeneratorConfig()
        logger.info("Using default configuration")

    # Override with command-line arguments
    if args.kafka_servers:
        config.kafka_bootstrap_servers = args.kafka_servers
    if args.topic:
        config.kafka_topic = args.topic
    if args.servers:
        config.num_servers = args.servers
    if args.services:
        config.num_services = args.services
    if args.interval:
        config.event_interval_seconds = args.interval
    if args.anomaly_prob is not None:
        config.anomaly_probability = args.anomaly_prob
    if args.anomalies:
        config.enabled_anomalies = [AnomalyType(a) for a in args.anomalies]

    # Backfill settings
    config.backfill_mode = args.backfill
    if args.backfill:
        config.backfill_days = args.backfill_days
        config.backfill_interval_seconds = args.backfill_interval

    return config


def main():
    """Main entry point"""
    args = parse_arguments()

    # Setup logging
    log_level = getattr(structlog.stdlib.logging, args.log_level)
    setup_logging(level=log_level)

    logger.info("Starting Datacenter Event Generator")

    try:
        # Build configuration
        config = build_config_from_args(args)

        # Create generator
        generator = DatacenterGenerator(config)

        # Run in appropriate mode
        if config.backfill_mode:
            logger.info("Running in BACKFILL mode")
            generator.run_backfill()
        else:
            logger.info("Running in REAL-TIME mode")
            generator.run(duration_seconds=args.duration)

        logger.info("Generator completed successfully")
        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0

    except Exception as e:
        logger.error("Generator failed", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
