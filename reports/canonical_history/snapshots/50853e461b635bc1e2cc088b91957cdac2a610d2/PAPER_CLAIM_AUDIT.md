# Paper Claim Audit (jisa.pdf vs repository)

Status legend:

- **IMPLEMENTED** - the capability exists in code and is unit-tested.
- **MEASURABLE** - measurement code now exists; the number must be produced by running it.
- **BLOCKED** - cannot be measured until benign trace features are collected (needs an archive RPC).
- **UNSUPPORTED** - the paper reports a number that no code in this repo produces.

## 1. Architecture and algorithm claims

| Paper | Claim | Status |
|---|---|---|
| S4.2 | FAEGL 7-feature vector | IMPLEMENTED (`faultseeker/research/failure_aware_localization.py`) |
| S4.3 | Severity `s = min(1, 0.58z + 0.24max(aG,te) + 0.18max(ds,ft))` | IMPLEMENTED, matches code exactly |
| S4.4 | Candidate ranking weights (0.24/0.18/0.16/0.14/0.12/0.10/0.04) | IMPLEMENTED, matches `rank_candidates` |
| S3.4 | TIG anomaly score | IMPLEMENTED (`forensics/interaction_graph.py`) |
| S3.6 | Four-factor confidence `C(f)` | IMPLEMENTED (`core/confidence_scorer.py`) |
| S5.3 | Logistic calibrator, L2 lambda=0.001, 600 epochs | IMPLEMENTED (`research/calibration.py`) |
| Table 2 | Reentrancy tier weights | IMPLEMENTED (`forensics/result.py`) |

The *capability* claims hold up. The *numeric* claims below do not yet.

## 2. Numeric claims requiring re-measurement

| Paper | Claim | Status | Action |
|---|---|---|---|
| Abstract, Table 4 | F1 = 0.969, FPR = 0.003 | BLOCKED | Collect benign traces, then run `run_honest_experiments.py` |
| Abstract | +14.7 pp over LLM-only | BLOCKED | Same; baselines must run on identical inputs |
| Table 5 | Ablation deltas | MEASURABLE | Use `AblationConfig` switches, not constant subtraction |
| Table 6 | Adversarial retention rho >= 0.94 | MEASURABLE | Re-run perturbations on real traces, not `synthetic_trace()` |
| Table 4 caption | 95% CI [0.961, 0.975] | UNSUPPORTED | No artifact contains this interval; regenerate with `bootstrap_f1_ci` |
| S6.2 | Bootstrap 1,000 resamples | IMPLEMENTED | Default is now 1000 (was 400) |
| S5.3 | Brier / ECE (Eq. 7, 8) | MEASURABLE | Now implemented; no value was reported in the paper |
| S6.6 | Reentrancy F1 0.86 / 0.69 / 0.57 on 18 txns | UNSUPPORTED | No script produces these; verified set has 13 reentrancy rows |
| S6.7 | 2.3 s / 8.1 s / 3.4 s, ~58% cost cut | MEASURABLE | `CostTracker` now records real latency and cost |
| S6.7 | ~40% BENIGN pre-filter, ~23% WAF fallback | MEASURABLE | `record_transaction(prefiltered=True)` |
| S6.2, S6.8 | "All 124 unit and integration tests pass" | MEASURABLE | CI now enforces the real count; README said 121 |

## 3. Dataset claims to correct in the paper

| Paper | Claim | Repository reality |
|---|---|---|
| S6.1, Table 3 | 1,059 annotated exploit transactions | 231 verified + 828 candidates marked `source_poc_tx_candidate_pending_rpc` |
| Table 3 | Total 11,059 | Double-counts: the 1,059 pool contains the 231 |
| S6.1 | Benign set "confirmed exploit-free by the Stage 1 signal extractor" | Labelled `address_label_benign_candidate` from HuggingFace address labels; the extractor never ran on them |
| S6.1 | 10 chains | 8 chains in the verified set; 10 only in the unvalidated pool |
| S6.1 | 231 rows fully annotated | 3 rows still read `TODO: Needs Annotation`; only 115 ground-truth JSON files exist |
| Abstract | Analysts spend 16.7 h per incident [5] | Verify against DAppFL before submission |

## 4. The structural blocker

The exploit CSV carries measured trace statistics (`functioncall_count`,
`address_count`, `max_depth`, `gas_cost`). The benign CSV carries **none** of
them. A classifier evaluated across both files separates the classes by feature
availability alone, which is a second form of leakage independent of reading
`label`. `audit_feature_coverage()` detects this and the harness refuses to emit
comparison tables until it is fixed:

```
python benchmark/collect_benign_traces.py --limit 1000 --rpc-url $ETH_RPC_URL
python benchmark/run_honest_experiments.py
```

