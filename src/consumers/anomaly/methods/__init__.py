"""
Anomaly detection methods registry and factory.
"""

from .base import AnomalyDetectionMethod, DetectionResult, ModelComponents
from .stl_zscore import STLZScoreMethod

# Registry of available methods
METHOD_REGISTRY = {
    "stl_zscore": STLZScoreMethod,
    # Future methods:
    # "stl_isolation": STLIsolationForestMethod,
    # "autoencoder": AutoencoderMethod,
    # "lstm": LSTMMethod,
}


def get_method(method_name: str, config: dict) -> AnomalyDetectionMethod:
    """Factory to create an anomaly detection method

    Args:
        method_name: Name of the method (e.g., 'stl_zscore')
        config: Configuration dict for the method

    Returns:
        Instance of the detection method

    Raises:
        ValueError: If method_name is not registered
    """
    if method_name not in METHOD_REGISTRY:
        available = ", ".join(METHOD_REGISTRY.keys())
        raise ValueError(f"Unknown method '{method_name}'. Available methods: {available}")

    method_class = METHOD_REGISTRY[method_name]
    return method_class(config)


def list_methods() -> list[str]:
    """List all available detection methods"""
    return list(METHOD_REGISTRY.keys())


__all__ = [
    "AnomalyDetectionMethod",
    "DetectionResult",
    "ModelComponents",
    "STLZScoreMethod",
    "get_method",
    "list_methods",
]
