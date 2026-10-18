"""Offline, grouped OOF address ranking on original110 evidence only.

No production integration or new batch. See the frozen Phase 1 protocol.
"""
from __future__ import annotations

import ast
from collections import defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from faultseeker.function_analysis.candidate_generation import parse_saved_trace_candidates
from faultseeker.function_analysis.function_ranker import rerank_saved_predictions

MANIFEST = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json"
GT = ROOT / "benchmark/original_faultseeker/ground_truth"
CLASSIFICATION = ROOT / "benchmark/original_faultseeker/benchmark_classification.csv"
OUTPUT = ROOT / "reports/address_ranking_phase1"
SEED = 20261018
VARIANTS = ("reciprocal_sum", "structural_grid", "delegate_context_grid")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_evidence(predictions: list[dict], trace_text: str) -> list[dict]:
    """Whitelisted row-local evidence only; labels/identifiers are not features."""
    groups = {}
    for rank, item in enumerate(predictions, 1):
        address = str(item.get("code_address") or item.get("address") or "").strip().lower()
        if not re.fullmatch(r"0x[0-9a-f]{40}", address):
            continue
        group = groups.setdefault(address, {"count": 0, "paths": set(), "reciprocals": []})
        group["count"] += max(0, int(item.get("count") or 0))
        group["reciprocals"].append(1 / rank)
        for path in item.get("supporting_call_depths") or []:
            if isinstance(path, (tuple, list)):
                group["paths"].add(tuple(path))
    raw = []
    for address, group in groups.items():
        paths = group["paths"]
        parents = {p[:-1] for p in paths if p}
        raw.append({"address": address, "best_reciprocal": max(group["reciprocals"]),
                    "reciprocal_sum": sum(group["reciprocals"]),
                    "count": math.log1p(group["count"]),
                    "depth": max((len(p) for p in paths), default=0),
                    "concentration": math.log1p(group["count"] / max(1, len(parents))),
                    "terminal_fanout": len(paths)})
    maxima = {key: max((r[key] for r in raw), default=0) for key in
              ["reciprocal_sum", "count", "depth", "concentration", "terminal_fanout"]}
    neighbors = defaultdict(set)
    for call in parse_saved_trace_candidates(trace_text):
        left, right = call.get("proxy_address"), call["address"]
        if call["call_type"] == "delegatecall" and left in groups and right in groups and left != right:
            neighbors[left].add(right)
            neighbors[right].add(left)
    normalized_sum = {r["address"]: r["reciprocal_sum"] / maxima["reciprocal_sum"] for r in raw}
    evidence = []
    for r in raw:
        norm = lambda key: r[key] / maxima[key] if maxima[key] else 0.0
        evidence.append({"address": r["address"], "best_reciprocal": r["best_reciprocal"],
                         "reciprocal_sum": norm("reciprocal_sum"),
                         "structural": (norm("count") + norm("depth") + norm("concentration")) / 3,
                         "terminal_fanout": norm("terminal_fanout"),
                         "delegate_neighbor": max((normalized_sum[a] for a in neighbors[r["address"]]), default=0.)})
    return evidence


