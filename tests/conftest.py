"""
Pytest configuration and shared fixtures.
"""

import pytest

from src.consumers.storage.models import ConsumerConfig
from src.generator.models import AnomalyType, GeneratorConfig


# Generator fixtures
@pytest.fixture
def basic_config():
    """Basic generator configuration for testing."""
    return GeneratorConfig(
        kafka_bootstrap_servers="localhost:9092",
        kafka_topic="test-topic",
        num_servers=3,
        num_services=2,
        event_interval_seconds=1.0,
        anomaly_probability=0.1,
    )


@pytest.fixture
def minimal_config():
    """Minimal configuration for fast tests."""
    return GeneratorConfig(
        num_servers=1,
        num_services=1,
        event_interval_seconds=0.1,
        anomaly_probability=0.0,  # No anomalies for predictable tests
    )


@pytest.fixture
def all_anomaly_types():
    """List of all anomaly types."""
    return list(AnomalyType)


# Consumer fixtures
@pytest.fixture
def consumer_config():
    """Basic consumer configuration for testing."""
    return ConsumerConfig(
        kafka_bootstrap_servers="localhost:9092",
        kafka_topic="test-topic",
        kafka_group_id="test-group",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_database="test_db",
        postgres_user="test_user",
        postgres_password="test_password",
        batch_size=10,
        commit_interval_seconds=1.0,
    )
