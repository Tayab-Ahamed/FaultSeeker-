"""Leakage-safe grouped five-fold OOF evaluation for candidate generation.

Only the saved 110-row provider-pinned population is read.  The evaluator does
not enumerate or open any Batch B or Batch C result directory.  Candidate
generation is row-local; the score-weight grid is selected from training rows
inside each fold and then applied once to that fold's test rows.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sys
from typing import Iterable, Mapping
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import load_ground_truth, rank_of_first_hit
from benchmark.honest_eval import localization
from faultseeker.function_analysis.candidate_generation import generate_saved_candidates
from faultseeker.function_analysis.function_ranker import canonical_call_label, rerank_saved_predictions


MANIFEST = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json"
CLASSIFICATION = ROOT / "benchmark/original_faultseeker/benchmark_classification.csv"
GROUND_TRUTH = ROOT / "benchmark/original_faultseeker/ground_truth"
OUTPUT = ROOT / "reports/research_results/candidate_generation_cv_reviewed_20261018.json"
FOLDS = 5
SEED = 20261018

FEATURES = (
    "trace_evidence",
    "count",
    "depth",
    "proxy",
    "saved_rank",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _directory_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(path.glob("*.json")):
        digest.update(child.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _incident_keys(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value or "[]")
    except (SyntaxError, ValueError):
        parsed = []
    if isinstance(parsed, str):
        parsed = [parsed]
    urls = sorted(str(item).strip().lower() for item in parsed if str(item).strip())
    return urls


def _contract_keys(target) -> list[str]:
    return sorted({address.lower() for address, _ in
                   set(target.functions) | set(getattr(target, "lines", set()))})


def _load_targets() -> dict:
    """Use public selector evidence only; GT vocabulary never enriches matching."""
    localization._SELECTOR_TO_NAMES.clear()
    localization._load_api_selector_cache()
    with patch.object(localization, "_register_fn_names", lambda names: None):
        return {target.txn_hash.lower(): target for target in load_ground_truth(str(GROUND_TRUTH))}


class _UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[right] = left


def grouped_rows(rows: list[dict], targets: Mapping[str, object]) -> dict[str, list[int]]:
    """Build connected groups so incident and target-contract groups stay whole."""
    classification: dict[str, dict] = {}
    with CLASSIFICATION.open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            classification[item["txn_hash"].lower()] = item

    union_find = _UnionFind(len(rows))
    members: dict[tuple[str, str], list[int]] = {}
    for index, row in enumerate(rows):
        txn = row["txn_hash"].lower()
        keys = [("incident", url) for url in _incident_keys(
            classification.get(txn, {}).get("analysis", ""))]
        keys += [("contract", address) for address in _contract_keys(targets[txn])]
        name = str(getattr(targets[txn], "name", "") or "").strip().lower()
        if name:
            keys.append(("name", name))
        for key in keys:
            members.setdefault(key, []).append(index)
    for indexes in members.values():
        for index in indexes[1:]:
            union_find.union(indexes[0], index)

    components: dict[int, list[int]] = {}
    for index in range(len(rows)):
        components.setdefault(union_find.find(index), []).append(index)
    return {
        f"group-{min(indexes):03d}": sorted(indexes)
        for indexes in sorted(components.values(), key=lambda item: min(item))
    }


def assign_folds(groups: Mapping[str, list[int]]) -> dict[int, int]:
    """Greedily balance connected groups with deterministic hash tie-breaking."""
    fold_sizes = [0] * FOLDS
    assignment: dict[int, int] = {}
    ordered = sorted(
        groups.items(),
        key=lambda item: (
            -len(item[1]),
            hashlib.sha256(f"{SEED}:{item[0]}".encode()).hexdigest(),
        ),
    )
    for group_id, indexes in ordered:
        fold = min(range(FOLDS), key=lambda item: (fold_sizes[item], item))
        for index in indexes:
            assignment[index] = fold
        fold_sizes[fold] += len(indexes)
    if set(assignment) != set(range(sum(len(item) for item in groups.values()))):
        raise AssertionError("fold assignment omitted a row")
    return assignment


def _candidate_features(candidate: Mapping[str, object], saved_rank: int) -> dict[str, float]:
    depths = [
        depth for depth in list(candidate.get("supporting_call_depths") or [])
        if isinstance(depth, (list, tuple))
    ]
    return {
        "trace_evidence": min(1.0, float(candidate.get("trace_evidence_count") or 0) / 3.0),
        "count": min(1.0, float(candidate.get("count") or 0) / 20.0),
        "depth": min(1.0, float(max((len(depth) for depth in depths), default=0)) / 8.0),
        "proxy": 1.0 if candidate.get("proxy_resolved") else 0.0,
        "saved_rank": 1.0 / float(max(1, saved_rank)),
    }


def prepare_row(row: Mapping[str, object]) -> list[tuple[dict, dict[str, float], int]]:
    predictions = list(row.get("predictions") or [])
    generated = generate_saved_candidates(
        predictions,
        str((row.get("cast") or {}).get("output_tail") or ""),
    )
    # The persisted position is an evidence feature, never a label feature.
    original_keys = []
    for item in predictions:
        address = str(
            item.get("code_address")
            or item.get("address")
            or item.get("contract")
            or item.get("callee")
            or ""
        ).strip().lower()
        function = canonical_call_label(
            str(item.get("function_name") or item.get("name") or item.get("function") or "")
        )
        original_keys.append((address, function))
    prepared = []
    for candidate in generated:
        key = (str(candidate.get("code_address") or "").lower(), str(candidate.get("function") or ""))
        saved_rank = original_keys.index(key) + 1 if key in original_keys else len(original_keys) + 1
        prepared.append((candidate, _candidate_features(candidate, saved_rank), saved_rank))
    return prepared


def _grid() -> list[dict[str, float]]:
    # Feature weights are chosen only by training-fold labels.  The zero vector
    # is the deterministic first candidate and is intentionally retained.
    values = (0.0, 0.5, 1.0)
    configs = []
    for feature_values in itertools.product(values, repeat=len(FEATURES) - 1):
        for saved_rank in (0.0, 1.0, 2.0, 4.0):
            configs.append(dict(zip(
                ("trace_evidence", "count", "depth", "proxy"), feature_values
            )) | {"saved_rank": saved_rank})
    return configs


def rank_prepared(prepared: list[tuple[dict, dict[str, float], int]], config: Mapping[str, float]) -> list[dict]:
    scored = []
    for encounter, (candidate, features, saved_rank) in enumerate(prepared):
        score = sum(float(config[name]) * features[name] for name in FEATURES)
        scored.append((score, encounter, saved_rank, features, candidate))
    scored.sort(key=lambda item: (-item[0], item[1]))
    result = []
    for rank, (score, _, _, _, candidate) in enumerate(scored, 1):
        item = dict(candidate)
        item["rank"] = rank
        item["candidate_generation_score"] = score
        result.append(item)
    return result


def _metric(rows: Iterable[dict], ranks: Mapping[str, int | None], *, k20: bool = False) -> dict:
    rows = list(rows)
    values = [ranks[row["txn_hash"].lower()] for row in rows]
    result = {"n": len(values)}
    for k in (1, 3, 5):
        hits = sum(rank is not None and rank <= k for rank in values)
        result[f"hits_at_{k}"] = hits
        result[f"recall_at_{k}"] = hits / len(values) if values else 0.0
    if k20:
        hits = sum(rank is not None and rank <= 20 for rank in values)
        result["hits_at_20"] = hits
        result["candidate_recall_at_20"] = hits / len(values) if values else 0.0
    return result


def _select_config(train_rows: list[dict], targets: Mapping[str, object], prepared: Mapping[str, list]) -> tuple[dict, dict]:
    best = None
    for ordinal, config in enumerate(_grid()):
        ranks = {
            row["txn_hash"].lower(): rank_of_first_hit(
                targets[row["txn_hash"].lower()], rank_prepared(prepared[row["txn_hash"].lower()], config), match="function"
            )
            for row in train_rows
        }
        metrics = _metric(train_rows, ranks, k20=True)
        # Candidate generation is a top-k change, so select the configuration
        # by the aggregate localization utility rather than sacrificing R@3/R@5
        # for a single R@1 gain.  All terms are computed on this training fold.
        objective = (
            metrics["hits_at_1"] + metrics["hits_at_3"] + metrics["hits_at_5"],
            metrics["hits_at_20"],
            metrics["hits_at_1"],
            metrics["hits_at_3"],
            metrics["hits_at_5"],
            -ordinal,
        )
        if best is None or objective > best[0]:
            best = (objective, config, metrics)
    assert best is not None
    return dict(best[1]), best[2]


def run(output: Path | None = OUTPUT) -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = [row for row in manifest["rows"] if row.get("status") == "ok"]
    if len(rows) != 110:
        raise SystemExit(f"expected exactly 110 successful rows, got {len(rows)}")
    rows.sort(key=lambda row: row["txn_hash"].lower())
    for row in rows:
        row["predictions"] = rerank_saved_predictions(list(row.get("predictions") or []))
    targets = _load_targets()
    if {row["txn_hash"].lower() for row in rows} - set(targets):
        raise SystemExit("saved row missing ground-truth target")

    groups = grouped_rows(rows, targets)
    fold_by_index = assign_folds(groups)
    if any(len({fold_by_index[index] for index in indexes}) != 1 for indexes in groups.values()):
        raise AssertionError("a connected incident/contract group was split")

    baseline = {
        row["txn_hash"].lower(): rank_of_first_hit(targets[row["txn_hash"].lower()], list(row.get("predictions") or []), match="function")
        for row in rows
    }
    prepared = {row["txn_hash"].lower(): prepare_row(row) for row in rows}
    oof: dict[str, int | None] = {}
    folds = []
    for fold in range(FOLDS):
        train = [row for index, row in enumerate(rows) if fold_by_index[index] != fold]
        test = [row for index, row in enumerate(rows) if fold_by_index[index] == fold]
        config, train_metrics = _select_config(train, targets, prepared)
        for row in test:
            txn = row["txn_hash"].lower()
            oof[txn] = rank_of_first_hit(targets[txn], rank_prepared(prepared[txn], config), match="function")
        test_metrics = _metric(test, {row["txn_hash"].lower(): oof[row["txn_hash"].lower()] for row in test}, k20=True)
        folds.append({"fold": fold, "train_n": len(train), "test_n": len(test), "config": config, "train_metrics": train_metrics, "test_metrics": test_metrics})

    result = {
        "population": 110,
        "grouping": "connected individual source-URL, incident-name, function/line-target address groups",
        "review_status": "exploratory corrected evaluator; no new held-out population scored",
        "baseline_ordering": "current production rerank_saved_predictions",
        "selector_matching": "public API cache only; GT name registration disabled",
        "folds": FOLDS,
        "seed": SEED,
        "grid_size": len(_grid()),
        "saved_evidence_only": True,
        "batch_b_and_c_read": False,
        "baseline": _metric(rows, baseline, k20=True),
        "oof_upgrade": _metric(rows, oof, k20=True),
        "fold_sizes": [sum(fold_by_index[index] == fold for index in range(len(rows))) for fold in range(FOLDS)],
        "groups": len(groups),
        "fold_results": folds,
        "input_sha256": {
            "manifest": _sha256(MANIFEST),
            "classification": _sha256(CLASSIFICATION),
            "ground_truth": _directory_sha256(GROUND_TRUTH),
            "public_selector_cache": _sha256(Path(localization._SELECTOR_CACHE_PATH)),
            "production_ranker": _sha256(ROOT / "faultseeker/function_analysis/function_ranker.py"),
            "candidate_generator": _sha256(ROOT / "faultseeker/function_analysis/candidate_generation.py"),
            "evaluator": _sha256(Path(__file__)),
        },
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run()