def connected_groups(rows):
    parent = list(range(len(rows)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    first = {}
    for i, row in enumerate(rows):
        keys = [("tx", row["tx"])]
        if row["incident"]:
            keys.append(("incident", row["incident"]))
        keys += [("contract", row.get("chain", ""), a) for a in row["targets"]]
        keys += [("url", u) for u in row["urls"]]
        for key in keys:
            if key in first:
                parent[find(i)] = find(first[key])
            else:
                first[key] = i
    groups = defaultdict(list)
    for i in range(len(rows)):
        groups[find(i)].append(i)
    return sorted(groups.values(), key=min)


def assign_folds(groups):
    sizes, assignments = [0] * 5, {}
    for indexes in sorted(groups, key=lambda g: (-len(g), hashlib.sha256(f"{SEED}:{min(g)}".encode()).hexdigest())):
        fold = min(range(5), key=lambda f: (sizes[f], f))
        for i in indexes:
            assignments[i] = fold
        sizes[fold] += len(indexes)
    return assignments


def configs(variant):
    if variant == "reciprocal_sum":
        return [{"kind": "reciprocal_sum"}]
    delta = (0., .5, 1.) if variant == "delegate_context_grid" else (0.,)
    return [{"alpha": a, "beta": b, "gamma": g, "delta": d}
            for a, b, g, d in itertools.product((0., .5, 1.), (0., .5, 1.), (0., .5, 1.), delta)]


def rank_addresses(evidence, config):
    def score(item):
        if config.get("kind") == "reciprocal_sum":
            return item["reciprocal_sum"]
        return ((1-config["alpha"]) * item["best_reciprocal"] + config["alpha"] * item["reciprocal_sum"]
                + config["beta"] * item["structural"] - config["gamma"] * item["terminal_fanout"]
                + config["delta"] * item["delegate_neighbor"])
    return [item["address"] for _, item in sorted(enumerate(evidence), key=lambda p: (-score(p[1]), p[0]))]


def first_hit(addresses, targets):
    return next((rank for rank, address in enumerate(addresses, 1) if address in targets), None)


def hit_counts(ranks):
    return [sum(r is not None and r <= k for r in ranks) for k in (1, 3, 5)]


def choose_config(rows, train_indices, variant):
    best = None
    for config in configs(variant):
        ranks = [first_hit(rank_addresses(rows[i]["evidence"], config), rows[i]["targets"]) for i in train_indices]
        objective = tuple(hit_counts(ranks))
        if best is None or objective > best[0]:
            best = objective, config
    return dict(best[1])


def metrics(ranks):
    n, result = len(ranks), {}
    for k, hits in zip((1, 3, 5), hit_counts(ranks)):
        z = 1.959963984540054
        p = hits / n
        den = 1 + z*z/n
        center = (p + z*z/(2*n)) / den
        half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
        result[f"R@{k}"] = {"hits": hits, "n": n, "recall": p,
                             "wilson95": [max(0., center-half), min(1., center+half)]}
    return result


def guard_event(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "http.client.connect"}:
        raise RuntimeError(f"Offline-only experiment blocked {event}")
    if event in {"open", "os.scandir", "os.listdir"} and args and isinstance(args[0], (str, bytes)):
        path = str(args[0]).replace("\\", "/").lower()
        if re.search(r"(?:^|/)reports/new_batches(?:/|$)", path):
            raise RuntimeError("Frozen/fresh batch access prohibited")


def install_offline_guard():
    sys.addaudithook(guard_event)


def read_rows():
    import csv
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = sorted([r for r in manifest["rows"] if r.get("status") == "ok"], key=lambda r: (r["txn_hash"], r["filename"]))
    if len(source) != 110:
        raise ValueError("Frozen110 population changed")
    fingerprints = {MANIFEST: sha(MANIFEST), CLASSIFICATION: sha(CLASSIFICATION)}
    with CLASSIFICATION.open(encoding="utf-8-sig", newline="") as handle:
        classification = {r["txn_hash"].lower(): r for r in csv.DictReader(handle)}
    rows = []
    for index, row in enumerate(source):
        path = GT / row["filename"]
        fingerprints[path] = sha(path)
        if fingerprints[path] != manifest["ground_truth_sha256"][row["filename"]]:
            raise ValueError("Frozen row-bound annotation changed")
        gt = json.loads(path.read_text(encoding="utf-8"))
        targets = set()
        for key, values in (gt.get("location") or {}).items():
            for item in [key] + list(values or []):
                parts = str(item).split("#")
                if len(parts) >= 3 and parts[-1].strip() and re.fullmatch(r"0x[0-9a-fA-F]{40}", parts[0].strip()):
                    targets.add(parts[0].strip().lower())
        if not targets:
            raise ValueError("No explicit target contract; do not silently drop record")
        try:
            urls = ast.literal_eval(classification.get(row["txn_hash"].lower(), {}).get("analysis") or "[]")
        except (ValueError, SyntaxError):
            urls = []
        if isinstance(urls, str):
            urls = [urls]
        # No persisted correctness/score field enters the ranking adapter.
        allowed = ("code_address", "address", "function", "function_name", "count", "supporting_call_depths")
        predictions = [{k: p[k] for k in allowed if k in p} for p in row.get("predictions") or []]
        production = rerank_saved_predictions(predictions)
        evidence = extract_evidence(production, str((row.get("cast") or {}).get("output_tail") or ""))
        rows.append({"row_id": f"{index:03d}:{row['filename']}", "tx": row["txn_hash"].lower(), "chain": row["chain"],
                     "incident": re.sub(r"[^a-z0-9]", "", str(gt.get("name") or "").lower()),
                     "targets": sorted(targets), "urls": sorted({str(u).strip().lower() for u in urls if str(u).strip()}),
                     "evidence": evidence,
                     "function_slot_rank": first_hit([p["code_address"] for p in production], targets)})
    return rows, fingerprints


def run():
    install_offline_guard()
    destination = OUTPUT / "results.json"
    if destination.exists():
        raise RuntimeError("Experiment already recorded; do not overwrite")
    rows, fingerprints = read_rows()
    fingerprints[OUTPUT / "PROTOCOL.md"] = sha(OUTPUT / "PROTOCOL.md")
    fingerprints[Path(__file__)] = sha(Path(__file__))
    for relative in ["faultseeker/function_analysis/function_ranker.py", "faultseeker/function_analysis/candidate_generation.py"]:
        fingerprints[ROOT / relative] = sha(ROOT / relative)
    groups = connected_groups(rows)
    fold_for = assign_folds(groups)
    audit = []
    for fold in range(5):
        train = [i for i in range(len(rows)) if fold_for[i] != fold]
        test = [i for i in range(len(rows)) if fold_for[i] == fold]
        record = {"fold": fold, "train_n": len(train), "test_n": len(test)}
        for field in ("tx", "incident", "targets", "urls"):
            def entities(indices):
                values = set()
                for i in indices:
                    item = rows[i][field]
                    for value in item if isinstance(item, list) else [item]:
                        if value:
                            values.add((rows[i]["chain"], value) if field == "targets" else value)
                return values
            record[field + "_crossings"] = len(entities(train) & entities(test))
            assert record[field + "_crossings"] == 0
        audit.append(record)
    baseline = [first_hit([r["address"] for r in row["evidence"]], row["targets"]) for row in rows]
    # Reweight only the already-produced OOF predictions for the unique sensitivity.
    unique, seen = [], set()
    for i, row in enumerate(rows):
        if row["tx"] not in seen:
            unique.append(i)
            seen.add(row["tx"])
    base_counts, unique_base = hit_counts(baseline), hit_counts([baseline[i] for i in unique])
    results = {}
    for variant in VARIANTS:
        ranks, folds = {}, []
        for fold in range(5):
            train = [i for i in range(len(rows)) if fold_for[i] != fold]
            test = [i for i in range(len(rows)) if fold_for[i] == fold]
            config = choose_config(rows, train, variant)
            for i in test:
                ranks[i] = first_hit(rank_addresses(rows[i]["evidence"], config), rows[i]["targets"])
            folds.append({"fold": fold, "config": config, "train_indices": train, "test_indices": test})
        ordered, unique_ranks = [ranks[i] for i in range(len(rows))], [ranks[i] for i in unique]
        delta = [a-b for a, b in zip(hit_counts(ordered), base_counts)]
        unique_delta = [a-b for a, b in zip(hit_counts(unique_ranks), unique_base)]
        eligible = min(delta) >= 0 and max(delta) > 0 and min(unique_delta) >= 0 and max(unique_delta) > 0
        results[variant] = {"metrics": metrics(ordered), "delta_hits": delta,
                            "unique109_reweighted_metrics": metrics(unique_ranks), "unique_delta_hits": unique_delta,
                            "eligible": eligible, "grid_size": len(configs(variant)), "folds": folds,
                            "oof_ranks": ordered}
    eligible = [name for name in VARIANTS if results[name]["eligible"]]
    selected = sorted(eligible, key=lambda name: tuple(-x for x in hit_counts(results[name]["oof_ranks"])) + (results[name]["grid_size"], name))[0] if eligible else None
    report = {"exploratory": True, "records": len(rows), "unique_transactions": len(unique), "seed": SEED,
              "groups": len(groups), "fold_audit": audit, "variant_selection": selected,
              "baseline_distinct_addresses": metrics(baseline),
              "baseline_function_slots_reference": metrics([r["function_slot_rank"] for r in rows]),
              "baseline_unique109_reweighted": metrics([baseline[i] for i in unique]),
              "candidate_coverage_records": sum(r is not None for r in baseline),
              "variants": results,
              "rows": [{k: row[k] for k in ("row_id", "tx", "chain", "incident", "targets", "urls")} |
                       {"fold": fold_for[i], "baseline_rank": baseline[i], "candidates": row["evidence"]}
                       for i, row in enumerate(rows)],
              "input_sha256": {p.relative_to(ROOT).as_posix(): h for p, h in fingerprints.items()},
              "network_calls": 0, "fresh_batches_read_or_created": 0, "commits": 0, "pushes": 0,
              "production_behavior_changed": False}
    assert all(sha(p) == h for p, h in fingerprints.items())
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"baseline": base_counts, "variants": {name: hit_counts(r["oof_ranks"]) for name, r in results.items()},
                      "selected": selected, "groups": len(groups), "fold_sizes": [a["test_n"] for a in audit]}))
    return report


if __name__ == "__main__":
    run()
