"""EstateIQ Synthetic Data Generator V2 Package.

Provides enhanced physics-based simulation with multi-mode fault injection,
clean chronological split support, and structured event metadata tracking.
"""

from src.data_generator_v2.fault_injection import (
    FaultScenario,
    GroundTruthEvent,
    inject_fault_scenarios,
)
from src.data_generator_v2.generator_v2 import DatasetGeneratorV2
from src.data_generator_v2.validation_v2 import validate_v2_dataset

__all__ = [
    "FaultScenario",
    "GroundTruthEvent",
    "inject_fault_scenarios",
    "DatasetGeneratorV2",
    "validate_v2_dataset",
]

