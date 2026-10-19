from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_copy_sources_all_exist():
    for line in (ROOT/'Dockerfile.benchmark').read_text().splitlines():
        if line.startswith('COPY '):
            for source in line.split()[1:-1]:
                assert (ROOT/source).exists(), source


def test_benchmark_dockerfile_uses_pinned_runtime_and_lockfile():
    dockerfile = (ROOT/'Dockerfile.benchmark').read_text()
    assert 'FROM python:3.11.9-slim-bookworm' in dockerfile
    assert 'COPY requirements.lock setup.py pyproject.toml ./' in dockerfile
    assert 'python -m pip install --no-cache-dir --requirement requirements.lock' in dockerfile
    assert 'requirements.txt' not in dockerfile
