"""
Tests for generator models (AnomalyType, GeneratorConfig).
"""

import pytest

from src.generator.models import AnomalyType, GeneratorConfig


class TestAnomalyType:
    """Tests for AnomalyType enum."""

    def test_all_anomaly_types_exist(self):
        """Verify all expected anomaly types are defined."""
        expected_types = {
            "cpu_spike",
            "memory_leak",
            "temperature_high",
            "power_surge",
            "network_saturation",
            "latency_spike",
            "error_burst",
            "disk_io_bottleneck",
        }
        actual_types = {anomaly.value for anomaly in AnomalyType}
        assert actual_types == expected_types

    def test_anomaly_type_count(self):
        """Verify we have exactly 8 anomaly types."""
        assert len(list(AnomalyType)) == 8


class TestGeneratorConfig:
    """Tests for GeneratorConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GeneratorConfig()

        assert config.kafka_bootstrap_servers == "localhost:9092"
        assert config.kafka_topic == "datacenter-metrics"
        assert config.num_servers == 10
        assert config.num_services == 5
        assert config.event_interval_seconds == 1.0
        assert config.anomaly_probability == 0.05

    def test_custom_config(self):
        """Test configuration with custom values."""
        config = GeneratorConfig(
            kafka_bootstrap_servers="kafka:9093",
            kafka_topic="custom-topic",
            num_servers=20,
            num_services=10,
            anomaly_probability=0.15,
        )

        assert config.kafka_bootstrap_servers == "kafka:9093"
        assert config.kafka_topic == "custom-topic"
        assert config.num_servers == 20
        assert config.num_services == 10
        assert config.anomaly_probability == 0.15

    def test_post_init_enabled_anomalies_default(self):
        """Test that enabled_anomalies defaults to all types."""
        config = GeneratorConfig()

        assert config.enabled_anomalies is not None
        assert len(config.enabled_anomalies) == 8
        assert all(isinstance(a, AnomalyType) for a in config.enabled_anomalies)

    def test_post_init_racks_default(self):
        """Test that racks are initialized with default values."""
        config = GeneratorConfig()

        assert config.racks == ["R01", "R02", "R03", "R04", "R05"]

    def test_post_init_zones_default(self):
        """Test that zones are initialized with default values."""
        config = GeneratorConfig()

        assert config.zones == ["marseille-1", "marseille-2"]

    def test_custom_enabled_anomalies(self):
        """Test configuration with custom enabled anomalies."""
        custom_anomalies = [AnomalyType.CPU_SPIKE, AnomalyType.MEMORY_LEAK]
        config = GeneratorConfig(enabled_anomalies=custom_anomalies)

        assert config.enabled_anomalies == custom_anomalies
        assert len(config.enabled_anomalies) == 2

    @pytest.mark.parametrize(
        "num_servers,num_services",
        [
            (1, 1),
            (5, 3),
            (10, 5),
            (50, 20),
        ],
    )
    def test_server_service_counts(self, num_servers, num_services):
        """Test various server and service count combinations."""
        config = GeneratorConfig(num_servers=num_servers, num_services=num_services)

        assert config.num_servers == num_servers
        assert config.num_services == num_services
