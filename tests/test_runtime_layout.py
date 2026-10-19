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


def test_ci_uses_pinned_runtime_lockfile_and_project_test_command():
    workflow = (ROOT/'.github'/'workflows'/'ci.yml').read_text()
    assert "python-version: '3.11.9'" in workflow
    assert 'python -m pip install --requirement requirements.lock' in workflow
    assert 'run: make test' in workflow
    assert 'pip install -r requirements.txt' not in workflow


def test_setup_and_readme_default_to_locked_dependencies():
    setup = (ROOT/'setup.py').read_text()
    readme = (ROOT/'README.md').read_text(encoding='utf-8')
    assert 'requirements.lock' in setup
    assert 'requirements.txt' not in setup
    assert 'pip install --requirement requirements.lock' in readme