1,000 benign transactions is sufficient for a valid FPR estimate.

## 5. Recommended primary result

The strongest defensible contribution is **fault localization**, not binary
classification. `benchmark/ground_truth/*.json` contains real contract, function
and line targets, so Top-k accuracy and MRR can be measured today on 115
transactions with no benign set required:

```
python main.py --batch benchmark/ground_truth --output data/output
python benchmark/run_localization_eval.py --predictions-dir data/output
```

A real Top-5 accuracy on 115 transactions is publishable. A fabricated F1 on
11,059 is not.

## 6. Security

`foundry.toml` contains a live QuickNode BSC endpoint with an embedded token.
Rotate it before any public release; the paper's Data Availability statement
points readers directly at the repository.

---

## Addendum: integration status after wiring pass

| Paper claim | Before | Now |
|---|---|---|
| Section 5.2 FAEGL affects localization | Module existed, unreachable from pipeline | **Wired.** `--disable-faegl` bypasses the localizer entirely |
| Section 4 TIG contributes graph features | Computed always, never ablatable | **Wired.** `--disable-tig` skips graph construction |
| Section 5.3 calibrated confidence | Class existed, **never called by the pipeline** | **Wired**, opt-in via `FAULTSEEKER_CALIBRATOR_PATH` |
| Section 6.7 per-stage latency (2.3 / 8.1 / 3.4 s) | Hardcoded in a synthetic script | **Instrumented** for 2 stages; needs a real corpus run |
| Section 6.7 ~58% cost reduction | Hardcoded | **Measurable** once `record_llm_call` is added to `llm_router.py` |
| Table 5 ablation deltas | Constant subtraction from full-system score | **Real behavioural switches** for FAEGL, TIG, calibration |

### Ablation table: what you can now legitimately report

Runnable today (real code-path ablations):
- `full_system`
- `minus_faegl`
- `minus_tig`
- `minus_calibration`

Not yet runnable (switch exists, call site not gated):
- `minus_llm_routing`
- `minus_adversarial_hardening`

Do not report the latter two until their call sites are gated. The old
`ablation_results.csv` values for them (`0.9032` and `0.9673`) were produced by
constant subtraction and are not measurements.

### Calibration caveat before reporting Brier/ECE

The calibrator declares 8 features but the orchestrator currently supplies 4.
The other four (`pattern_match`, `code_evidence`, `txn_consistency`,
`llm_confidence`) come from Stage-2 agent output and default to 0.0. Wire those
through before reporting the section 5.3 numbers, or the calibrator is running on
half its inputs.

### Verified test count

112 tests collected without optional dependencies (93 passed, 0 failed, 19
skipped); 117 collected with all import dependencies satisfied (104 passed, 0
failed, 13 fixture-based skips). Neither number is the paper's "124" or the
README badge's "121". Replace both with the number your CI prints.

---

## Addendum 2: final integration status

| Component | Wired | Ablation is a real code-path change |
|---|---|---|
| FAEGL | Yes | Yes — localizer never called |
| TIG | Yes | Yes — graph never built |
| Calibration | Yes (opt-in) | Yes — calibrator never consulted |
| LLM routing | Yes | Yes — all queries forced to cloud |
| Adversarial hardening | **No such component exists** | N/A |
| Per-stage latency | Yes (2 stages) | N/A |
| Token cost / 58% claim | Yes — `record_llm_call` now invoked | N/A |

### Section 6.7 is now measurable

`HybridLLMRouter.record_query()` feeds `CostTracker`, so `tracker.report()`
returns real `actual_cost_usd`, `counterfactual_all_cloud_cost_usd`,
`cost_reduction_vs_all_cloud`, and `tier_distribution`. Note the reduction is a
**fraction in [0, 1]**, not a percentage — multiply by 100 before quoting "58%".

Token counts are estimated at ~4 chars/token by the existing router code. If you
quote cost figures, either say "estimated tokens" or switch to the provider's
returned usage counts.

### Section 6.5 must be reframed

There is no adversarial hardening in the system. The evaluator perturbs inputs
and measures score deltas against the **unhardened** pipeline. Report it as a
robustness probe, not as an ablation of a defence.

### Remaining blockers, unchanged

1. Benign trace coverage is 0/10000 — blocks Tables 4 and 5.
2. No pipeline predictions written yet — blocks the localization table, which is
   otherwise ready (115 transactions, 161 function targets, 134 line targets).
3. Calibrator receives 4 of its 8 declared features; the other four come from
   Stage-2 `ConfidenceScorer` output (`pattern_match`, `code_evidence`,
   `txn_consistency`, `llm_confidence`) and are not yet threaded into the
   pre-LLM calibration call. Do not report Brier/ECE until they are.
