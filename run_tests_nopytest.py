"""Compatibility entry point using real pytest for trustworthy results."""
import sys
from pathlib import Path


def main():
    try:
        import pytest
    except ImportError:
        print('pytest is required; no reduced test runner is used.', file=sys.stderr)
        return 2
    arguments = sys.argv[1:] or [str(Path(__file__).resolve().parent/'tests'), '-q']
    return int(pytest.main(arguments))


if __name__ == '__main__':
    raise SystemExit(main())
