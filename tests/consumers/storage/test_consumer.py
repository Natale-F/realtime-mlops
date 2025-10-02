"""
Tests for StorageConsumer class.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.consumers.storage.consumer import StorageConsumer


class TestStorageConsumer:
    """Tests for StorageConsumer class."""

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_initialization(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test consumer initialization."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db_class.return_value = mock_db

        mock_kafka = MagicMock()
        mock_kafka_class.return_value = mock_kafka

        consumer = StorageConsumer(consumer_config)

        # Verify database was initialized
        mock_db_class.assert_called_once_with(consumer_config)
        mock_db.check_health.assert_called_once()

        # Verify Kafka consumer was created
        mock_kafka_class.assert_called_once()

        # Verify stats are initialized
        assert consumer.stats["total_consumed"] == 0
        assert consumer.stats["server_metrics"] == 0
        assert consumer.stats["application_metrics"] == 0

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_initialization_fails_on_unhealthy_db(
        self, mock_db_class, mock_kafka_class, consumer_config
    ):
        """Test that initialization fails if database health check fails."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = False
        mock_db_class.return_value = mock_db

        with pytest.raises(RuntimeError, match="Database health check failed"):
            StorageConsumer(consumer_config)

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_parse_server_metric(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test parsing of server metric message."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db_class.return_value = mock_db

        consumer = StorageConsumer(consumer_config)

        message = {
            "type": "server_metric",
            "timestamp": "2025-10-02T12:00:00Z",
            "server_id": "srv-001",
            "cpu_usage_percent": 75.0,
        }

        result = consumer._parse_and_route_message(message)

        assert result is True
        assert len(consumer.server_metrics_batch) == 1
        assert consumer.stats["server_metrics"] == 1

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_parse_application_metric(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test parsing of application metric message."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db_class.return_value = mock_db

        consumer = StorageConsumer(consumer_config)

        message = {
            "type": "application_metric",
            "timestamp": "2025-10-02T12:00:00Z",
            "service_name": "api-gateway",
            "request_rate_per_sec": 100.0,
        }

        result = consumer._parse_and_route_message(message)

        assert result is True
        assert len(consumer.application_metrics_batch) == 1
        assert consumer.stats["application_metrics"] == 1

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_parse_unknown_type(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test handling of unknown message type."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db_class.return_value = mock_db

        consumer = StorageConsumer(consumer_config)

        message = {"type": "unknown_type", "data": "something"}

        result = consumer._parse_and_route_message(message)

        assert result is False
        assert consumer.stats["unknown_type"] == 1

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_parse_invalid_message(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test handling of invalid message."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db_class.return_value = mock_db

        consumer = StorageConsumer(consumer_config)

        # Message without type field
        message = {"data": "invalid"}

        result = consumer._parse_and_route_message(message)

        assert result is False
        assert consumer.stats["unknown_type"] == 1

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_flush_batches(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test flushing batches to database."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db.insert_batch_server_metrics.return_value = 2
        mock_db.insert_batch_application_metrics.return_value = 1
        mock_db_class.return_value = mock_db

        consumer = StorageConsumer(consumer_config)

        # Add some messages to batches
        consumer.server_metrics_batch = [{"server_id": "srv-001"}, {"server_id": "srv-002"}]
        consumer.application_metrics_batch = [{"service_name": "api-gateway"}]

        inserted = consumer._flush_batches()

        assert inserted == 3
        mock_db.insert_batch_server_metrics.assert_called_once()
        mock_db.insert_batch_application_metrics.assert_called_once()
        assert len(consumer.server_metrics_batch) == 0
        assert len(consumer.application_metrics_batch) == 0

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_should_commit_by_batch_size(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test commit trigger by batch size."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db_class.return_value = mock_db

        consumer = StorageConsumer(consumer_config)

        # Add messages up to batch size
        consumer.server_metrics_batch = [{"id": i} for i in range(consumer_config.batch_size)]

        assert consumer._should_commit() is True

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    @patch("src.consumers.storage.consumer.time")
    def test_should_commit_by_time(
        self, mock_time, mock_db_class, mock_kafka_class, consumer_config
    ):
        """Test commit trigger by time interval."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db_class.return_value = mock_db

        mock_time.time.return_value = 100.0  # Mock time

        consumer = StorageConsumer(consumer_config)
        consumer.last_commit_time = 50.0  # Long time ago

        # No messages, but time elapsed
        assert consumer._should_commit() is True

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_stats_tracking(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test that statistics are tracked correctly."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db_class.return_value = mock_db

        consumer = StorageConsumer(consumer_config)

        # Process some messages
        consumer._parse_and_route_message({"type": "server_metric", "server_id": "srv-001"})
        consumer._parse_and_route_message({"type": "application_metric", "service_name": "api"})
        consumer._parse_and_route_message({"type": "unknown"})

        assert consumer.stats["total_consumed"] == 0  # Not incremented in parse
        assert consumer.stats["server_metrics"] == 1
        assert consumer.stats["application_metrics"] == 1
        assert consumer.stats["unknown_type"] == 1

    @patch("src.consumers.storage.consumer.KafkaConsumer")
    @patch("src.consumers.storage.consumer.StorageDatabase")
    def test_flush_handles_partial_failure(self, mock_db_class, mock_kafka_class, consumer_config):
        """Test that flush handles partial insertion failures."""
        mock_db = MagicMock()
        mock_db.check_health.return_value = True
        mock_db.insert_batch_server_metrics.return_value = 1  # Only 1 out of 2 inserted
        mock_db.insert_batch_application_metrics.return_value = 1
        mock_db_class.return_value = mock_db

        consumer = StorageConsumer(consumer_config)

        consumer.server_metrics_batch = [{"server_id": "srv-001"}, {"server_id": "srv-002"}]
        consumer.application_metrics_batch = [{"service_name": "api-gateway"}]

        consumer._flush_batches()

        # Should track the insertion error
        assert consumer.stats["insert_errors"] == 1
