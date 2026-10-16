from common import COHORT, read_csv, run


def compute():
    """Count legacy vulnerability strings containing 'reentran', case-insensitively."""
    rows = read_csv(COHORT)
    print("Scope: label-string matches, not independently verified reentrancy incidents.")
    return {"reentrancy_label_count": sum("reentran" in r["vuln_type"].lower() for r in rows)}


if __name__ == "__main__":
    raise SystemExit(run(compute))
