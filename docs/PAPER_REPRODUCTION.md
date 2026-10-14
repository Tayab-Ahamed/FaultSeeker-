# Reproducing paper claims locally

The paper is unchanged. A passing fixture proves code behavior, not a historical
transaction, a published percentage, a provider's current price, or model quality.

Run from this project's inner directory:

```powershell
python scripts/reproduce_paper.py
python scripts/replay_evm_fixtures.py --check
```

The first command runs real pytest, writes JUnit evidence and audits every cohort
row. Results are in `reports/local_verification/claim_report.md` and JSON. The
strict `--require-paper-verification` option exits nonzero while any external or
empirical claim remains unverified. Original baseline test sources must remain
unchanged, and all 201 original cases must pass.

The second command returns `PENDING-TOOLS` until the actual compiler/EVM tools
exist. Set `SOLC_BINARY`, `ANVIL_BINARY`, `CAST_BINARY`, or `FOUNDRY_BIN`. Without
`--check`, the runner compiles all three sources, deploys six contracts, executes
attacks/guard/proxy transactions, and captures both callTracer and opcode logs.
Hand-authored opcode fixtures never count as compiled execution evidence.

## Authentic cohort gate

`benchmark.evidence_manifest.audit_dataset` audits every row;
`benchmark.build_paper_benchmark.freeze_cohort` refuses partial or padded cohorts.
Exactly 246 unique accepted rows are required. Each row needs:

- Correct chain/hash, captured transaction, receipt, complete raw trace and tracer configuration.
- Ground truth matching that transaction; exact adjudicated address/function findings are additionally required for localization experiments.
- Two independent publisher artifacts with content digests and two annotation reviewers.
- Canonical-block confirmation from two RPC providers, replay evidence, tool versions and acquisition digests.
- Adjudicated binary/reentrancy labels, vulnerability type and class for the corresponding experiment.

This checks artifact integrity and recorded attestations. It does not turn an old
`verified` string or syntactically valid hash into independently verified history.
The current legacy files lack those acquisition manifests, so publication-scale
claims remain `BLOCKED-BY-DATA` with per-row reasons and exact shortfalls.

## Measurements

```powershell
python -m benchmark.run_paper_experiments --cohort reports/cohort.json --experiment detectors --output reports/detectors.json
python -m benchmark.run_paper_experiments --cohort reports/cohort.json --experiment categories --output reports/categories.json
python -m benchmark.build_paper_tables --input reports/categories.json --output reports/categories.md
```

Detector variants execute different algorithms on the same captured inputs.
Tables use integer confusion matrices and actual receipt/trace observations.
Undefined denominators stay undefined. Category means are never fabricated.

Routing, prefilter and simulated-guidance experiments use the same public
production pipeline, with genuine configuration changes. They require
`--execute-live`, a dated sourced `--pricing-file`, and preregistered
`--selection-file`. Routing uses 100 selected transactions; guidance uses 20.
The independently benign prefilter pool has a preregistered `expected_n` and is
separate from the main 246-row exploit cohort. No study pool is padded to 246.
The routing workload records the 50/30/20 tier split explicitly. Guidance is
simulated and its policy must be recorded; it is not a practitioner study.
Variant execution order rotates across paired transactions. Record cache state
and host/model versions before interpreting latency or reproducing a publication.
Exploit detection and function localization are reported as distinct metrics.
Function quality uses exact adjudicated address/function identities.
Incomplete agent analyses are refused as measurements. An empty completed
finding set is distinct from a deterministic BENIGN triage verdict.

Prices must contain `units` (`USD per 1000000 tokens`), `verified_at`, `source_url`
and a `models` mapping containing positive finite `input` and `output` rates.
Built-in historical prices are explicitly unverified and cannot establish paper
cost savings. Failed calls and unknown usage retain conservative reservations.
Every direct or routed public cloud query uses the shared durable $10 ledger;
SDK retries are disabled. `BudgetApprovalRequired` stops dispatch before the next
reserved call would exceed the cap. Tests use isolated temporary ledgers.

Live environment names: `DRPC_RPC_URL` (optionally a `{chain}` / `{api_key}` URL
template), `DRPC_API_KEY`, `OLLAMA_HOST`, and the selected provider's
`OPENAI_API_KEY`, `XAI_API_KEY`, `DASHSCOPE_API_KEY`, `GOOGLE_API_KEY`, or
`ANTHROPIC_API_KEY`. Verified source retrieval may require `ETHERSCAN_API_KEY`.
No credentials are committed. `benchmark.acquire_paper_evidence.capture_transaction`
captures matching canonical data from two independent hosts and requires a
successful Foundry replay before emitting a verification artifact.

Challenge recovery uses `benchmark.run_waf_experiment`, a preregistered
`WAF_CASES_JSON` case list, `CURL_IMPERSONATE_BINARY`, and `--execute-live`.
It records all attempts, recognizes actual challenge responses, and calculates
recoveries over challenged requests. RPC fallback is not relabelled as a WAF
challenge bypass. Missing browser transport or real challenged cases remains
pending; the claimed 23% is not an implementation constant.

## Numerical and semantic constraints

- Ordinary precision .89 and recall .83 cannot both round to those values with
  exactly 18 positives; the enumerator reports feasible integer matrices.
- Twenty single binary outcomes give 5-point accuracy increments. Reporting
  68% and 81% needs a different, explicitly defined aggregation.
- $0.039 compared with $0.060 is 35% savings. Measure the paired baseline.
- The structural cap .80 equals the literal CONFIRMED tier boundary .80. The
  fallback flag and evidence context remain explicit; the label is not storage
  proof. Authors must resolve any contrary interpretive statement themselves.
- Equation 4 is a relative heuristic score. Optional probability calibration
  requires the genuine production feature schema and disjoint provenance;
  legacy aggregate proxy models are rejected. Export and inference share one
  feature contract and missing observations cannot silently become zeros.
- BENIGN requires complete evidence. The conservative receipt path proves no
  token changes only when a verified receipt has no logs and a complete opcode
  capture has no writes. Complex token flows remain UNCERTAIN without decoding
  evidence; no 40% prefilter rate is promised by the implementation.

Kluster is waived for local development only. Before any PR or push, the
repository AGENTS.md rules apply in full and Kluster review must be re-enabled.
