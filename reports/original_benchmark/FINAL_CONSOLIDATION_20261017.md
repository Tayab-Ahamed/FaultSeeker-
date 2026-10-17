# Original FaultSeeker benchmark — final consolidation

**Scope:** documentation and existing evidence only.  
**Not performed:** scorer changes, paper edits, edits to existing claims files,
RPC, `cast`, benchmark reruns, provider calls, or push.

## 1. Protocol decision

The primary reported metric is **address + function identity**. The secondary
sensitivity metric is **function-only identity**. The complete rules,
normalization, selector handling, provenance boundary, and the 115-label/
114-unique-hash limitation are in:

`reports/original_benchmark/LOCALIZATION_SCORING_PROTOCOL_NOTE_20261017.md`

The authors did not publish their scorer. The imported public material does not
include the authors' per-transaction traces, ranked predictions, or evaluation
scripts; it contains the 115 label JSONs and the authors' runtime/ranking
source. Therefore, the function-only number below is explicitly a
**reconstruction**, not a reproduction of a hidden author evaluator.

## 2. Final saved-row benchmark results

The final provider-pinned manifest records **110 ok rows, 5 bounded timeouts,
and 14 replay mismatches**. Replay mismatches are valid trace results, not
failures.

### New measurement — all 115 denominator

| Metric | Original paper reported value | New measurement — primary address + function | New measurement — function-only sensitivity |
|---|---:|---:|---:|
| Recall@1 | 50.43% | 21.74% (25/115) | 23.48% (27/115) |
| Recall@3 | 73.91% | 42.61% (49/115) | 42.61% (49/115) |
| Recall@5 | 76.52% | 45.22% (52/115) | 46.09% (53/115) |

Every value in the two right-hand columns is labeled **new measurement**. The
paper values are retained only as the comparison baseline and are not claimed
to be reproduced.

### New measurement — valid-trace denominator, n=110

| Metric | Original paper reported value | New measurement — primary address + function | New measurement — function-only sensitivity |
|---|---:|---:|---:|
| Recall@1 | 50.43% | 22.73% (25/110) | 24.55% (27/110) |
| Recall@3 | 73.91% | 44.55% (49/110) | 44.55% (49/110) |
| Recall@5 | 76.52% | 47.27% (52/110) | 48.18% (53/110) |

### Scoring correction and strictness result

The saved predictions use `code_address`, while the scorer originally looked
for `address`/`contract`/`callee` and omitted `code_address`. That fixed bug
was corrected before this consolidation. It was a saved-row scoring fix only;
no traces or predictions were regenerated.

The strictness audit found the following on the 110 valid traces:

| Metric | Primary current rule | Function-only reconstruction |
|---|---:|---:|
| Recall@1 | 22.73% | 24.55% |
| Recall@3 | 44.55% | 44.55% |
| Recall@5 | 47.27% | 48.18% |

The combined Top-5 difference is **3 current misses → function-only hits** and
**2 current hits → function-only misses**. The first direction is caused by
function-name matches at a different address; the second is caused by current
selector-name resolution for two saved `0x2e1a7d4d` predictions. Full examples
and exact command output are in the strictness audit report.

### Provider and retry notes

- ETH and BSC resumed with **BlockPI pinned**.
- Four early rows from **dRPC** were preserved and were not rewritten.
- The retry pass attempted the genuinely failed primary rows at the lower
  compute-unit rate and recovered 15 of 20; 5 remained bounded failures.
- The retry pass overwrote most original failed raw rows. Original stderr for
  those overwritten failures cannot be reconstructed without inventing it.
  The retained manifest documents this limitation.

## 3. Consolidated 47-claim status table

This table is a documentation consolidation of existing evidence, not a new
claim decision. The 31 historical claim records are retained as H01–H31.
Sixteen non-duplicate current evidence claims are retained as E01–E16. Current
evidence items corresponding to the historical test/reproduction claims are
mapped to H02 and H30 rather than counted twice. This yields 47 consolidated
rows without inventing a new claim.

