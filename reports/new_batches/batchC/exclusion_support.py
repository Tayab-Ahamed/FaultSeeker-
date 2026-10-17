"""Local, label-only incident exclusions for Batch C (Python 3.11+, stdlib).

API:
    get_exclusions(root) -> JSON-serializable dict, with sorted lists, counts,
        incident/alias provenance and SHA256 input fingerprints.
    matches_source(snapshot, source_path, text) -> list[str] of exclusion reasons.

Only ground-truth metadata, classification CSV, A/B candidate labels, B's source
manifest and B's builder *syntax* are read. Raw benchmark files are listed, never
opened. B's builder is never imported or executed. Missing/changed dataset inputs
fail closed. No result-bearing manifest is used to identify benchmark successes:
all 115 ground-truth incidents are forbidden regardless of benchmark success.

Previously screened B sources (including its phase-1 exclusions) are excluded
separately from its 20 selected labels. Address overlap is supporting evidence
only, never an independent exclusion. Alias matching uses complete normalized
incident stems, not substring matches against Solidity code or dependency names.

Run offline checks without creating bytecode files:
    python -B reports/new_batches/batchC/exclusion_support.py --self-test
Print a snapshot with this script's optional --root REPO argument (no files written).
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import posixpath
import re
import unittest
from pathlib import Path

__all__ = ["get_exclusions", "matches_source"]

_GT = "benchmark/original_faultseeker/ground_truth"
_CSV = "benchmark/original_faultseeker/benchmark_classification.csv"
_A = "reports/new_batches/batchA_candidates.json"
_B = "reports/new_batches/batchB/batchB_candidates.json"
_B_MANIFEST = "reports/new_batches/batchB/source_manifest.json"
_B_BUILDER = "reports/new_batches/batchB/build_batchB.py"
_RAW = ("reports/original_benchmark/provider-pinned/"
        "original-v1-pinned-sequential-20261017/raw")
_HASH = re.compile(r"(?<![a-zA-Z0-9_])0x[0-9a-f]{64}(?![a-zA-Z0-9_])", re.I)
_ADDRESS = re.compile(r"(?<![a-zA-Z0-9_])0x[0-9a-f]{40}(?![a-zA-Z0-9_])", re.I)
_TX_URL = re.compile(
    r"https?://[^\s\"'<>]*?/(?:tx|transaction)/(?:[a-z0-9_-]+/)?"
    r"(0x[0-9a-f]{64})(?![a-zA-Z0-9_])", re.I)
_LEX = re.compile(r'(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'
                  r'|(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)', re.M)
_TX_LABEL = re.compile(
    r"\b(?:(?:attack|exploit|example|hack)[\s_-]*(?:transactions?|txs?)"
    r"|(?:transactions?|txs?)(?:[\s_-]*(?:hash(?:es)?|ids?))?\s*[:=\-])", re.I)
_NON_ATTACK_TX = re.compile(
    r"\b(?:deploy(?:ment)?|creat(?:e|ion)|fund(?:ing)?|approv(?:al|e)|"
    r"rescue|whitehat|refund)[\s_-]+(?:transactions?|txs?)\b", re.I)

# Known alternate PoC names; do not equate CurveBurner with July's Vyper attack.
# Conic's ETH/crvUSD variants are deliberately one conservative incident family.
_ALIAS_GROUPS = (
    ("curve", "curvefinance", "curvevyper", "curvevyperreentrancy",
     "curveeth", "curvecrveth", "curvepeth", "curvealeth", "curvejpegd"),
    ("conic", "conicfinance", "conicethpool", "coniccrvusd", "coniceth",
     "conicfinanceeth", "conicfinancecrvusd"),
    ("unizen", "unizenio"),
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hash(value: object, where: str) -> str:
    _require(isinstance(value, str) and _HASH.fullmatch(value) is not None,
             f"Invalid transaction hash in {where}: {value!r}")
    return value.lower()


def _path(value: object) -> str:
    """Normalize repository paths, URLs and absolute local mirrors lexically."""
    value = str(value).strip().replace("\\", "/").split("?", 1)[0].split("#", 1)[0]
    value = posixpath.normpath(value).lower()
    marker = "/src/test/"
    if marker in value:
        value = "src/test/" + value.split(marker, 1)[1]
    return value


def _alias(value: str) -> str:
    value = _path(value).rsplit("/", 1)[-1]
    value = re.sub(r"\.sol$", "", value)
    # exp01, _2_exp, _attack_2 and numbered GT labels denote incident variants.
    value = re.sub(r"(?:[\s_.-]*(?:exp(?:loit)?|attack|poc|test)[\s_.-]*\d*)+$",
                   "", value, flags=re.I)
    value = re.sub(r"[\s_.-]+\d+$", "", value)
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _aliases(value: str) -> set[str]:
    alias = _alias(value)
    result = {alias} if alias else set()
    for group in _ALIAS_GROUPS:
        # Numbered family variants also appear without delimiters (Conic02).
        if alias in group or re.sub(r"\d+$", "", alias) in group:
            result.update(group)
    return result


def _strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def _addresses(value: object) -> set[str]:
    return {match.group().lower() for text in _strings(value)
            for match in _ADDRESS.finditer(text)}


def _attack_transactions(text: str) -> set[str]:
    """Explicit transaction URLs or labelled comments, never bytes32 constants.

    A labelled heading may continue onto adjacent hash-only comment lines. A
    different field, prose, blank line, or code ends that continuation. Strings
    are only considered if they contain an explicit transaction URL.
    """
    found: set[str] = set()
    active = False
    previous_end = -1
    for token in _LEX.finditer(text):
        if token.group("string") is not None:
            found.update(m.group(1).lower() for m in _TX_URL.finditer(token.group()))
            active = False
            continue
        gap = text[previous_end:token.start()] if previous_end >= 0 else ""
        if gap.strip() or gap.count("\n") > 1:
            active = False
        comment = token.group("comment")
        body = comment[2:-2] if comment.startswith("/*") else comment[2:]
        for line in body.split("\n"):
            line = line.strip().lstrip("*").strip()
            if not line or _NON_ATTACK_TX.search(line):
                active = False
                continue
            found.update(m.group(1).lower() for m in _TX_URL.finditer(line))
            label = _TX_LABEL.search(line)
            if label:
                found.update(m.group().lower() for m in _HASH.finditer(line[label.end():]))
                active = True
            elif active:
                hashes = list(_HASH.finditer(line))
                remainder = _HASH.sub("", line)
                if hashes and re.fullmatch(r"[\s,;:#\[\]()\d.\-]*", remainder):
                    found.update(m.group().lower() for m in hashes)
                else:
                    active = False
        previous_end = token.end()
    return found


def _builder_literals(text: str) -> tuple[list[dict], set[str] | None]:
    """Extract only allowlisted literal assignments; never evaluate Python calls."""
    tree = ast.parse(text, filename=_B_BUILDER)
    exclusions: list[dict] = []
    failed = None
    failed_names = {"benchmark_failed", "BENCHMARK_FAILED", "FAILED_HASHES",
                    "BENCHMARK_FAILED_HASHES", "FAILED_BENCHMARK_HASHES"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        else:
            continue
        names = {target.id for target in targets if isinstance(target, ast.Name)}
        if not (names & (failed_names | {"EXCLUSIONS"})) or value is None:
            continue
        try:
            literal = ast.literal_eval(value)
        except (ValueError, TypeError):
            _require("EXCLUSIONS" not in names, "B EXCLUSIONS must be a literal")
            continue  # e.g. a comprehension over a results-bearing manifest
        if "EXCLUSIONS" in names:
            _require(isinstance(literal, list) and all(isinstance(x, dict) for x in literal),
                     "Malformed B EXCLUSIONS")
            exclusions = literal
        if names & failed_names:
            _require(isinstance(literal, (list, tuple, set)), "Malformed failed-hash literal")
            candidate = {_hash(x, "B failed-hash literal") for x in literal}
            _require(failed is None or candidate == failed, "Conflicting failed-hash literals")
            failed = candidate
    return exclusions, failed


def get_exclusions(root: str | Path) -> dict:
    """Build a deterministic, JSON-safe snapshot from the allowlisted local inputs.

    ``forbidden_hashes`` is the union of GT filename/metadata hashes, CSV hashes,
    raw *filename* hashes, and all 40 A / all 20 B transaction labels. The
    ``benchmark110_hashes`` field is null when no literal five-failure set exists
    in B's builder. Its reported count is labelled separately, not invented.
    Fingerprints for files hash bytes; directory fingerprints hash sorted JSON
    filename arrays (not file contents). No absolute machine paths are retained.
    """
    root = Path(root)
    fingerprints: dict[str, dict] = {}

    def read_bytes(relative: str) -> bytes:
        content = (root / relative).read_bytes()
        fingerprints[relative] = {"kind": "file_bytes", "sha256": hashlib.sha256(content).hexdigest()}
        return content

    def read_json(relative: str) -> dict:
        data = json.loads(read_bytes(relative).decode("utf-8-sig"))
        _require(isinstance(data, dict), f"Expected JSON object: {relative}")
        return data

    def filenames(relative: str) -> list[str]:
        # iterdir rather than glob: a missing directory must not look empty.
        names = sorted(p.name for p in (root / relative).iterdir()
                       if p.name.lower().endswith(".json"))
        digest = hashlib.sha256(json.dumps(names, separators=(",", ":")).encode()).hexdigest()
        fingerprints[relative + "/"] = {"kind": "json_filenames_only", "sha256": digest,
                                           "count": len(names)}
        return names

    gt_names = filenames(_GT)
    _require(len(gt_names) == 115, "Expected all 115 GT metadata files")
    gt_filename_hashes = {_hash(Path(name).stem, _GT) for name in gt_names}
    gt_hashes = set(gt_filename_hashes)
    incidents: list[dict] = []
    alias_index: dict[str, set[str]] = {}
    address_index: dict[str, set[str]] = {}

    def add_incident(identifier: str, name: str, hashes: set[str], addresses: set[str],
                     source_paths: list[str], cause: str = "") -> None:
        aliases = _aliases(name)
        for path in source_paths:
            aliases.update(_aliases(path))
        incident = {"id": identifier, "name": name, "cause": cause,
                    "transaction_hashes": sorted(hashes), "target_addresses": sorted(addresses),
                    "source_paths": sorted(set(source_paths)), "aliases": sorted(aliases)}
        incidents.append(incident)
        for alias in aliases:
            alias_index.setdefault(alias, set()).add(identifier)
        for address in addresses:
            address_index.setdefault(address, set()).add(identifier)

    for filename in gt_names:
        relative = f"{_GT}/{filename}"
        data = read_json(relative)
        _require(isinstance(data.get("name"), str) and bool(data["name"].strip()),
                 f"Missing incident name: {relative}")
        _require(isinstance(data.get("transaction_hash"), list) and bool(data["transaction_hash"]),
                 f"Missing transaction_hash[]: {relative}")
        _require(isinstance(data.get("location"), dict), f"Missing GT location: {relative}")
        _require(isinstance(data.get("cause"), str), f"Missing GT cause: {relative}")
        hashes = {_hash(tx, relative) for tx in data["transaction_hash"]}
        hashes.add(_hash(Path(filename).stem, relative))
        gt_hashes.update(hashes)
        add_incident("ground_truth:" + Path(filename).stem.lower(), data["name"], hashes,
                     _addresses(data["location"]), [], data["cause"])

    classification = list(csv.DictReader(io.StringIO(read_bytes(_CSV).decode("utf-8-sig"))))
    csv_hashes = {_hash(row.get("txn_hash"), _CSV) for row in classification}
    _require(len(classification) == 115 and len(csv_hashes) == 115,
             "Expected 115 unique classification rows")
    _require(csv_hashes <= gt_hashes, "Classification hashes outside ground truth")
    raw_names = filenames(_RAW)
    raw_hashes = {_hash(Path(name).stem, _RAW) for name in raw_names}
    _require(len(raw_names) == 115 and len(raw_hashes) == 115,
             "Expected 115 unique raw benchmark filenames")
    _require(raw_hashes <= gt_hashes, "Raw filenames outside ground truth")

    label_hashes: dict[str, set[str]] = {}
    label_paths: dict[str, set[str]] = {}
    b_data = None
    for batch, relative, expected in (("batch_a", _A, 40), ("batch_b", _B, 20)):
        data = read_json(relative)
        rows = data.get("rows")
        _require(isinstance(rows, list) and len(rows) == expected,
                 f"Expected all {expected} labels in {relative}")
        label_hashes[batch], label_paths[batch] = set(), set()
        for number, row in enumerate(rows):
            _require(isinstance(row, dict), f"Malformed row in {relative}")
            tx = _hash(row.get("transaction_hash"), relative)
            source = row.get("source_path")
            _require(isinstance(source, str) and bool(source.strip()), f"Missing source in {relative}")
            source = _path(source)
            label_hashes[batch].add(tx)
            label_paths[batch].add(source)
            name = row.get("incident_name") or _alias(source)
            _require(isinstance(name, str), f"Invalid incident name in {relative}")
            # Label fields only: do not walk arbitrary manifest metadata/evidence.
            addresses = _addresses([row.get("vulnerable_contract"),
                                    row.get("vulnerable_contract_address")])
            add_incident(f"{batch}:{number + 1}", name, {tx}, addresses, [source])
        _require(len(label_hashes[batch]) == expected, f"Duplicate transaction labels in {relative}")
        if batch == "batch_b":
            b_data = data

    manifest = read_json(_B_MANIFEST)  # source provenance only, not benchmark manifests
    files = manifest.get("files")
    _require(isinstance(files, list) and bool(files), "Missing B source manifest paths")
    screened_paths: set[str] = set()
    by_basename: dict[str, set[str]] = {}
    for entry in files:
        _require(isinstance(entry, dict) and isinstance(entry.get("source_path"), str),
                 "Invalid B source manifest entry")
        source = _path(entry["source_path"])
        _require(source.startswith("src/test/"), "B source manifest path must be repository relative")
        screened_paths.add(source)
        by_basename.setdefault(source.rsplit("/", 1)[-1], set()).add(source)
    _require(label_paths["batch_b"] <= screened_paths, "B selected sources missing from source manifest")
    exclusions, failed_hashes = _builder_literals(read_bytes(_B_BUILDER).decode("utf-8-sig"))
    screened_exclusions = []
    for number, entry in enumerate(exclusions):
        _require(all(isinstance(entry.get(key), str) for key in ("file", "incident", "reason")),
                 "Malformed B phase-1 exclusion")
        paths = sorted(by_basename.get(_path(entry["file"]).rsplit("/", 1)[-1], set()))
        _require(bool(paths), "B excluded source missing from source manifest")
        screened_exclusions.append({"file": entry["file"], "incident": entry["incident"],
                                    "reason": entry["reason"], "source_paths": paths})
        add_incident(f"batch_b_screened_exclusion:{number + 1}", entry["incident"], set(), set(), paths)
    # Include source aliases even for a fetched source not in selected/excluded labels.
    for source in sorted(screened_paths - label_paths["batch_b"]):
        add_incident("batch_b_screened_source:" + source, _alias(source), set(), set(), [source])

    benchmark110 = None
    status = "unavailable_without_literal_failed_hashes; all_115_excluded"
    if failed_hashes is not None:
        _require(len(failed_hashes) == 5 and failed_hashes <= raw_hashes,
                 "Expected five literal failed hashes contained in raw filenames")
        benchmark110 = sorted(raw_hashes - failed_hashes)
        _require(len(benchmark110) == 110, "Expected benchmark110 after literal failures")
        status = "raw_filenames_minus_AST_literal_failed_hashes"
    reported = b_data.get("exclusion_policy", {}).get("benchmark_row_count")
    _require(reported == 110, "B labels no longer report benchmark110")
    forbidden = gt_hashes | csv_hashes | raw_hashes | label_hashes["batch_a"] | label_hashes["batch_b"]
    all_paths = label_paths["batch_a"] | label_paths["batch_b"] | screened_paths
    snapshot = {
        "schema_version": 1,
        "policy": {"ground_truth": "exclude_all_115_including_benchmark_failures",
                   "address_overlap": "supporting_evidence_only",
                   "batch_b_screened_sources": "excluded_including_phase1_rejections",
                   "attack_hashes": "explicit_transaction_URLs_or_labelled_comments_only"},
        "forbidden_hashes": sorted(forbidden),
        "ground_truth_hashes": sorted(gt_hashes),
        "ground_truth_filename_hashes": sorted(gt_filename_hashes),
        "classification_hashes": sorted(csv_hashes),
        "benchmark_raw_filename_hashes": sorted(raw_hashes),
        "benchmark110_hashes": benchmark110,
        "benchmark110_status": status,
        "benchmark110_reported_count": reported,
        "benchmark_failed_hashes": sorted(failed_hashes) if failed_hashes is not None else None,
        "batch_a_hashes": sorted(label_hashes["batch_a"]),
        "batch_b_hashes": sorted(label_hashes["batch_b"]),
        "batch_a_source_paths": sorted(label_paths["batch_a"]),
        "batch_b_source_paths": sorted(label_paths["batch_b"]),
        "batch_b_source_manifest_paths": sorted(screened_paths),
        "batch_b_phase1_exclusions": screened_exclusions,
        "source_paths": sorted(all_paths),
        "incident_aliases": {key: sorted(value) for key, value in sorted(alias_index.items())},
        "target_addresses": sorted(address_index),
        "target_address_incidents": {key: sorted(value) for key, value in sorted(address_index.items())},
        "incidents": incidents,
        "counts": {"ground_truth_files": len(gt_names), "ground_truth_hashes": len(gt_hashes),
                   "classification_rows": len(classification), "raw_benchmark_filenames": len(raw_names),
                   "benchmark110": len(benchmark110) if benchmark110 is not None else None,
                   "batch_a_rows": 40, "batch_b_rows": 20,
                   "batch_a_sources": len(label_paths["batch_a"]),
                   "batch_b_sources": len(label_paths["batch_b"]),
                   "batch_b_screened_sources": len(screened_paths),
                   "batch_b_phase1_exclusions": len(screened_exclusions),
                   "forbidden_hashes": len(forbidden), "source_paths": len(all_paths),
                   "incident_aliases": len(alias_index), "target_addresses": len(address_index)},
        "input_fingerprints": dict(sorted(fingerprints.items())),
    }
    return snapshot


def matches_source(snapshot: dict, source_path: str | Path, text: str) -> list[str]:
    """Return deterministic reasons; an empty list means no exclusion evidence.

    A selected/screened source is excluded even if it references a new attack
    transaction. Renamed/mirrored sources are checked by normalized incident
    stem as well. Addresses are appended only when some independent incident,
    path or explicit transaction reason already excludes the source.
    """
    source = _path(source_path)
    reasons = []
    for field, label in (("batch_a_source_paths", "batch_a_source"),
                         ("batch_b_source_paths", "batch_b_source"),
                         ("batch_b_source_manifest_paths", "batch_b_already_screened_source")):
        if source in snapshot[field]:
            reasons.append(f"{label}:{source}")
    for tx in sorted(_attack_transactions(text) & set(snapshot["forbidden_hashes"])):
        reasons.append(f"forbidden_attack_transaction:{tx}")
    for alias in sorted(_aliases(source)):
        ids = snapshot["incident_aliases"].get(alias)
        if ids:
            reasons.append(f"incident_alias:{alias}:" + ",".join(ids))
    if reasons:
        for address in sorted(_addresses(text) & set(snapshot["target_addresses"])):
            reasons.append(f"target_address_evidence_only:{address}")
    return reasons


class _SelfTests(unittest.TestCase):
    TX = "0x" + "a" * 64
    ADDRESS = "0x" + "b" * 40

    def snapshot(self):
        return {"forbidden_hashes": [self.TX], "batch_a_source_paths": ["src/test/2020-01/alpha_exp.sol"],
                "batch_b_source_paths": ["src/test/2020-02/beta_exp.sol"],
                "batch_b_source_manifest_paths": ["src/test/2020-02/beta_exp.sol",
                                                   "src/test/2020-03/screened_exp.sol"],
                "incident_aliases": {alias: ["ground_truth:test"] for name in
                                     ("Alpha", "Beta", "Conic Finance 02", "UnizenIO",
                                      "Curve Vyper reentrancy 1", "Screened") for alias in _aliases(name)},
                "target_addresses": [self.ADDRESS]}

    def test_explicit_attack_references(self):
        for text in (f"// Attack Tx: {self.TX}",
                     f"/* Attack Transaction:\n * {self.TX}\n */",
                     f"// Attack Tx\n// {self.TX}\n// {self.TX.upper()}",
                     f"// https://etherscan.io/tx/{self.TX}",
                     f' string url = "https://app.blocksec.com/explorer/tx/eth/{self.TX}";',
                     f"// Example tx - https://etherscan.io/tx/{self.TX}?foo=1"):
            with self.subTest(text=text):
                self.assertEqual(_attack_transactions(text), {self.TX})
                self.assertTrue(matches_source(self.snapshot(), "New_exp.sol", text))

    def test_constants_and_unrelated_comments_are_not_transactions(self):
        for text in (f"bytes32 constant TOKENS_RECIPIENT_INTERFACE_HASH = {self.TX};",
                     f"// bytes32 interface hash: {self.TX}", f"// {self.TX}",
                     f"// Attack Tx:\nbytes32 constant X = {self.TX};",
                     f"// Attack Tx:\n// Vulnerable Contract:\n// {self.TX}",
                     f"// Attack Tx:\n\n// {self.TX}",
                     f"// Deployment tx: https://etherscan.io/tx/{self.TX}",
                     f"// Attack Tx: 0x{'a' * 65}",
                     f' string constant note = "// Attack Tx: {self.TX}";'):
            with self.subTest(text=text):
                self.assertEqual(_attack_transactions(text), set())

    def test_paths_aliases_and_different_transactions(self):
        for path in ("src/test/2020-01/Alpha_exp.sol",
                     r"C:\mirror\src\test\2020-02\BETA_exp.sol",
                     "https://github.com/owner/repo/blob/pin/src/test/2020-03/Screened_exp.sol",
                     "other/Alpha_2_exp.sol", "Conic02_exp.sol", "ConicFinance_exp02.sol",
                     "Unizen_exp.sol", "Curve_exp03.sol", "Curve_2_exp.sol"):
            with self.subTest(path=path):
                self.assertTrue(matches_source(self.snapshot(), path, "// Attack Tx: 0x" + "c" * 64))
        self.assertEqual(matches_source(self.snapshot(), "CurveBurner_exp.sol", ""), [])
        self.assertEqual(matches_source(self.snapshot(), "UnrelatedAlpha_exp.sol", ""), [])

    def test_shared_router_is_not_an_exclusion(self):
        text = f"address router = {self.ADDRESS};"
        self.assertEqual(matches_source(self.snapshot(), "Fresh_exp.sol", text), [])
        self.assertTrue(any("evidence_only" in reason for reason in
                            matches_source(self.snapshot(), "Alpha_exp.sol", text)))

    def test_ast_never_executes_builder(self):
        text = ("raise RuntimeError('must not execute')\n"
                "EXCLUSIONS = [{'file':'x.sol','incident':'X','reason':'old'}]\n"
                "benchmark_failed = {x['txn_hash'] for x in forbidden_manifest['results']}\n")
        exclusions, failed = _builder_literals(text)
        self.assertEqual(exclusions[0]["incident"], "X")
        self.assertIsNone(failed)
        _, failed = _builder_literals(f"FAILED_HASHES = {{{self.TX!r}}}")
        self.assertEqual(failed, {self.TX})

    def test_real_inputs_and_read_boundary(self):
        # Inspect the actual dataset offline and enforce the read allowlist.
        from unittest.mock import patch

        root = _TEST_ROOT
        original = Path.read_bytes
        opened = []

        def guarded(path):
            relative = path.relative_to(root).as_posix()
            allowed = {_CSV, _A, _B, _B_MANIFEST, _B_BUILDER}
            self.assertTrue(relative in allowed or
                            (relative.startswith(_GT + "/") and relative.endswith(".json")), relative)
            opened.append(relative)
            return original(path)

        with patch.object(Path, "read_bytes", guarded):
            snapshot = get_exclusions(root)
        self.assertEqual(len(opened), 120)
        self.assertEqual(snapshot["counts"]["ground_truth_files"], 115)
        self.assertEqual(snapshot["counts"]["batch_a_rows"], 40)
        self.assertEqual(snapshot["counts"]["batch_b_rows"], 20)
        self.assertEqual(len(snapshot["ground_truth_filename_hashes"]), 115)
        self.assertTrue(set(snapshot["ground_truth_hashes"]) <= set(snapshot["forbidden_hashes"]))
        self.assertTrue(set(snapshot["benchmark_raw_filename_hashes"]) <= set(snapshot["forbidden_hashes"]))
        self.assertEqual(json.loads(json.dumps(snapshot)), snapshot)
        self.assertEqual(snapshot, get_exclusions(root))
        for incident in snapshot["incidents"]:
            for path in incident["source_paths"]:
                self.assertTrue(matches_source(snapshot, path, ""), path)
        for name in ("Conic_exp.sol", "ConicFinance02_exp.sol", "Curve_exp03.sol", "Unizen_exp.sol"):
            self.assertTrue(matches_source(snapshot, name, ""), name)


_TEST_ROOT = Path(__file__).resolve().parents[3]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_TEST_ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        _TEST_ROOT = args.root.resolve()
        unittest.main(argv=[__file__], verbosity=2)
    else:
        print(json.dumps(get_exclusions(args.root), indent=2, sort_keys=True))
