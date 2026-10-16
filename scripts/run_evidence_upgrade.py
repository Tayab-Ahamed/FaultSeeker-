"""Run the evidence-separated synthetic and historical replay evaluation."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.evidence_upgrade import (  # noqa: E402
    DEFAULT_COMPILED_FIXTURE,
    DEFAULT_REPLAY_SUMMARIES,
    build_report,
    write_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/claim_evidence/evidence_upgrade.json",
    )
    parser.add_argument("--compiled-fixture", type=Path, default=DEFAULT_COMPILED_FIXTURE)
    parser.add_argument("--replay-summary", type=Path, action="append",
                        default=list(DEFAULT_REPLAY_SUMMARIES))
    args = parser.parse_args()
    report = build_report(args.compiled_fixture, args.replay_summary)
    write_report(args.output, report)
    print(f"synthetic_cases={len(report['synthetic']['cases'])}")
    print(f"historical_captures={report['real_replay']['summary']['captures_seen']}")
    print(f"valid_historical_captures={report['real_replay']['summary']['valid_captures']}")
    print(f"metric_eligible_real_captures={report['real_replay']['summary']['metric_eligible_captures']}")
    print(f"claim_gate={report['claim_gate']['real_population_metrics']}")
    print(f"report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