Status meanings used here:

- **backed** — the scoped/local or descriptive statement is supported by an
  existing artifact; this does not promote a broader paper sentence.
- **not backed** — retained evidence contradicts the broad claim or identifies
  it as unsupported.
- **pending credentials** — the required live provider/tool access is not
  available in the retained evidence.
- **not checkable** — the required authentic cohort, paired run, or source
  bundle is absent.

| ID | Consolidated claim | Status | Existing evidence / reason |
|---|---|---|---|
| H01 | Open source release | backed | `reports/claim_closure/claims/01.json`; cached upstream Apache-2.0 evidence. Local branch publication is not asserted. |
| H02 | 201 original tests pass | backed | `reports/claim_closure/claims/02.json`; original source hashes and local test evidence. |
| H03 | Authentic 246-row cohort | not checkable | `reports/claim_closure/claims/03.json`; 246 accepted cohort/provenance bundle absent. |
| H04 | Real transactions, two sources, annotations | not checkable | `claims/04.json`; complete independent source/annotation records absent. |
| H05 | Ten chains and Ethereum 47.6% | not backed | `PAPER_VS_REPO.md`; retained CSV has eight chains, not the claimed ten. |
| H06 | More than 80 vulnerability labels | not checkable | `claims/06.json`; adjudicated taxonomy is absent. |
| H07 | Published class proportions | not checkable | `claims/07.json`; authentic accepted cohort and frozen class protocol absent. |
| H08 | 18 reentrant incidents among 246 | not checkable | `claims/08.json`; cohort-wide independent binary annotation absent. |
| H09 | Storage-aware detector/guards/delegatecall | backed | `claims/09.json`; local mechanism tests pass within stated scope. |
| H10 | Five storage signal weights | backed | `claims/10.json`; executed local signal tests pass. |
| H11 | Five confidence tiers | backed | `claims/11.json`; boundary tests and profile activation pass. |
| H12 | Structural signals, .75 penalty, .80 cap | backed | `claims/12.json`; local fallback tests pass. |
| H13 | Detector precision/recall/F1 and baselines | not checkable | `claims/13.json`; no adjudicated evaluation cohort/raw Table V outcomes. |
| H14 | 17/29 percentage-point gains | not checkable | `claims/14.json`; paired detector outcomes absent. |
| H15 | Compound case study | not checkable | `claims/15.json`; exact transaction and trace/source linkage absent. |
| H16 | Query routing theta gate | backed | `claims/16.json`; local routing gate tests pass. |
| H17 | Six provider families | pending credentials | `claims/17.json`; live family conformance and reachable Ollama model absent. |
| H18 | 58% cost savings/100 paired transactions | not checkable | `claims/18.json`; authenticated paired workload, observed usage, and pricing snapshot absent. |
| H19 | Stage 1 makes no model calls | backed | `claims/19.json`; deterministic/keyless local tests pass. |
| H20 | BENIGN skip/EXPLOIT lock/UNCERTAIN escalation | backed | `claims/20.json`; local control-flow tests pass. |
| H21 | 40% benign prefilter/latency reduction | not checkable | `claims/21.json`; independently verified benign paired study absent. |
| H22 | Multi-agent function localization | pending credentials | `claims/22.json`; live model quality/source retrieval evidence absent. |
| H23 | Equation 4 confidence scoring | backed | `claims/23.json`; relative heuristic implementation is tested. |
| H24 | Evidence cards/HITL/guidance types | backed | `claims/24.json`; local guidance-state tests pass. |
| H25 | RPC EMA/cache/breakers/batching | pending credentials | `claims/25.json`; broader live dRPC/archive tracer capability absent. |
| H26 | Foundry replay extracts SLOAD/SSTORE | backed | `claims/26.json`; verified historical Ethereum sample and compiled fixtures, limited in scope. |
| H27 | 23% WAF challenge bypass | pending credentials | `claims/27.json` and `experiments/waf.json`; authorized challenge cases/transport absent. |
| H28 | Table VI category averages | not checkable | `claims/28.json`; production PMS/CES/TCS/LCS vectors absent. |
| H29 | 20-transaction guidance 68→81% | not checkable | `claims/29.json`; original/preregistered selection and paired outcomes absent. |
| H30 | Reproduction scripts | backed | `claims/30.json`; local workflow exists, but it does not reproduce unavailable paper studies. |
| H31 | Repository layout/runtime compatibility | backed | `claims/31.json`; local runtime/layout evidence. |
| E01 | 231-row authentic cohort | not backed | `CLAIMS_FINAL.md:17`; 231 frozen rows do not establish authentic incidents/annotations. |
| E02 | Chain composition/Ethereum share | backed | `CLAIMS_FINAL.md:19`; backed only as the frozen CSV descriptive count. |
| E03 | Vulnerability label/SWC mapping | backed | `CLAIMS_FINAL.md:20`; backed only as 82 strings, 36 mapped and 46 unmapped. |
| E04 | Stored complexity proportions | backed | `CLAIMS_FINAL.md:21`; backed only as stored CSV proportions. |
| E05 | 17 reentrancy label strings | backed | `CLAIMS_FINAL.md:22`; label-string count, not independently adjudicated incidents. |
| E06 | Table V F1=0.7586 as paper result | not backed | `CLAIMS_FINAL.md:23`; retained aggregate is a different feature-harness result. |
| E07 | Table V baselines comparable | not backed | `CLAIMS_FINAL.md:24`; saved local proxy aggregates are not the paper comparison. |
| E08 | All cohort entries real/labelled | not backed | `CLAIMS_FINAL.md:25`; field presence is not incident/label proof. |
| E09 | All named providers/chains supported | not backed | `CLAIMS_FINAL.md:26`; only limited observations exist. |
| E10 | 35% modeled cost saving | backed | `CLAIMS_FINAL.md:27`; safe wording is modeled arithmetic, not observed billing. |
| E11 | Future-work/limitations statement | backed | `CLAIMS_FINAL.md:28`; valid as a limitation/future-work statement, not a measured result. |
| E12 | Historical 6.1% localization summary | backed | `CLAIMS_FINAL.md:29`; saved historical aggregate only, not a fresh reproduction. |
| E13 | Eight-chain free RPC capability | not backed | `CLAIMS_FINAL.md:30`; retained probe does not establish universal capability. |
| E14 | WAF results support security conclusion | not backed | `CLAIMS_FINAL.md:31`; no retained WAF evaluation supports it. |
| E15 | Table VI comparison | not backed | `CLAIMS_FINAL.md:32`; no production vectors/averages. |
| E16 | 20-transaction guidance result | not backed | `CLAIMS_FINAL.md:33`; no paired selection/outcome artifact. |

