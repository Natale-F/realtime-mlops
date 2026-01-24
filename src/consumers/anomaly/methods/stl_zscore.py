"""
STL + Z-Score anomaly detection method.

This method decomposes time series into Trend + Seasonal + Residual components using STL,
then detects anomalies by computing z-scores on the residuals.

Workflow:
1. Training: Fit STL on historical data, extract trend/seasonal/residual statistics
2. Inference: For new data points, compute expected value (trend + seasonal),
   calculate residual, and compute z-score to detect anomalies
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import structlog
from statsmodels.tsa.seasonal import STL

from .base import AnomalyDetectionMethod, DetectionResult, ModelComponents

logger = structlog.get_logger(__name__)


@dataclass
class STLZScoreConfig:
    """Configuration for STL + Z-Score method"""

    seasonal_period: int = 288  # Period for seasonal component (288 = 24h in 5min buckets)
    trend_period: int = (
        577  # Period for trend smoothing (~2 days), must be > seasonal_period and odd
    )
    z_score_threshold: float = 3.0  # Threshold for anomaly detection (3 sigma)
    min_points: int = 2016  # Minimum points required (14 days × 288 points/day / 2)


class STLZScoreMethod(AnomalyDetectionMethod):
    """STL decomposition + Z-score on residuals for anomaly detection"""

    def __init__(self, config: dict):
        """Initialize with configuration

        Args:
            config: Dictionary with keys matching STLZScoreConfig fields
        """
        self.config = STLZScoreConfig(**config)
        self._name = "stl_zscore"

        logger.info(
            "STL Z-Score method initialized",
            seasonal_period=self.config.seasonal_period,
            z_score_threshold=self.config.z_score_threshold,
        )

    @property
    def name(self) -> str:
        return self._name

    def get_config(self) -> dict[str, Any]:
        return {
            "seasonal_period": self.config.seasonal_period,
            "trend_period": self.config.trend_period,
            "z_score_threshold": self.config.z_score_threshold,
            "min_points": self.config.min_points,
        }

    def fit(self, timeseries: pd.DataFrame, entity_id: str, metric_name: str) -> ModelComponents:
        """Fit STL model on historical timeseries

        Args:
            timeseries: DataFrame with ['timestamp', 'value']
            entity_id: Entity identifier
            metric_name: Metric name

        Returns:
            ModelComponents with extracted STL components
        """
        self.validate_timeseries(timeseries)

        if len(timeseries) < self.config.min_points:
            raise ValueError(
                f"Insufficient data points: {len(timeseries)} < {self.config.min_points}"
            )

        logger.debug(
            "Fitting STL model",
            entity_id=entity_id,
            metric_name=metric_name,
            n_points=len(timeseries),
        )

        # Prepare time series - STL doesn't need freq, just clean data
        timeseries["timestamp"] = pd.to_datetime(timeseries["timestamp"])
        ts = timeseries.set_index("timestamp")["value"].sort_index()
        ts = ts.dropna()

        # Infer aggregation interval from data
        if len(ts) > 1:
            time_diffs = ts.index.to_series().diff().dropna()
            median_interval_seconds = int(time_diffs.median().total_seconds())
        else:
            median_interval_seconds = 300  # Default to 5 minutes

        logger.debug(
            "Prepared timeseries for STL",
            entity_id=entity_id,
            metric_name=metric_name,
            total_points=len(ts),
            has_duplicates=ts.index.duplicated().any(),
            first_timestamp=ts.index[0] if len(ts) > 0 else None,
            last_timestamp=ts.index[-1] if len(ts) > 0 else None,
            interval_seconds=median_interval_seconds,
        )

        # Check we have enough points for the seasonal period
        if len(ts) < 2 * self.config.seasonal_period:
            raise ValueError(
                f"Insufficient points for STL: {len(ts)} < {2 * self.config.seasonal_period} "
                f"(need at least 2x seasonal_period)"
            )

        # Ensure seasonal period is odd (STL requirement)
        seasonal = self.config.seasonal_period
        if seasonal % 2 == 0:
            seasonal += 1
            logger.debug(
                "Adjusted seasonal period to be odd",
                original=self.config.seasonal_period,
                adjusted=seasonal,
            )

        try:
            stl = STL(
                ts,
                seasonal=seasonal,
                trend=self.config.trend_period,
                period=self.config.seasonal_period,  # Explicitly set period
            ).fit()
        except Exception as e:
            logger.error(
                "STL fit failed", entity_id=entity_id, metric_name=metric_name, error=str(e)
            )
            raise

        components = {
            # Store last seasonal cycle for lookup
            "seasonal_pattern": stl.seasonal[-self.config.seasonal_period :].tolist(),
            # Trend: store last value and slope for simple extrapolation
            "trend_last_value": float(stl.trend.iloc[-1]),
            "trend_slope": self._compute_trend_slope(stl.trend),
            "trend_last_timestamp": ts.index[-1].isoformat(),
            # Residual statistics
            "residual_mean": float(stl.resid.mean()),
            "residual_std": float(stl.resid.std()),
            # Store aggregation interval for proper extrapolation
            "interval_seconds": median_interval_seconds,
        }

        metadata = {
            "seasonal_period": self.config.seasonal_period,
            "trend_period": self.config.trend_period,
            "n_training_points": len(ts),
            "training_start": ts.index[0].isoformat(),
            "training_end": ts.index[-1].isoformat(),
        }

        logger.info(
            "STL model fitted",
            entity_id=entity_id,
            metric_name=metric_name,
            residual_std=round(components["residual_std"], 3),
            trend_slope=round(components["trend_slope"], 5),
        )

        return ModelComponents(
            method_name=self.name,
            entity_id=entity_id,
            metric_name=metric_name,
            components=components,
            trained_at=datetime.now().isoformat(),
            metadata=metadata,
        )

    def predict(
        self, current_value: float, timestamp: datetime, model: ModelComponents
    ) -> DetectionResult:
        """Predict if current value is an anomaly using STL components

        Args:
            current_value: Observed metric value
            timestamp: Timestamp of observation
            model: Trained model components

        Returns:
            DetectionResult with anomaly flag and details
        """
        comp = model.components

        # 1. Extrapolate trend
        trend_value = self._extrapolate_trend(timestamp, comp)

        # 2. Get seasonal component
        seasonal_index = self._get_seasonal_index(timestamp, comp)
        seasonal_value = comp["seasonal_pattern"][seasonal_index]

        # 3. Compute expected value
        expected = trend_value + seasonal_value

        # 4. Compute residual
        residual = current_value - expected

        # 5. Compute z-score
        z_score = (residual - comp["residual_mean"]) / comp["residual_std"]

        # 6. Detect anomaly
        is_anomaly = abs(z_score) > self.config.z_score_threshold

        # 7. Compute normalized score (0 to 1)
        # Map z-score to [0, 1] range: z=3 → 0.6, z=5 → 1.0
        score = min(1.0, abs(z_score) / 5.0)

        return DetectionResult(
            is_anomaly=is_anomaly,
            score=score,
            expected_value=expected,
            actual_value=current_value,
            details={
                "z_score": round(z_score, 4),
                "residual": round(residual, 4),
                "trend": round(trend_value, 4),
                "seasonal": round(seasonal_value, 4),
                "threshold": self.config.z_score_threshold,
            },
        )

    def _compute_trend_slope(self, trend: pd.Series) -> float:
        """Compute the slope of the trend for extrapolation

        Uses linear regression on the last 20% of trend points
        """
        # Take last 20% of points for slope estimation
        n = max(10, len(trend) // 5)
        recent_trend = trend.iloc[-n:]

        # Simple linear regression
        x = np.arange(len(recent_trend))
        y = recent_trend.values
        slope = np.polyfit(x, y, 1)[0]

        return float(slope)

    def _extrapolate_trend(self, timestamp: datetime, components: dict) -> float:
        """Extrapolate trend value to given timestamp

        Uses simple linear extrapolation: trend(t) = last_value + slope * time_diff
        """
        last_timestamp = pd.Timestamp(components["trend_last_timestamp"])
        time_diff_seconds = (timestamp - last_timestamp).total_seconds()

        # Convert to number of periods using actual interval from training
        interval_seconds = components.get("interval_seconds", 300)
        periods_diff = time_diff_seconds / interval_seconds

        trend_value = components["trend_last_value"] + components["trend_slope"] * periods_diff

        return trend_value

    def _get_seasonal_index(self, timestamp: datetime, components: dict) -> int:
        """Get the seasonal pattern index for given timestamp

        Maps timestamp to index in seasonal pattern (0 to seasonal_period-1)
        """
        # Get interval from components
        interval_seconds = components.get("interval_seconds", 300)
        interval_minutes = interval_seconds // 60

        # Calculate minutes since start of day
        minutes_since_midnight = timestamp.hour * 60 + timestamp.minute

        # Map to seasonal index using actual interval
        seasonal_period = len(components["seasonal_pattern"])
        seasonal_index = (minutes_since_midnight // interval_minutes) % seasonal_period

        return seasonal_index
