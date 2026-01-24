"""
Base abstract interface for anomaly detection methods.

All detection methods must inherit from AnomalyDetectionMethod and implement:
- fit(): Train on historical data
- predict(): Detect anomalies in real-time
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass
class DetectionResult:
    """Result of an anomaly detection"""

    is_anomaly: bool
    score: float
    expected_value: float | None
    actual_value: float
    details: dict[str, Any]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class ModelComponents:
    """Trained model components (serializable for caching)"""

    method_name: str
    entity_id: str  # server_id or service_name
    metric_name: str  # cpu_usage_percent, memory_usage_percent, etc.
    components: dict[str, Any]
    trained_at: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ModelComponents":
        """Create from dictionary"""
        return cls(**data)


class AnomalyDetectionMethod(ABC):
    """Abstract base class for all anomaly detection methods

    Each method must implement:
    1. fit() - Train on historical timeseries data
    2. predict() - Detect anomalies in real-time on new data points
    """

    @abstractmethod
    def fit(self, timeseries: pd.DataFrame, entity_id: str, metric_name: str) -> ModelComponents:
        """Train the model on historical data

        Args:
            timeseries: DataFrame with columns ['timestamp', 'value']
                       Must be sorted by timestamp and have regular intervals
            entity_id: Identifier of the entity (server_id, service_name, etc.)
            metric_name: Name of the metric (cpu_usage_percent, etc.)

        Returns:
            ModelComponents containing the trained model parameters
        """
        pass

    @abstractmethod
    def predict(
        self, current_value: float, timestamp: datetime, model: ModelComponents
    ) -> DetectionResult:
        """Detect if the current value is an anomaly

        Args:
            current_value: The observed metric value
            timestamp: Timestamp of the observation
            model: Pre-trained model components

        Returns:
            DetectionResult containing anomaly flag, score, and details
        """
        pass

    @abstractmethod
    def get_config(self) -> dict[str, Any]:
        """Get the current configuration of this method"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the detection method"""
        pass

    def validate_timeseries(self, timeseries: pd.DataFrame) -> None:
        """Validate that the timeseries has the required format

        Args:
            timeseries: DataFrame to validate

        Raises:
            ValueError: If the timeseries is invalid
        """
        if timeseries.empty:
            raise ValueError("Timeseries is empty")

        required_columns = ["timestamp", "value"]
        missing = set(required_columns) - set(timeseries.columns)
        if missing:
            raise ValueError(f"Timeseries missing required columns: {missing}")

        if timeseries["value"].isna().all():
            raise ValueError("Timeseries has no valid values")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.get_config()})"
