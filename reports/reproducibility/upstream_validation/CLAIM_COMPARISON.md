# Independent upstream validation

This is an independent calculation from retained upstream benchmark labels and provider-pinned LLM-free ranker outputs. It is not an exact reproduction of the paper's multi-agent run.

## Localization calculation

| View | Denominator | R@1 | R@3 | R@5 | Scope |
|---|---:|---:|---:|---:|---|
| original_function_only_all_115 | 115 | 27/115 (0.2348) | 49/115 (0.4261) | 53/115 (0.4609) | retained outputs |
| current_address_aware_all_115 | 115 | 25/115 (0.2174) | 49/115 (0.4261) | 52/115 (0.4522) | retained outputs |
| original_function_only_valid_110 | 110 | 27/110 (0.2455) | 49/110 (0.4455) | 53/110 (0.4818) | retained outputs |
| current_address_aware_valid_110 | 110 | 25/110 (0.2273) | 49/110 (0.4455) | 52/110 (0.4727) | retained outputs |

Published upstream Table II values are 50.43%, 73.91%, and 76.52% on 115 transactions. Their implied integer hits are 58/115, 85/115, and 88/115. The retained independent function-only calculation produces 27/115, 49/115, and 53/115 because five rows failed and the 110 successful rows are LLM-free ranker outputs. This is an independent calculation, not an exact reproduction.

## Claim comparison