### Nine retained pending external-run inputs

The evidence contains only three literal `PENDING-CREDENTIALS` claim statuses
(H17, H22, H25). To avoid inventing six more credential statuses, the nine
items below are listed as **pending external-run inputs**; where a run is
blocked by data or tools rather than credentials, that distinction is shown.

| Run/input | Existing status | What it needs |
|---|---|---|
| H17 six-provider conformance | pending credentials | Eligible six-family access configuration and reachable installed Ollama model; see `claims/17.json`. |
| H22 model-assisted localization | pending credentials | `OLLAMA_HOST`, model/provider access, `OPENAI_API_KEY`, `ETHERSCAN_API_KEY`, plus source-linked function ground truth; see `claims/22.json`. |
| H25 live RPC mechanisms | pending credentials | `DRPC_API_KEY`, `DRPC_RPC_URL`, and a preregistered multi-chain archive/debug-trace/failover run; see `claims/25.json`. |
| H26 broader historical replay | tool/input limited | `SOLC_BINARY`, `ANVIL_BINARY`, `CAST_BINARY`, `FOUNDRY_BIN`, plus the intended historical capture set; current evidence backs only a limited Ethereum sample. |
| H27 WAF experiment | pending external credentials/data | `CURL_IMPERSONATE_BINARY`, `WAF_CASES_JSON`, and an authorized challenge denominator; see `experiments/waf.json`. |
| H18 paired cost study | data/pricing blocked | Preregistered 100-case 50/30/20 workload, observed provider usage, dated prices, and paired quality/rank outputs. |
| H21 benign prefilter | data blocked | Independently verified benign cohort, paired production runs, and latency measurements. |
| H28 Table VI | data blocked | Observed PMS/CES/TCS/LCS vectors for the accepted cohort. |
| H29 guidance study | data blocked | Preregistered 20-case selection, ranking ground truth, guidance policy, denominator, and paired outcomes. |

