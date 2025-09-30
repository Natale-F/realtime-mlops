"""
Tests for ServerState class.
"""

import pytest

from src.generator.models import AnomalyType
from src.generator.server_state import ServerState


class TestServerState:
    """Tests for ServerState class."""

    def test_initialization(self):
        """Test ServerState initialization."""
        server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")

        assert server.server_id == "srv-001"
        assert server.rack_id == "R01"
        assert server.zone == "marseille-1"
        assert server.active_anomaly is None
        assert server.anomaly_duration == 0

    def test_base_values_are_realistic(self):
        """Test that base values are within realistic ranges."""
        server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")

        assert 20 <= server.base_cpu <= 40
        assert 30 <= server.base_memory <= 50
        assert 40 <= server.base_disk_usage <= 70
        assert 45 <= server.base_temp <= 55
        assert 200 <= server.base_power <= 300

    def test_generate_metrics_structure(self):
        """Test that generated metrics have the correct structure."""
        server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")
        metrics = server.generate_metrics()

        # Check all required fields are present
        required_fields = {
            "type",
            "timestamp",
            "server_id",
            "rack_id",
            "datacenter_zone",
            "cpu_usage_percent",
            "memory_usage_percent",
            "memory_available_gb",
            "disk_usage_percent",
            "disk_read_mbps",
            "disk_write_mbps",
            "network_rx_mbps",
            "network_tx_mbps",
            "cpu_temperature_celsius",
            "power_consumption_watts",
        }
        assert set(metrics.keys()) == required_fields

        # Check metric type
        assert metrics["type"] == "server_metric"
        assert metrics["server_id"] == "srv-001"
        assert metrics["rack_id"] == "R01"
        assert metrics["datacenter_zone"] == "marseille-1"

    def test_metrics_within_bounds(self):
        """Test that metrics stay within realistic bounds."""
        server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")
        metrics = server.generate_metrics()

        # CPU and memory should be percentages
        assert 0 < metrics["cpu_usage_percent"] <= 100
        assert 0 < metrics["memory_usage_percent"] <= 100
        assert 0 < metrics["disk_usage_percent"] <= 100

        # Temperature should be reasonable
        assert 30 <= metrics["cpu_temperature_celsius"] <= 95

        # Power should be positive
        assert metrics["power_consumption_watts"] > 0

    @pytest.mark.parametrize(
        "anomaly_type",
        [
            AnomalyType.CPU_SPIKE,
            AnomalyType.MEMORY_LEAK,
            AnomalyType.TEMPERATURE_HIGH,
            AnomalyType.POWER_SURGE,
            AnomalyType.NETWORK_SATURATION,
            AnomalyType.DISK_IO_BOTTLENECK,
        ],
    )
    def test_anomaly_injection(self, anomaly_type):
        """Test that anomaly injection sets the active anomaly."""
        server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")

        # Generate metrics with anomaly
        server.generate_metrics(inject_anomaly=anomaly_type)

        # Verify anomaly is active
        assert server.active_anomaly == anomaly_type
        assert server.anomaly_duration > 0
        assert 30 <= server.anomaly_duration <= 120

    def test_cpu_spike_increases_metrics(self):
        """Test that CPU spike anomaly increases related metrics."""
        server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")

        # Inject CPU spike
        server.generate_metrics(inject_anomaly=AnomalyType.CPU_SPIKE)

        # CPU spike should be active
        assert server.active_anomaly == AnomalyType.CPU_SPIKE

    def test_anomaly_duration_decreases(self):
        """Test that anomaly duration decreases over time."""
        server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")

        # Inject anomaly
        server.generate_metrics(inject_anomaly=AnomalyType.CPU_SPIKE)
        initial_duration = server.anomaly_duration

        # Generate more metrics
        server.generate_metrics()
        assert server.anomaly_duration == initial_duration - 1

    def test_anomaly_expires(self):
        """Test that anomaly expires after duration reaches 0."""
        server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")

        # Inject anomaly with manual duration
        server.active_anomaly = AnomalyType.CPU_SPIKE
        server.anomaly_duration = 1

        # Generate metrics (should decrement to 0)
        server.generate_metrics()

        # Anomaly should be cleared
        assert server.active_anomaly is None
        assert server.anomaly_duration == 0
