"""
Tests for core PostgreSQL connection management.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.database import PostgresConnection


class TestPostgresConnection:
    """Tests for PostgresConnection base class."""

    @patch("src.core.database.psycopg2.connect")
    def test_initialization_success(self, mock_connect):
        """Test successful database connection initialization."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        # Verify connection was established with correct parameters
        mock_connect.assert_called_once_with(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
            connect_timeout=10,
        )

        assert conn.connection == mock_connection
        assert conn.host == "localhost"
        assert conn.port == 5432
        assert conn.database == "test_db"
        assert conn.user == "test_user"
        assert conn.password == "test_password"

    @patch("src.core.database.psycopg2.connect")
    def test_initialization_failure(self, mock_connect):
        """Test connection initialization failure."""
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            PostgresConnection(
                host="localhost",
                port=5432,
                database="test_db",
                user="test_user",
                password="test_password",
            )

    @patch("src.core.database.psycopg2.connect")
    def test_get_cursor_context_manager_success(self, mock_connect):
        """Test cursor context manager with successful operation."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        # Use cursor context manager
        with conn.get_cursor() as cursor:
            # The cursor should be usable
            assert cursor is not None

        # Verify commit was called
        mock_connection.commit.assert_called_once()

    @patch("src.core.database.psycopg2.connect")
    def test_get_cursor_context_manager_rollback_on_error(self, mock_connect):
        """Test cursor context manager rolls back on error."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query failed")
        mock_connection.cursor.return_value = mock_cursor

        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        # Use cursor context manager with error
        with pytest.raises(Exception, match="Query failed"):  # noqa: SIM117
            with conn.get_cursor() as cursor:
                cursor.execute("BAD SQL")

        # Verify rollback was called instead of commit
        mock_connection.rollback.assert_called_once()
        mock_connection.commit.assert_not_called()

    @patch("src.core.database.psycopg2.connect")
    def test_execute_query_success(self, mock_connect):
        """Test successful query execution."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        result = conn.execute_query(
            "INSERT INTO test (name) VALUES (%(name)s)", {"name": "test_value"}
        )

        assert result is True
        mock_cursor.execute.assert_called_once_with(
            "INSERT INTO test (name) VALUES (%(name)s)", {"name": "test_value"}
        )

    @patch("src.core.database.psycopg2.connect")
    def test_execute_query_failure(self, mock_connect):
        """Test failed query execution."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query error")
        mock_connection.cursor.return_value = mock_cursor

        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        result = conn.execute_query("BAD QUERY")

        assert result is False

    @patch("src.core.database.psycopg2.connect")
    def test_execute_query_without_params(self, mock_connect):
        """Test query execution without parameters."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        result = conn.execute_query("SELECT 1")

        assert result is True
        # Should be called with empty dict when no params provided
        mock_cursor.execute.assert_called_once_with("SELECT 1", {})

    @patch("src.core.database.psycopg2.connect")
    def test_check_health_success(self, mock_connect):
        """Test successful health check."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value = mock_cursor

        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        result = conn.check_health()

        assert result is True
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.fetchone.assert_called_once()

    @patch("src.core.database.psycopg2.connect")
    def test_check_health_failure(self, mock_connect):
        """Test failed health check."""
        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = Exception("Connection lost")

        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        result = conn.check_health()

        assert result is False

    @patch("src.core.database.psycopg2.connect")
    def test_check_health_returns_false_on_wrong_result(self, mock_connect):
        """Test health check returns False when SELECT 1 returns unexpected value."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)  # Wrong value
        mock_connection.cursor.return_value = mock_cursor

        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        result = conn.check_health()

        assert result is False

    @patch("src.core.database.psycopg2.connect")
    def test_close_connection(self, mock_connect):
        """Test closing database connection."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        conn.close()

        mock_connection.close.assert_called_once()

    @patch("src.core.database.psycopg2.connect")
    def test_close_when_no_connection(self, mock_connect):
        """Test closing when connection is None."""
        mock_connect.return_value = MagicMock()

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        # Set connection to None
        conn.connection = None

        # Should not raise an error
        conn.close()

    @patch("src.core.database.psycopg2.connect")
    def test_multiple_cursor_operations(self, mock_connect):
        """Test multiple cursor operations in sequence."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        mock_connect.return_value = mock_connection

        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )

        # Execute multiple operations
        with conn.get_cursor() as cursor:
            cursor.execute("CREATE TABLE test (id INT)")
            cursor.execute("INSERT INTO test VALUES (1)")

        # Verify both operations were executed
        assert mock_cursor.execute.call_count == 2
        mock_connection.commit.assert_called_once()
