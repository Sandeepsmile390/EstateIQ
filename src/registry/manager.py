"""
Model Registry Manager for Sustainable Facility Platform.
Maintains versioned model metadata, hyperparameter histories, metrics, and deployment statuses.
Allows multiple model versions to coexist seamlessly.
"""

import os
import json
import joblib
from datetime import datetime
from typing import Dict, Any, List

REGISTRY_FILE = "models/model_registry.json"

class ModelRegistryManager:
    def __init__(self, registry_file: str = REGISTRY_FILE):
        self.registry_file = registry_file
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        if os.path.exists(self.registry_file):
            with open(self.registry_file, "r") as f:
                return json.load(f)
        return {"models": {}}

    def register_model(
        self,
        model_id: str,
        task: str,
        algorithm: str,
        model_version: str,
        facility_type: str,
        features: List[str],
        hyperparameters: Dict[str, Any],
        metrics: Dict[str, Any],
        validation_method: str = "Chronological Split 70/15/15",
        status: str = "ACTIVE"
    ) -> Dict[str, Any]:
        """Registers new model version into metadata registry."""
        record = {
            "model_id": model_id,
            "model_version": model_version,
            "task": task,
            "facility_type": facility_type,
            "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_version": "v1.0_synthetic",
            "features": features,
            "algorithm": algorithm,
            "hyperparameters": hyperparameters,
            "metrics": metrics,
            "validation_method": validation_method,
            "status": status
        }
        self.registry["models"][model_id] = record
        with open(self.registry_file, "w") as f:
            json.dump(self.registry, f, indent=2)
        print(f"[Model Registry] Successfully registered {model_id}")
        return record

    def list_models() -> List[Dict[str, Any]]:
        return list(self.registry["models"].values())

    def get_model_metadata(self, model_id: str) -> Dict[str, Any]:
        return self.registry["models"].get(model_id, {})
