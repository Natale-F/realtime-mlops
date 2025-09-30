"""
Tests for DatacenterGenerator class.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.generator.generator import DatacenterGenerator
from src.generator.models import AnomalyType, GeneratorConfig


class TestDatacenterGenerator:
    """Tests for DatacenterGenerator class."""

    @patch("src.generator.generator.KafkaProducer")
    def test_initialization(self, mock_producer, basic_config):
        """Test generator initialization."""
        generator = DatacenterGenerator(basic_config)

        # Verify producer was created
        mock_producer.assert_called_once()

        # Verify servers and services were created
        assert len(generator.servers) == basic_config.num_servers
        assert len(generator.services) == basic_config.num_services

    @patch("src.generator.generator.KafkaProducer")
    def test_servers_have_correct_attributes(self, mock_producer, basic_config):
        """Test that servers are initialized with correct attributes."""
        generator = DatacenterGenerator(basic_config)

        for server in generator.servers:
            # Server ID should match pattern
            assert server.server_id.startswith("srv-")

            # Rack and zone should be from config
            assert server.rack_id in basic_config.racks
            assert server.zone in basic_config.zones

    @patch("src.generator.generator.KafkaProducer")
    def test_services_have_correct_attributes(self, mock_producer, basic_config):
        """Test that services are initialized correctly."""
        generator = DatacenterGenerator(basic_config)

        for service in generator.services:
            # Service name should be set
            assert service.service_name is not None
            assert "-" in service.service_name

            # Server ID should be from one of the servers
            server_ids = [s.server_id for s in generator.servers]
            assert service.server_id in server_ids

    @patch("src.generator.generator.KafkaProducer")
    def test_generate_event_sends_metrics(self, mock_producer, basic_config):
        """Test that generate_event sends metrics to Kafka."""
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        generator = DatacenterGenerator(basic_config)
        generator.generate_event()

        # Should send one event per server + one per service
        expected_calls = basic_config.num_servers + basic_config.num_services
        assert mock_producer_instance.send.call_count == expected_calls

        # Verify flush was called
        mock_producer_instance.flush.assert_called_once()

    @patch("src.generator.generator.KafkaProducer")
    def test_generate_event_sends_to_correct_topic(self, mock_producer, basic_config):
        """Test that events are sent to the correct Kafka topic."""
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        generator = DatacenterGenerator(basic_config)
        generator.generate_event()

        # Check that all send calls used the correct topic
        for call in mock_producer_instance.send.call_args_list:
            topic = call[0][0]
            assert topic == basic_config.kafka_topic

    @patch("src.generator.generator.KafkaProducer")
    def test_anomaly_injection_probability(self, mock_producer):
        """Test that anomalies are injected based on probability."""
        # Config with 100% anomaly probability
        config = GeneratorConfig(
            num_servers=10,
            num_services=5,
            anomaly_probability=1.0,  # Always inject
        )

        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        generator = DatacenterGenerator(config)
        generator.generate_event()

        # With 100% probability, some anomalies should be active
        active_server_anomalies = sum(1 for s in generator.servers if s.active_anomaly is not None)
        active_service_anomalies = sum(
            1 for s in generator.services if s.active_anomaly is not None
        )

        # At least some should have anomalies (probabilistic but very likely)
        assert (active_server_anomalies + active_service_anomalies) > 0

    @patch("src.generator.generator.KafkaProducer")
    def test_no_anomalies_when_probability_zero(self, mock_producer):
        """Test that no anomalies are injected when probability is 0."""
        config = GeneratorConfig(
            num_servers=5,
            num_services=3,
            anomaly_probability=0.0,  # Never inject
        )

        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        generator = DatacenterGenerator(config)
        generator.generate_event()

        # No anomalies should be active
        assert all(s.active_anomaly is None for s in generator.servers)
        assert all(s.active_anomaly is None for s in generator.services)

    @patch("src.generator.generator.KafkaProducer")
    def test_enabled_anomalies_filter(self, mock_producer):
        """Test that only enabled anomalies are used."""
        # Use both server and service anomalies
        config = GeneratorConfig(
            num_servers=5,
            num_services=3,
            anomaly_probability=1.0,
            enabled_anomalies=[
                AnomalyType.CPU_SPIKE,  # Server anomaly
                AnomalyType.LATENCY_SPIKE,  # Service anomaly
            ],
        )

        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        generator = DatacenterGenerator(config)

        # Generate multiple events to trigger anomalies
        for _ in range(10):
            generator.generate_event()

        # Check that only CPU_SPIKE was used for servers
        for server in generator.servers:
            if server.active_anomaly is not None:
                assert server.active_anomaly == AnomalyType.CPU_SPIKE

        # Check that only LATENCY_SPIKE was used for services
        for service in generator.services:
            if service.active_anomaly is not None:
                assert service.active_anomaly == AnomalyType.LATENCY_SPIKE

    @patch("src.generator.generator.KafkaProducer")
    def test_run_stops_after_duration(self, mock_producer):
        """Test that run stops when duration is specified."""
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        config = GeneratorConfig(
            num_servers=1,
            num_services=1,
            event_interval_seconds=0.01,  # Very short interval
        )

        generator = DatacenterGenerator(config)

        # Run for a very short duration
        generator.run(duration_seconds=0.1)

        # Producer should be closed after run completes
        mock_producer_instance.close.assert_called_once()

    @patch("src.generator.generator.KafkaProducer")
    def test_kafka_connection_error_handling(self, mock_producer):
        """Test that Kafka connection errors are handled properly."""
        # Make KafkaProducer raise an exception
        mock_producer.side_effect = Exception("Connection failed")

        config = GeneratorConfig()

        # Should raise the exception (not swallow it)
        with pytest.raises(Exception, match="Connection failed"):
            DatacenterGenerator(config)
