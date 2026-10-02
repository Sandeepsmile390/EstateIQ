"""
Baseline Predictive Models for Benchmarking.
Every ML task must start with a transparent, non-trainable baseline to establish the absolute minimum acceptable benchmark.
"""

import numpy as np

class NaiveMeanRegressor:
    """Predicts historical mean for regression tasks."""
    def __init__(self):
        self.mean_val = None

    def fit(self, X, y):
        self.mean_val = float(np.mean(y))

    def predict(self, X):
        return np.full(shape=(len(X),), fill_value=self.mean_val)

class PersistenceRegressor:
    """Predicts previous timestep value (last known observation) for time-series forecasting."""
    def fit(self, X, y):
        pass

    def predict_from_lag(self, lag_series: np.ndarray):
        return np.array(lag_series, dtype=float)

class MajorityClassClassifier:
    """Predicts majority class proportion for classification tasks."""
    def __init__(self):
        self.majority_prob = None

    def fit(self, X, y):
        self.majority_prob = float(np.mean(y))

    def predict_proba(self, X):
        probs = np.zeros((len(X), 2))
        probs[:, 1] = self.majority_prob
        probs[:, 0] = 1.0 - self.majority_prob
        return probs
