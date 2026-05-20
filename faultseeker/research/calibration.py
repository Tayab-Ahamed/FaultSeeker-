import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence


FEATURE_NAMES = [
    "pattern_match",
    "code_evidence",
    "txn_consistency",
    "llm_confidence",
    "trace_entropy",
    "call_depth",
    "state_delta",
    "token_flow_anomaly",
]


@dataclass
class CalibrationMetrics:
    brier_score: float
    expected_calibration_error: float
    bins: List[Dict[str, float]] = field(default_factory=list)


class LogisticConfidenceCalibrator:
    """Small dependency-free logistic calibrator for exploit probability."""

    def __init__(self, feature_names: Sequence[str] = FEATURE_NAMES):
        self.feature_names = list(feature_names)
        self.weights = [0.0 for _ in self.feature_names]
        self.bias = 0.0
        self.means = [0.0 for _ in self.feature_names]
        self.scales = [1.0 for _ in self.feature_names]
        self.trained = False

    def fit(
        self,
        rows: Iterable[Dict[str, Any]],
        labels: Iterable[int],
        epochs: int = 600,
        learning_rate: float = 0.08,
        l2: float = 0.001,
    ) -> "LogisticConfidenceCalibrator":
        matrix = [self._raw_features(row) for row in rows]
        y = [1 if int(label) else 0 for label in labels]
        if not matrix or len(matrix) != len(y):
            raise ValueError("Calibration training requires equal non-empty rows and labels")

        self._fit_scaler(matrix)
        x = [self._scale(values) for values in matrix]
        self.weights = [0.0 for _ in self.feature_names]
        self.bias = self._logit((sum(y) + 0.5) / (len(y) + 1.0))

        for _ in range(max(1, epochs)):
            grad_w = [0.0 for _ in self.feature_names]
            grad_b = 0.0
            for values, label in zip(x, y):
                pred = self._sigmoid(self.bias + sum(w * v for w, v in zip(self.weights, values)))
                err = pred - label
                grad_b += err
                for idx, value in enumerate(values):
                    grad_w[idx] += err * value

            n = float(len(x))
            self.bias -= learning_rate * grad_b / n
            for idx in range(len(self.weights)):
                grad = grad_w[idx] / n + l2 * self.weights[idx]
                self.weights[idx] -= learning_rate * grad

        self.trained = True
        return self

    def predict_proba(self, row: Dict[str, Any]) -> float:
        values = self._scale(self._raw_features(row))
        score = self.bias + sum(w * v for w, v in zip(self.weights, values))
        return self._sigmoid(score)

    def evaluate(self, rows: Iterable[Dict[str, Any]], labels: Iterable[int], bins: int = 10) -> CalibrationMetrics:
        probabilities = [self.predict_proba(row) for row in rows]
        y = [1 if int(label) else 0 for label in labels]
        if not probabilities or len(probabilities) != len(y):
            raise ValueError("Calibration evaluation requires equal non-empty rows and labels")

        brier = sum((p - label) ** 2 for p, label in zip(probabilities, y)) / len(y)
        bin_rows = self.reliability_bins(probabilities, y, bins=bins)
        ece = sum(item["weight"] * abs(item["accuracy"] - item["confidence"]) for item in bin_rows)
        return CalibrationMetrics(
            brier_score=round(brier, 6),
            expected_calibration_error=round(ece, 6),
            bins=bin_rows,
        )

    def reliability_bins(self, probabilities: Sequence[float], labels: Sequence[int], bins: int = 10) -> List[Dict[str, float]]:
        buckets = []
        total = len(probabilities)
        for idx in range(bins):
            low = idx / bins
            high = (idx + 1) / bins
            members = [
                (p, label)
                for p, label in zip(probabilities, labels)
                if low <= p < high or (idx == bins - 1 and p == 1.0)
            ]
            if not members:
                buckets.append({"low": low, "high": high, "count": 0, "weight": 0.0, "confidence": 0.0, "accuracy": 0.0})
                continue
            confidence = sum(p for p, _ in members) / len(members)
            accuracy = sum(label for _, label in members) / len(members)
            buckets.append(
                {
                    "low": round(low, 4),
                    "high": round(high, 4),
                    "count": len(members),
                    "weight": len(members) / total,
                    "confidence": round(confidence, 6),
                    "accuracy": round(accuracy, 6),
                }
            )
        return buckets

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_names": self.feature_names,
            "weights": self.weights,
            "bias": self.bias,
            "means": self.means,
            "scales": self.scales,
            "trained": self.trained,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogisticConfidenceCalibrator":
        model = cls(data.get("feature_names", FEATURE_NAMES))
        model.weights = [float(v) for v in data.get("weights", model.weights)]
        model.bias = float(data.get("bias", 0.0))
        model.means = [float(v) for v in data.get("means", model.means)]
        model.scales = [float(v) or 1.0 for v in data.get("scales", model.scales)]
        model.trained = bool(data.get("trained", False))
        return model

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "LogisticConfidenceCalibrator":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def _raw_features(self, row: Dict[str, Any]) -> List[float]:
        return [float(row.get(name, 0.0) or 0.0) for name in self.feature_names]

    def _fit_scaler(self, matrix: List[List[float]]) -> None:
        n = len(matrix)
        self.means = [sum(row[idx] for row in matrix) / n for idx in range(len(self.feature_names))]
        self.scales = []
        for idx, mean in enumerate(self.means):
            variance = sum((row[idx] - mean) ** 2 for row in matrix) / n
            self.scales.append(math.sqrt(variance) or 1.0)

    def _scale(self, values: List[float]) -> List[float]:
        return [(value - mean) / scale for value, mean, scale in zip(values, self.means, self.scales)]

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            z = math.exp(-value)
            return 1.0 / (1.0 + z)
        z = math.exp(value)
        return z / (1.0 + z)

    @staticmethod
    def _logit(probability: float) -> float:
        p = min(1.0 - 1e-9, max(1e-9, probability))
        return math.log(p / (1.0 - p))
