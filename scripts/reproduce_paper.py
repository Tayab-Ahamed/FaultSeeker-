"""Run all local acceptance checks and emit the 31-claim evidence ledger."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.run_paper_verification import main

if __name__ == '__main__':
    raise SystemExit(main())
