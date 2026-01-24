"""
Anomaly Detection System

Autonomous, self-learning anomaly detection for datacenter metrics.

Architecture:
- Batch Training: Learns from historical data, extracts patterns (STL decomposition)
- Real-time Detection: Detects anomalies in streaming data using pre-trained models
- Pluggable Methods: Easy to add new detection algorithms (STL, IsolationForest, etc.)

Usage:
    # Train models on historical data
    python -m src.consumers.anomaly.train

    # Run real-time detection
    python -m src.consumers.anomaly.detect
"""

from .consumer import AnomalyConsumer
from .models import AnomalyConfig, AnomalyRecord
from .trainer import AnomalyTrainer

__all__ = ["AnomalyConsumer", "AnomalyTrainer", "AnomalyConfig", "AnomalyRecord"]
