"""Experiment artifact IO against a real historical capture, not metric proof."""
import json
from pathlib import Path


def test_experiment_reader_loads_real_compressed_historical_opcodes():
    from benchmark.run_paper_experiments import read_observed_artifact
    root = Path(__file__).resolve().parents[1] / 'reports/provenance_hunt/cohort'
    records = json.loads((root / 'records.json').read_text())
    record = next(row for row in records if row['txn_hash'] ==
        '0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6')
    trace = read_observed_artifact(record, 'trace', root)
    steps = trace['raw_trace']['opcode']['structLogs']
    assert trace['transaction_hash'] == record['txn_hash']
    assert len(steps) == 21300
    assert sum(step['op'] == 'SLOAD' for step in steps) == 80
    assert sum(step['op'] == 'SSTORE' for step in steps) == 29
    receipt = read_observed_artifact(record, 'receipt', root)
    assert receipt['transactionHash'] == record['txn_hash']
