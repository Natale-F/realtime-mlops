"""
Tests for storage database operations.
"""

from unittest.mock import MagicMock, patch

from src.consumers.storage.database import StorageDatabase


class TestStorageDatabase:
    """Tests for StorageDatabase class."""

    @patch("src.consumers.storage.database.psycopg2.connect")
    def test_initialization(self, mock_connect, consumer_config):
        """Test database initialization."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        db = StorageDatabase(consumer_config)

        # Verify connection was established
        mock_connect.assert_called_once_with(
            host=consumer_config.postgres_host,
            port=consumer_config.postgres_port,
            database=consumer_config.postgres_database,
            user=consumer_config.postgres_user,
            password=consumer_config.postgres_password,
            connect_timeout=10,
        )

        assert db.connection == mock_connection

    @patch("src.core.database.PostgresConnection.check_health")
    @patch("src.consumers.storage.database.psycopg2.connect")
    def test_health_check_success(self, mock_connect, mock_health, consumer_config):
        """Test successful database health check."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_health.return_value = True

        db = StorageDatabase(consumer_config)

        # Mock the health check to return True
        result = db.check_health()

        assert result is True

    @patch("src.consumers.storage.database.psycopg2.connect")
    def test_health_check_failure(self, mock_connect, consumer_config):
        """Test failed database health check."""
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.side_effect = Exception("Connection failed")
        mock_connect.return_value = mock_connection

        db = StorageDatabase(consumer_config)
        assert db.check_health() is False

    @patch("src.consumers.storage.database.psycopg2.connect")
    @patch("src.consumers.storage.database.psycopg2.extras.execute_batch")
    def test_insert_batch_server_metrics(self, mock_execute_batch, mock_connect, consumer_config):
        """Test batch insertion of server metrics."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        db = StorageDatabase(consumer_config)

        metrics = [
            {
                "timestamp": "2025-10-02T12:00:00Z",
                "server_id": "srv-001",
                "cpu_usage_percent": 75.0,
                "memory_usage_percent": 60.0,
                "memory_available_gb": 16.0,
                "disk_usage_percent": 50.0,
                "disk_read_mbps": 100.0,
                "disk_write_mbps": 50.0,
                "network_rx_mbps": 200.0,
                "network_tx_mbps": 150.0,
                "cpu_temperature_celsius": 65.0,
                "power_consumption_watts": 250.0,
                "rack_id": "R01",
                "datacenter_zone": "zone-1",
            }
        ]

        inserted = db.insert_batch_server_metrics(metrics)

        assert inserted == 1
        mock_execute_batch.assert_called_once()
        # Check that metrics were passed (call_args[0][2] is the third positional arg)
        assert mock_execute_batch.call_args[0][2] == metrics

    @patch("src.consumers.storage.database.psycopg2.connect")
    @patch("src.consumers.storage.database.psycopg2.extras.execute_batch")
    def test_insert_batch_application_metrics(
        self, mock_execute_batch, mock_connect, consumer_config
    ):
        """Test batch insertion of application metrics."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        db = StorageDatabase(consumer_config)

        metrics = [
            {
                "timestamp": "2025-10-02T12:00:00Z",
                "service_name": "api-gateway",
                "request_rate_per_sec": 100.0,
                "response_time_p50_ms": 10.0,
                "response_time_p95_ms": 50.0,
                "response_time_p99_ms": 100.0,
                "error_rate_percent": 0.5,
                "error_count": 5,
                "active_connections": 50,
                "queue_depth": 10,
                "server_id": "srv-001",
                "endpoint": "/api/users",
            }
        ]

        inserted = db.insert_batch_application_metrics(metrics)

        assert inserted == 1
        mock_execute_batch.assert_called_once()

    @patch("src.consumers.storage.database.psycopg2.connect")
    def test_insert_batch_empty_list(self, mock_connect, consumer_config):
        """Test batch insertion with empty list."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        db = StorageDatabase(consumer_config)

        inserted_server = db.insert_batch_server_metrics([])
        inserted_app = db.insert_batch_application_metrics([])

        assert inserted_server == 0
        assert inserted_app == 0

    @patch("src.consumers.storage.database.psycopg2.connect")
    @patch("src.consumers.storage.database.psycopg2.extras.execute_batch")
    def test_insert_batch_handles_error(self, mock_execute_batch, mock_connect, consumer_config):
        """Test that batch insertion handles errors gracefully."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Simulate database error
        mock_execute_batch.side_effect = Exception("Database error")

        db = StorageDatabase(consumer_config)

        metrics = [{"timestamp": "2025-10-02T12:00:00Z", "server_id": "srv-001"}]

        inserted = db.insert_batch_server_metrics(metrics)

        assert inserted == 0  # Should return 0 on error

    @patch("src.consumers.storage.database.psycopg2.connect")
    def test_close_connection(self, mock_connect, consumer_config):
        """Test closing database connection."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        db = StorageDatabase(consumer_config)
        db.close()

        mock_connection.close.assert_called_once()
