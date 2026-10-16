"""Explicit separation of empirical, benign, fixture, and adversarial data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


VALID_KINDS = frozenset({"real_exploit", "real_benign", "fixture", "synthetic_adversarial"})
EMPIRICAL_KINDS = frozenset({"real_exploit", "real_benign"})


@dataclass(frozen=True)
class EvaluationSample:
    sample_id: str
    kind: str
    payload: Any = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(f"kind must be one of {sorted(VALID_KINDS)}")


class EvaluationPartition:
    def __init__(self, samples: Iterable[EvaluationSample] = ()):
        self.samples: list[EvaluationSample] = []
        for sample in samples:
            self.add(sample)

    def add(self, sample: EvaluationSample) -> None:
        if any(existing.sample_id == sample.sample_id for existing in self.samples):
            raise ValueError(f"duplicate sample id: {sample.sample_id}")
        self.samples.append(sample)

    def kinds(self) -> set[str]:
        return {sample.kind for sample in self.samples}

    def empirical(self) -> list[EvaluationSample]:
        return [sample for sample in self.samples if sample.kind in EMPIRICAL_KINDS]

    def assert_metric_eligible(self, *, allow_fixture: bool = False, allow_synthetic: bool = False) -> None:
        disallowed = {
            sample.kind for sample in self.samples
            if (sample.kind == "fixture" and not allow_fixture)
            or (sample.kind == "synthetic_adversarial" and not allow_synthetic)
        }
        if disallowed:
            raise ValueError("non-empirical samples cannot enter metrics: " + ", ".join(sorted(disallowed)))

    def metric_samples(self, *, allow_fixture: bool = False, allow_synthetic: bool = False) -> list[EvaluationSample]:
        self.assert_metric_eligible(allow_fixture=allow_fixture, allow_synthetic=allow_synthetic)
        return list(self.samples)

    def report(self) -> dict[str, Any]:
        return {
            "total": len(self.samples),
            "kinds": {kind: sum(sample.kind == kind for sample in self.samples) for kind in sorted(self.kinds())},
            "empirical_ids": [sample.sample_id for sample in self.empirical()],
            "synthetic_ids": [sample.sample_id for sample in self.samples if sample.kind == "synthetic_adversarial"],
        }
