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


def production_features(components, signals):
    """One feature contract for training export and production inference.

    The first four factors are the Equation 4 components; entropy/anomaly are
    normalized scores, call depth is trace depth, state delta is SSTORE count.
    Missing observations cannot silently become zero-valued training evidence.
    """
    debug = signals.get('debug', {})
    try:
        row = {name:components[name] for name in FEATURE_NAMES[:4]}
        row.update(trace_entropy=signals['trace_entropy'],call_depth=debug['call_depth_max'],
                   state_delta=debug['storage_events_total'],token_flow_anomaly=signals['token_flow_anomaly'])
        values = {name:float(value) for name,value in row.items()}
    except (KeyError,TypeError,ValueError) as error:
        raise ValueError('Missing genuine production confidence observations') from error
    if not all(math.isfinite(value) and value >= 0 for value in values.values()):
        raise ValueError('Production confidence observations must be finite and nonnegative')
    return values


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
        self.schema_id = "legacy-unspecified"
        self.training_ids = []
        self.evaluation_ids = []

    def require_schema(self, expected: str) -> None:
        if self.schema_id != expected or self.feature_names != FEATURE_NAMES or not self.trained:
            raise ValueError("Calibration schema is incompatible with production features")
        if any(not isinstance(ids,list) or not ids or any(not isinstance(item,str) or not item for item in ids)
               or len(set(ids)) != len(ids) for ids in (self.training_ids,self.evaluation_ids)):
            raise ValueError("Calibration schema requires disjoint training and evaluation provenance")
        if set(self.training_ids) & set(self.evaluation_ids):
            raise ValueError("Calibration provenance overlap")

    def fit_observations(self, rows, labels, training_ids, evaluation_ids, **kwargs):
        rows, labels = list(rows), list(labels)
        training_ids, evaluation_ids = list(training_ids), list(evaluation_ids)
        for identifiers in (training_ids, evaluation_ids):
            if not identifiers or any(not isinstance(item, str) or not item for item in identifiers):
                raise ValueError("Calibration requires nonempty observation identifiers")
            if len(set(identifiers)) != len(identifiers):
                raise ValueError("Duplicate calibration observation identifiers")
        if set(training_ids) & set(evaluation_ids):
            raise ValueError("Training and evaluation observation overlap")
        if len(training_ids) != len(rows) or self.feature_names != FEATURE_NAMES:
            raise ValueError("Calibration schema or observation count mismatch")
        if any(any(name not in row for name in FEATURE_NAMES) for row in rows):
            raise ValueError("Production schema requires every observed feature")
        if any(any(row[name] is None for name in FEATURE_NAMES) for row in rows):
            raise ValueError('Production schema requires numeric observations')
        if any(label not in (0, 1) for label in labels):
            raise ValueError("Calibration labels must be binary")
        self.fit(rows, labels, **kwargs)
        self.schema_id = "production-confidence-v1"
        self.training_ids, self.evaluation_ids = training_ids, evaluation_ids
        return self

    def fit(
        self,
        rows: Iterable[Dict[str, Any]],
        labels: Iterable[int],
        epochs: int = 600,
        learning_rate: float = 0.08,
        l2: float = 0.001,
    ) -> "LogisticConfidenceCalibrator":
        matrix = [self._raw_features(row) for row in rows]
        self.schema_id = "legacy-unspecified"
        self.training_ids, self.evaluation_ids = [], []
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
            "schema_id": self.schema_id,
            "training_ids": self.training_ids,
            "evaluation_ids": self.evaluation_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogisticConfidenceCalibrator":
        model = cls(data.get("feature_names", FEATURE_NAMES))
        model.weights = [float(v) for v in data.get("weights", model.weights)]
        model.bias = float(data.get("bias", 0.0))
        model.means = [float(v) for v in data.get("means", model.means)]
        model.scales = [float(v) for v in data.get("scales", model.scales)]
        model.trained = bool(data.get("trained", False))
        model.schema_id = data.get("schema_id", "legacy-unspecified")
        model.training_ids = data.get("training_ids", [])
        model.evaluation_ids = data.get("evaluation_ids", [])
        for values in (model.weights, model.means, model.scales):
            if len(values) != len(model.feature_names) or not all(math.isfinite(v) for v in values):
                raise ValueError("Calibration model dimensions and values must be finite and valid")
        if not math.isfinite(model.bias) or any(v <= 0 for v in model.scales):
            raise ValueError("Calibration scales must be positive and model values finite")
        if model.schema_id == "production-confidence-v1":
            model.require_schema(model.schema_id)
        return model

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "LogisticConfidenceCalibrator":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def _raw_features(self, row: Dict[str, Any]) -> List[float]:
        if self.schema_id == "production-confidence-v1" and any(name not in row for name in self.feature_names):
            raise ValueError("Production schema requires every observed feature")
        values = [float(row.get(name, 0.0) or 0.0) for name in self.feature_names]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Calibration features must be finite")
        return values

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
