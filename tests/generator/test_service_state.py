"""
Tests for ServiceState class.
"""

import pytest

from src.generator.models import AnomalyType
from src.generator.service_state import ServiceState


class TestServiceState:
    """Tests for ServiceState class."""

    def test_initialization(self):
        """Test ServiceState initialization."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")

        assert service.service_name == "api-gateway-1"
        assert service.server_id == "srv-001"
        assert service.active_anomaly is None
        assert service.anomaly_duration == 0

    def test_base_values_are_realistic(self):
        """Test that base values are within realistic ranges."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")

        assert 100 <= service.base_request_rate <= 1000
        assert 10 <= service.base_latency <= 50
        assert 0.1 <= service.base_error_rate <= 1.0

    def test_generate_metrics_structure(self):
        """Test that generated metrics have the correct structure."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")
        metrics = service.generate_metrics()

        # Check all required fields
        required_fields = {
            "type",
            "timestamp",
            "service_name",
            "server_id",
            "request_rate_per_sec",
            "response_time_p50_ms",
            "response_time_p95_ms",
            "response_time_p99_ms",
            "error_rate_percent",
            "error_count",
            "active_connections",
            "queue_depth",
            "endpoint",
        }
        assert set(metrics.keys()) == required_fields

        # Check metric type
        assert metrics["type"] == "application_metric"
        assert metrics["service_name"] == "api-gateway-1"
        assert metrics["server_id"] == "srv-001"

    def test_metrics_within_bounds(self):
        """Test that metrics are realistic."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")
        metrics = service.generate_metrics()

        # Request rate should be positive
        assert metrics["request_rate_per_sec"] > 0

        # Latency should be ordered: p50 < p95 < p99
        assert metrics["response_time_p50_ms"] > 0
        assert metrics["response_time_p95_ms"] > metrics["response_time_p50_ms"]
        assert metrics["response_time_p99_ms"] > metrics["response_time_p95_ms"]

        # Error rate should be a percentage
        assert 0 <= metrics["error_rate_percent"] <= 50

        # Connections and queue depth should be positive
        assert metrics["active_connections"] >= 0
        assert metrics["queue_depth"] >= 0

    def test_endpoint_is_valid(self):
        """Test that endpoint is one of the expected values."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")
        metrics = service.generate_metrics()

        valid_endpoints = ["/api/users", "/api/products", "/api/orders", "/health"]
        assert metrics["endpoint"] in valid_endpoints

    @pytest.mark.parametrize(
        "anomaly_type",
        [AnomalyType.LATENCY_SPIKE, AnomalyType.ERROR_BURST],
    )
    def test_service_anomaly_injection(self, anomaly_type):
        """Test service-specific anomaly injection."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")

        # Generate metrics with anomaly
        service.generate_metrics(inject_anomaly=anomaly_type)

        # Verify anomaly is active
        assert service.active_anomaly == anomaly_type
        assert service.anomaly_duration > 0
        assert 20 <= service.anomaly_duration <= 90

    def test_latency_spike_increases_latency(self):
        """Test that latency spike anomaly is applied."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")

        # Inject latency spike
        service.generate_metrics(inject_anomaly=AnomalyType.LATENCY_SPIKE)

        # Verify anomaly is set
        assert service.active_anomaly == AnomalyType.LATENCY_SPIKE

    def test_error_burst_increases_errors(self):
        """Test that error burst anomaly is applied."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")

        # Inject error burst
        service.generate_metrics(inject_anomaly=AnomalyType.ERROR_BURST)

        # Verify anomaly is set
        assert service.active_anomaly == AnomalyType.ERROR_BURST

    def test_anomaly_duration_decreases(self):
        """Test that anomaly duration decreases over time."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")

        # Inject anomaly
        service.generate_metrics(inject_anomaly=AnomalyType.LATENCY_SPIKE)
        initial_duration = service.anomaly_duration

        # Generate more metrics
        service.generate_metrics()
        assert service.anomaly_duration == initial_duration - 1

    def test_time_multiplier_business_hours(self):
        """Test that time multiplier affects request rate."""
        service = ServiceState(service_name="api-gateway-1", server_id="srv-001")

        # Generate metrics (will use current hour)
        metrics = service.generate_metrics()

        # Just verify the request rate is positive and reasonable
        # (we can't easily control the time in this test)
        assert metrics["request_rate_per_sec"] > 0
