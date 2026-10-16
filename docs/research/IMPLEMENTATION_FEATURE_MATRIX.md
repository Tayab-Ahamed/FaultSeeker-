# Implementation-paper feature matrix

This matrix audits mechanisms described in the supplied eight-page implementation paper against the repository. `EXISTS` means an executable local mechanism is present, `PARTIAL` means the mechanism exists but its paper-level scope depends on external inputs or lacks a required audit boundary, and `MISSING` means the repository had no explicit mechanism before the opt-in additions listed here. Status is not an empirical result and does not validate reported numbers.

| Mechanism | Paper location | Status | Exact repository paths | Scope note |
|---|---|---|---|---|
| dual-path explorer/RPC collection | III-A, Algorithm 1 | EXISTS | `faultseeker/utils/explorer_provider.py`; `faultseeker/utils/rpc_provider.py`; `faultseeker/data_collection/txn_replayer.py` | Explorer and scored RPC fallback are executable; live endpoint success is separate. |
| explorer EMA ranking and circuit breaker | III-A | EXISTS | `faultseeker/utils/explorer_provider.py` | EMA alpha, endpoint scoring, and half-open recovery exist. |
| RPC weighted failover, LRU/TTL cache, and batch calls | III-A | EXISTS | `faultseeker/utils/rpc_provider.py` | Defaults are 512 entries and 600 seconds. |
| Foundry replay with call/gas/selector/storage observations | III-A | PARTIAL | `faultseeker/data_collection/txn_replayer.py`; `faultseeker/data_collection/storage_trace.py` | Capture/storage completeness depends on provider and transaction. |
| zero-LLM five-category deterministic signal extraction | III-B | EXISTS | `faultseeker/forensics/signal_extractor.py` | Five signal families are emitted locally. |
| EXPLOIT/BENIGN/UNCERTAIN rule classifier | III-B, Algorithm 1 | EXISTS | `faultseeker/forensics/rule_classifier.py`; `faultseeker/forensics/orchestrator.py` | Control flow exists; population rates are not inferred. |
| SSTORE cross-depth storage-mutation reentrancy score | III-C, Eq. (2) | EXISTS | `faultseeker/core/paper_profile.py`; `faultseeker/forensics/signal_extractor.py` | Paper-mode weights and nested-slot evidence execute locally. |
| structural fallback discount and cap | III-C | EXISTS | `faultseeker/core/paper_profile.py`; `faultseeker/forensics/signal_extractor.py` | Fallback is marked and discounted. |
| OpenZeppelin mutex filtering | III-C | EXISTS | `faultseeker/forensics/signal_extractor.py` | Local 1→2→1 mutex transitions without nested writes are filtered. |
| DELEGATECALL/CALLCODE storage-context normalization | III-C | EXISTS | `faultseeker/forensics/signal_extractor.py`; `faultseeker/data_collection/storage_trace.py` | Storage ownership follows caller context. |
| three-tier hybrid LLM routing and local-confidence gate | III-D | EXISTS | `faultseeker/core/llm_router.py`; `faultseeker/research/ablation.py` | Tier selection and Tier-2 fallback are executable. |
| six provider backend adapters | III-D, III-F | PARTIAL | `faultseeker/utils/agent.py`; `faultseeker/core/llm_router.py` | Families are declared; live conformance is not bundled. |
| per-query cost accounting and cloud counterfactual | III-D, Eq. (3) | PARTIAL | `faultseeker/core/llm_router.py`; `faultseeker/research/cost_tracker.py`; `faultseeker/research/routing_audit.py` | Existing tracking is extended with explicit observed-vs-estimated accounting. |
| four-factor confidence scoring | III-E, Eq. (4) | EXISTS | `faultseeker/core/confidence_scorer.py` | PMS/CES/TCS/LCS and display levels are relative heuristics. |
| structured evidence cards | III-E | PARTIAL | `faultseeker/core/confidence_scorer.py`; `faultseeker/core/pipeline.py`; `faultseeker/research/evidence_provenance.py` | Cards exist; digest-bound provenance is opt-in. |
| two HITL checkpoints and five guidance types | III-E | EXISTS | `faultseeker/core/human_interface.py`; `faultseeker/core/pipeline.py` | CLI checkpoints and structured modifications exist. |
| JSON forensic report and optional benchmark row | III-A, Fig. 2 | EXISTS | `faultseeker/forensics/result.py`; `faultseeker/main.py`; `benchmark/run_eval.py` | Serialization and evaluation-row construction exist. |
| multi-chain EVM coverage | III-A, IV-A | PARTIAL | `faultseeker/utils/rpc_provider.py`; `faultseeker/utils/explorer_provider.py`; `faultseeker/research/chain_profiles.py` | Registries exist; the paper's authenticated ten-chain cohort is not established. |
| trace capability and storage eligibility metadata | III-A/III-C | MISSING → opt-in | `faultseeker/research/trace_capability.py` | Added conservative storage/structural/ineligible decisions. |
| artifact/evidence provenance for evidence cards | III-E, III-F | MISSING → opt-in | `faultseeker/research/evidence_provenance.py` | Added digest-bound observed/derived/synthetic ledger. |
| adversarial versus empirical/synthetic evaluation separation | V, IV | MISSING → opt-in | `faultseeker/research/evaluation_partition.py`; `faultseeker/research/adversarial.py` | Added metric eligibility guard for perturbations and fixtures. |
| empirical calibration with disjoint provenance | III-E, VI | PARTIAL | `faultseeker/research/calibration.py` | Calibrator enforces disjoint IDs; calibrated outcomes remain opt-in. |

The machine-readable source for this table is `faultseeker/research/paper_mechanisms.py`. The implementation paper file itself is intentionally unchanged.
