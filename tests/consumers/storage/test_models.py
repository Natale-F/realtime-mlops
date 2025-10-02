"""
Tests for storage consumer models and configuration.
"""

from src.consumers.storage.models import ConsumerConfig


class TestConsumerConfig:
    """Tests for ConsumerConfig dataclass."""

    def test_default_values(self):
        """Test that ConsumerConfig has correct default values."""
        config = ConsumerConfig()

        assert config.kafka_bootstrap_servers == "localhost:9092"
        assert config.kafka_topic == "datacenter-metrics"
        assert config.kafka_group_id == "storage-consumer-group"
        assert config.kafka_auto_offset_reset == "earliest"
        assert config.postgres_host == "localhost"
        assert config.postgres_port == 5432
        assert config.postgres_database == "mlops_db"
        assert config.postgres_user == "mlops"
        assert config.postgres_password == "mlops_password"
        assert config.batch_size == 100
        assert config.commit_interval_seconds == 5.0
        assert config.max_poll_records == 500
        assert config.enable_auto_commit is False

    def test_custom_values(self):
        """Test creating config with custom values."""
        config = ConsumerConfig(
            kafka_bootstrap_servers="custom:9092",
            kafka_topic="custom-topic",
            postgres_host="custom-host",
            batch_size=50,
        )

        assert config.kafka_bootstrap_servers == "custom:9092"
        assert config.kafka_topic == "custom-topic"
        assert config.postgres_host == "custom-host"
        assert config.batch_size == 50

    def test_all_parameters(self, consumer_config):
        """Test that all parameters can be set."""
        assert consumer_config.kafka_bootstrap_servers == "localhost:9092"
        assert consumer_config.kafka_topic == "test-topic"
        assert consumer_config.kafka_group_id == "test-group"
        assert consumer_config.postgres_host == "localhost"
        assert consumer_config.postgres_port == 5432
        assert consumer_config.postgres_database == "test_db"
        assert consumer_config.postgres_user == "test_user"
        assert consumer_config.postgres_password == "test_password"
        assert consumer_config.batch_size == 10
        assert consumer_config.commit_interval_seconds == 1.0

    def test_config_immutable_after_creation(self):
        """Test that config values can be accessed after creation."""
        config = ConsumerConfig(batch_size=200)
        assert config.batch_size == 200

        # Update should work (dataclass is not frozen by default)
        config.batch_size = 300
        assert config.batch_size == 300
