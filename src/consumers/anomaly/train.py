"""
CLI for training anomaly detection models.

Usage:
    python -m src.consumers.anomaly.train [options]
"""

import argparse
import logging
import os
import sys
import time

import structlog

from src.core.logger import setup_logging

from .models import AnomalyConfig
from .trainer import AnomalyTrainer

logger = structlog.get_logger(__name__)


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Train anomaly detection models on historical data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        # Basic usage
        python -m src.consumers.anomaly.train

        # Custom configuration
        python -m src.consumers.anomaly.train \\
            --method stl_zscore \\
            --history-days 14 \\
            --aggregation 10min

        # Periodic retraining (every 10 minutes)
        python -m src.consumers.anomaly.train --schedule 10
        """,
    )

    # Method configuration
    parser.add_argument(
        "--method",
        default="stl_zscore",
        choices=["stl_zscore"],
        help="Detection method to use (default: stl_zscore)",
    )

    # Data configuration
    parser.add_argument(
        "--history-days",
        type=int,
        default=7,
        help="Days of historical data to use for training (default: 7)",
    )
    parser.add_argument(
        "--aggregation",
        default="5min",
        choices=["1min", "5min", "10min", "15min", "1hour"],
        help="Time bucket aggregation (default: 5min)",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=["cpu_usage_percent", "memory_usage_percent", "cpu_temperature_celsius"],
        help="Metrics to train on (default: cpu, memory, temperature)",
    )

    # Method-specific parameters
    parser.add_argument(
        "--seasonal-period",
        type=int,
        default=288,
        help="STL seasonal period (default: 288 = 24h in 5min buckets)",
    )
    parser.add_argument(
        "--z-score-threshold",
        type=float,
        default=3.0,
        help="Z-score threshold for anomaly detection (default: 3.0)",
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
        help="PostgreSQL port (default: 5432)",
    )
    parser.add_argument(
        "--postgres-db",
        default=os.getenv("POSTGRES_DB", "mlops_db"),
        help="PostgreSQL database (default: mlops_db)",
    )
    parser.add_argument(
        "--postgres-user",
        default=os.getenv("POSTGRES_USER", "mlops"),
        help="PostgreSQL user (default: mlops)",
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

    # Scheduling
    parser.add_argument(
        "--schedule",
        type=int,
        help="Run training periodically every N minutes (default: run once)",
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
            "seasonal_period": args.seasonal_period,
            "z_score_threshold": args.z_score_threshold,
        },
        history_days=args.history_days,
        aggregation_interval=args.aggregation,
        metrics=args.metrics,
        postgres_host=args.postgres_host,
        postgres_port=args.postgres_port,
        postgres_database=args.postgres_db,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
        redis_host=args.redis_host,
    )


def train_once(config: AnomalyConfig) -> dict:
    """Run training once"""
    trainer = AnomalyTrainer(config)
    try:
        stats = trainer.train_all()
        return stats
    finally:
        trainer.close()


def train_scheduled(config: AnomalyConfig, interval_minutes: int):
    """Run training on a schedule"""
    logger.info("Starting scheduled training", interval_minutes=interval_minutes)

    iteration = 0
    while True:
        iteration += 1
        logger.info("Starting training iteration", iteration=iteration)

        try:
            stats = train_once(config)
            logger.info("Training iteration completed", iteration=iteration, stats=stats)
        except Exception as e:
            logger.error("Training iteration failed", iteration=iteration, error=str(e))

        # Sleep until next iteration
        sleep_seconds = interval_minutes * 60
        logger.info("Sleeping until next iteration", sleep_seconds=sleep_seconds)
        time.sleep(sleep_seconds)


def main():
    """Main entry point"""
    args = parse_arguments()

    # Setup logging
    log_level = getattr(logging, args.log_level)
    setup_logging(level=log_level)

    logger.info("Starting anomaly detection training")

    try:
        config = build_config(args)

        if args.schedule:
            # Scheduled training
            train_scheduled(config, args.schedule)
        else:
            # One-time training
            stats = train_once(config)
            logger.info("Training completed successfully", stats=stats)

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0

    except Exception as e:
        logger.error("Training failed", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
