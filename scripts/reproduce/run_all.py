"""Run every offline reproduction script and summarize its reported metrics."""

import re
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
REPORT = ROOT / "reports/reproducibility/FINAL_REPORT.md"
RESULT_RE = re.compile(
    r"^\s*(?P<metric>[A-Za-z0-9_.-]+): raw=.*?; expected=(?P<expected>[^;]+); "
    r"reproduced=(?P<reproduced>[^;]+); (?P<status>PASS|FAIL)\s*$"
)


def expected_values():
    """Read metric order and expected values from the scoped final report."""
    values = {}
    for line in REPORT.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) == 6 and cells[1] not in {"Metric", ""} and cells[3].isdigit():
            if cells[1] in values:
                raise ValueError(f"Duplicate expected metric: {cells[1]}")
            values[cells[1]] = cells[2]
    if not values:
        raise ValueError(f"No expected metrics found in {REPORT}")
    return values


def reproduction_scripts():
    """Return direct child reproduction scripts, excluding shared and runner code."""
    return sorted(
        path
        for path in SCRIPT_DIR.glob("*.py")
        if path.name not in {"common.py", Path(__file__).name, "claim_evidence.py"}
    )


def run_scripts():
    """Invoke scripts directly and collect their reported result lines."""
    results = {}
    failures = []
    for script in reproduction_scripts():
        completed = subprocess.run(
            [sys.executable, str(script), "--report", str(REPORT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        for line in completed.stdout.splitlines():
            match = RESULT_RE.match(line)
            if match:
                metric = match.group("metric")
                if metric in results:
                    failures.append(f"duplicate reported metric: {metric}")
                results[metric] = {
                    "expected": match.group("expected").strip(),
                    "reproduced": match.group("reproduced").strip(),
                    "status": match.group("status"),
                }
        if completed.returncode:
            failures.append(f"{script.name} exited with status {completed.returncode}")
    return results, failures


def print_table(expected, results, failures):
    """Print one compact table in the report's metric order."""
    rows = []
    for metric, report_value in expected.items():
        result = results.get(metric)
        if result is None:
            rows.append((metric, report_value, "<missing>", "FAIL"))
            failures.append(f"no reported result for {metric}")
            continue
        status = "PASS" if result["status"] == "PASS" and result["expected"] == report_value else "FAIL"
        if status == "FAIL":
            failures.append(f"reported result mismatch for {metric}")
        rows.append((metric, report_value, result["reproduced"], status))

    for metric in sorted(set(results) - set(expected)):
        rows.append((metric, "<not in report>", results[metric]["reproduced"], "FAIL"))
        failures.append(f"unexpected reported metric: {metric}")

    headers = ("Metric", "Expected", "Reproduced", "Result")
    widths = [max(len(headers[index]), *(len(row[index]) for row in rows)) for index in range(4)]
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def main():
    expected = expected_values()
    results, failures = run_scripts()
    print_table(expected, results, failures)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
