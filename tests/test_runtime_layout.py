from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_copy_sources_all_exist():
    for line in (ROOT/'Dockerfile.benchmark').read_text().splitlines():
        if line.startswith('COPY '):
            for source in line.split()[1:-1]:
                assert (ROOT/source).exists(), source
