import argparse
import csv
import json
import os
from faultseeker.research.calibration import production_features


FEATURE_FIELDS = [
    "pattern_match",
    "code_evidence",
    "txn_consistency",
    "llm_confidence",
    "trace_entropy",
    "call_depth",
    "state_delta",
    "token_flow_anomaly",
    "label",
]


def features_from_result(result: dict, label: int) -> dict:
    confidence = _first_confidence(result)
    signals = result.get("signals", {}) or {}
    if label not in (0,1):
        raise ValueError('Binary adjudicated label required')
    return dict(production_features(confidence,signals),label=int(label))


def export_feature_rows(input_dir: str, output_csv: str, label: int) -> int:
    rows = []
    for name in sorted(os.listdir(input_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(input_dir, name), encoding="utf-8") as f:
            rows.append(features_from_result(json.load(f), label=label))

    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _first_confidence(result: dict) -> dict:
    scored = result.get("scored_functions") or []
    if not scored:
        return {}
    confidence = scored[0].get("confidence", {})
    return confidence.get("components", {}) if isinstance(confidence, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export calibration-ready feature rows from analysis JSON outputs.")
    parser.add_argument("--input-dir", default="data/output")
    parser.add_argument("--output", default="benchmark/calibration_features.csv")
    parser.add_argument("--label", type=int, default=1, help="1 for exploit rows, 0 for benign rows")
    args = parser.parse_args()
    count = export_feature_rows(args.input_dir, args.output, args.label)
    print(f"Exported {count} rows to {args.output}")


if __name__ == "__main__":
    main()