| ID | Claim | Status | Independent evidence | Required change |
|---:|---|---|---|---|
| 1 | Open source release | `EXTERNALLY_BLOCKED` | — | Public fork/release URL; local Apache license alone does not prove publication. |
| 2 | 201 original tests pass | `UNVERIFIED` | — | Full suite with original baseline tests retained; runner unit test alone is insufficient. |
| 3 | Authentic 246-row cohort | `EXTERNALLY_BLOCKED` | {"root_accepted": 14, "root_target": 246, "v4_accepted": 22, "v4_target": 246} | 223 further fully admitted unique exploit transactions and1additional chain to reach246/10; preregister any new study version before assigning/predicting the accepted zkSync addition |
| 4 | Real transactions, two independent sources, annotations | `EXTERNALLY_BLOCKED` | — | 226 additional unique exploit transactions with the same complete provenance and annotation standard, including4 additional chains |
| 5 | Ten chains and Ethereum 47.6% | `CONTRADICTED_BY_CURRENT_EVIDENCE` | {"historical_csv_chains": 8, "historical_csv_rows": 231, "historical_eth_rows": 132} | Accepted frozen study cohort and independently verified chain membership |
| 6 | More than 80 vulnerability labels | `EXTERNALLY_BLOCKED` | {"historical_distinct_nonempty_vulnerability_strings": 82, "semantic_adjudication": false} | Adjudicated SWC/DASP label mapping and semantic deduplication for the frozen cohort |
| 7 | Class proportions 6.5/33.3/32.5/27.6% | `CONTRADICTED_BY_CURRENT_EVIDENCE` | — | Trace-verified function-count bins for the authentic paper cohort |
| 8 | 18 reentrant incidents among 246 | `CONTRADICTED_BY_CURRENT_EVIDENCE` | {"historical_reentrancy_substring_rows": 17, "target_cohort": 246} | Independently adjudicated reentrancy positives in the frozen evaluation cohort |
| 9 | Storage-aware detector, guards and delegatecall | `VERIFIED_IMPLEMENTATION` | — | Compiled execution still separately required under claim 26. |
| 10 | Five storage signal weights | `VERIFIED_IMPLEMENTATION` | — | Weights must fire on observed opcode events. |
| 11 | Five confidence tiers | `VERIFIED_IMPLEMENTATION` | — | Threshold boundaries and production paper profile. |
| 12 | Three structural signals, .75 penalty, .80 cap | `VERIFIED_IMPLEMENTATION` | — | Fallback when storage capture unavailable, no extra terms. |
| 13 | Detector precision/recall/F1 and baselines | `EXTERNALLY_BLOCKED` | {"historical_proxy_f1": 0.7586, "scope": "saved aggregate; not authenticated cohort"} | Complete full-system predictions on accepted population and one-use held-out final exam; missing trace observations must remain missing |
| 14 | 17/29 percentage-point gains | `EXTERNALLY_BLOCKED` | — | Paired final frozen-system evaluation on adequately sourced full population; current five-case availability-selected sample does not verify published gains |
| 15 | Compound case study | `EXTERNALLY_BLOCKED` | — | Exact legitimate cToken case-study transaction plus source linkage |
| 16 | Query routing with theta gate | `VERIFIED_IMPLEMENTATION` | — | Local quality/confidence gate must dispatch escalation. |
| 17 | Six provider families | `EXTERNALLY_BLOCKED` | — | Eligible live family access including a reachable installed Ollama model |
| 18 | 58% cost savings, 100 transactions, quality/rank bounds | `CONTRADICTED_BY_CURRENT_EVIDENCE` | {"measured_100_case_runs": 0, "modeled_cost_reduction_pct": 35.0} | Frozen100-case paired workload with observed usage, pricing and quality outputs |
| 19 | Stage 1 makes no model calls | `VERIFIED_IMPLEMENTATION` | — | Constructor and executed Stage1 must remain keyless. |
| 20 | BENIGN skip, EXPLOIT lock and UNCERTAIN escalation | `VERIFIED_IMPLEMENTATION` | — | Coverage required; positive verdict cannot be overwritten. |
| 21 | 40% benign prefilter and latency reduction | `EXTERNALLY_BLOCKED` | — | A preregistered representative legitimate-contract population with complete contextual execution evidence and paired production inference latency/usage observations |
| 22 | Multi-agent function localization | `EXTERNALLY_BLOCKED` | {"exact_reproduction": false, "failure_count": 5, "independent_calculation": true, "independent_localization": {"current_address_aware_all_115": {"hits": {"recall_at_1": 25, "recall_at_3": 49, "recall_at_5": 52}, "n": 115, "recall": {"recall_at_1": 0.2173913, "recall_at_3": 0.42608696, "recall_at_5": 0.45217391}}, "current_address_aware_valid_110": {"hits": {"recall_at_1": 25, "recall_at_3": 49, "recall_at_5": 52}, "n": 110, "recall": {"recall_at_1": 0.22727273, "recall_at_3": 0.44545455, "recall_at_5": 0.47272727}}, "original_function_only_all_115": {"hits": {"recall_at_1": 27, "recall_at_3": 49, "recall_at_5": 53}, "n": 115, "recall": {"recall_at_1": 0.23478261, "recall_at_3": 0.42608696, "recall_at_5": 0.46086957}}, "original_function_only_valid_110": {"hits": {"recall_at_1": 27, "recall_at_3": 49, "recall_at_5": 53}, "n": 110, "recall": {"recall_at_1": 0.24545455, "recall_at_3": 0.44545455, "recall_at_5": 0.48181818}}}, "published_upstream_table_ii": {"recall_at_1": {"denominator": 115, "hits_inferred_from_reported_percentage": 58, "percentage": 50.43}, "recall_at_3": {"denominator": 115, "hits_inferred_from_reported_percentage": 85, "percentage": 73.91}, "recall_at_5": {"denominator": 115, "hits_inferred_from_reported_percentage": 88, "percentage": 76.52}}, "replay_mismatch_count": 14} | Complete genuine model-assisted production outputs with validated final function identities; bounded pilot supplied no complete cases |
| 23 | Equation 4 confidence scoring | `VERIFIED_IMPLEMENTATION` | — | Heuristic score identified separately from calibrated probability. |
| 24 | Evidence cards and two HITL checkpoints, five guidance types | `VERIFIED_IMPLEMENTATION` | — | All feedback must affect downstream state, with rejection audit trail. |
| 25 | RPC EMA, LRU, TTL, breakers and batching | `EXTERNALLY_BLOCKED` | — | Authenticated missing-chain opcode/archive observations and live sustained multi-provider outage/recovery evidence |
| 26 | Foundry replay extracts SLOAD and SSTORE | `VERIFIED_IMPLEMENTATION` | {"cohort_scale": false, "historical_replay_samples": 2} | Compile and execute all Solidity fixtures and preserve raw trace captures; local EVM proof does not verify historical replay or cohort outcomes. |
| 27 | 23% WAF challenge bypass | `EXTERNALLY_BLOCKED` | — | Authorized challenged explorer-request corpus with recovery logs and denominator |
| 28 | Table VI category averages | `EXTERNALLY_BLOCKED` | — | Raw production per-function four-factor scores with adjudicated categories and declared averaging |
| 29 | Simulated guidance on 20 transactions, 68→81% | `EXTERNALLY_BLOCKED` | — | Original20-case selection/policy and paired rankings with explicit aggregation definition |
| 30 | Reproduction scripts | `UNVERIFIED` | — | Complete Stage2/3 provider/source-target prerequisites and actual final frozen-system experiments with observed billing and ranking outcomes |
| 31 | Repository layout/runtime compatibility | `VERIFIED_IMPLEMENTATION` | — | Local Python runtime and Docker input layout checked; actual Docker execution remains an external-tool check. |

## Provenance and limits

- Upstream source commit: `72753bd833554449efa8499f0d1775a97fb5c696`.
- Imported classification and ground-truth files are byte-preserved copies of the upstream benchmark.
- Failed rows remain in the 115-row denominator; valid-trace-only views are reported separately.
- No RPC, provider, LLM, or upstream rerun was performed by this calculation.
- Missing original scorer configuration, original predictions, and multi-agent transcripts prevent exact paper reproduction.