This distinction is based on `benchmark/claim_registry.py:37-49`,
`reports/claim_closure/local_snapshot/claim_report.md:27-39`, and
`reports/provenance_hunt/FINAL_REPORT.md:89-108`.

## 4. Known issues — flagged, not edited

These issues are recorded only; no paper or claims file was changed:

1. The original cost table's GPT-4o price input is approximately **16× too
   high** relative to the retained pricing comparison and should be checked
   against a dated source.
2. The repository arithmetic supports **35% modeled cost saving**, not the
   paper's “60–80%” claim. See `PAPER_VS_REPO.md:34,84` and
   `reports/reproducibility/FINAL_REPORT.md:50`.
3. The current retained exploit CSV has **183 rows**, while another retained
   artifact refers to **231** and the paper claims **246**; these are different
   dataset versions and must not be silently conflated.
4. The paper's **“111 of 114” arithmetic** remains flagged for reconciliation;
   no corrected value is inferred here.

## 5. Licensing check

| Check | Result | Evidence |
|---|---|---|
| Apache-2.0 LICENSE kept | confirmed | Root `LICENSE:1-5` begins with Apache License, Version 2.0. |
| NOTICE kept | **not confirmed** | No root or workspace `NOTICE` file was found by the offline file check; it was not created or inferred. |
| ASE 2025 paper cited in README | **not confirmed in root README** | The authors' copied README cites ASE 2025 at `third_party/original_faultseeker/README.md:3,33-35`, but root `README.md:419-436` cites the 2026 FaultSeeker++ survey draft instead. No README was edited in this task. |

## 6. Proof commands and actual output

All commands below were offline. No keys, endpoints, RPC calls, `cast`, or
benchmark execution were used.

### Saved-row manifest and label inventory

```text
$ python -c "...read manifest and count labels..."
manifest: n_total=115 n_ok=110 n_failed=5 replay_mismatch=14
labels: json_files=115 unique_transaction_hashes=114
```

### Offline metric regeneration

```text
$ python scripts/reproduce/audit_original_scorer_strictness.py
current_rule: hits_at_1=25 hits_at_3=49 hits_at_5=52
original_definition_reconstruction: hits_at_1=27 hits_at_3=49 hits_at_5=53
address_requirement: miss_to_hit=3 hit_to_miss=0
selector_name_resolution: miss_to_hit=0 hit_to_miss=2
combined_current_vs_original: miss_to_hit=3 hit_to_miss=2
```

The exact complete audit output is retained by the already committed audit
script and report; the command reads only saved rows and labels.

### Full tests

```text
$ python -m pytest tests -q -p no:cacheprovider
994 passed, 7 skipped in 187.58s (0:03:07)
```

### Protected-file diff check

The final commit stages only the two new documents in
`reports/original_benchmark/`. The working tree may still contain unrelated
pre-existing modifications, but this consolidation does not stage or modify
any `paper/` or `reports/claim_evidence/` file.

## 7. Reproducibility and commit

New files:

- `reports/original_benchmark/LOCALIZATION_SCORING_PROTOCOL_NOTE_20261017.md`
- `reports/original_benchmark/FINAL_CONSOLIDATION_20261017.md`

No existing scorer, paper, or claims file was changed. The commit hash will be
reported after the final docs-only commit.
