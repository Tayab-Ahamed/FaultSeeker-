# FaultSeeker++ submission reproduction guide

Run commands from the repository root with Python 3.11.9 and the pinned
`requirements.lock`. The commands below are offline unless explicitly marked
otherwise; no provider credentials or `.env` files are needed.

## Environment and software checks

```powershell
python --version
python -m pip install --requirement requirements.lock
python -m pytest tests/test_runtime_layout.py tests/test_cohort_manifest_validator.py -q -p no:cacheprovider
```

The Docker paths use `python:3.11.9-slim-bookworm` and `requirements.lock`.
Building the image requires Docker and an available package cache or network;
the current audit did not claim a Docker build.

## Claim and evidence checks

```powershell
python scripts/reproduce/claim_closure_ledger.py --root .
python scripts/reproduce/audit_calibration_cost_evidence.py --root .
python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root .
python -m benchmark.validate_cohort_manifest benchmark/versions/cohort_v3_20261016/cohort_manifest.json --root .
python -m benchmark.validate_cohort_manifest benchmark/versions/cohort_v4_20261016/cohort_manifest.json --root .
```

Expected scope:

- The calibration/cost audit exits `2` with blocked empirical status.
- The root cohort is valid as a manifest but remains `BLOCKED-BY-DATA` at
  14/246; v3 and v4 remain incomplete at 20/246 and 22/246.
- The claim ledger must contain zero `REPRODUCED_EMPIRICAL` rows until the
  external evidence plan has been satisfied.

## Historical offline numbers

```powershell
python scripts/reproduce/run_all.py
python scripts/reproduce/honest_f1.py
python scripts/reproduce/modeled_cost.py
python scripts/reproduce/localization.py
python scripts/reproduce/reentrancy_count.py
python scripts/reproduce/vulnerability_count.py
python scripts/reproduce/cohort.py
```

These commands recalculate retained historical aggregates. They do not validate
incident authenticity, independent labels, live provider quality, or held-out
generalization.

## Frozen Batch E

```powershell
python scripts/research/verify_batch_e_result.py
```

Expected result is `PASS` with the preserved address-only values R@1=14/40,
R@3=27/40, and R@5=33/40. Do not rerun the ranker or alter Batch E inputs.

## Current test status

Focused claim-closure tests pass. The full suite currently stops at
`tests/test_t3_evidence_audits.py::test_local_source_audit_is_network_free_and_keeps_adjudication_separate`
because the dirty source CSV contains 69 unresolved rows while the test
assertion requires at least 70. The clean source snapshot has 70; the dirty
derived files are stale. No row is added to force a pass.

## External completion requirements

See `EXTERNAL_EVIDENCE_ACQUISITION_PLAN.md` for the minimum authenticated
cohort, independent annotation, balanced detector evaluation, measured cost
workload, provider, localization, WAF, and guidance artifacts.
