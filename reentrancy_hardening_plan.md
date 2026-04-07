# FaultSeeker++ Forensic Engine Hardening: Reentrancy Hardening Plan

This document summarizes the current progress, technical findings, and the finalized implementation strategy for reaching high-confidence reentrancy detection.

## 1. Current Progress & Infrastructure
*   **Infrastructure Status**: **FIXED**. The engine is now successfully fetching deep execution traces from the Tenderly Web3 Gateway.
*   **Trace Normalization**: Heterogeneous trace formats (Geth, Tenderly, Erigon) are unified into a canonical tree structure.
*   **Initial Heuristics**: We have successfully implemented a **stack-based recursive walker** that detects:
    *   `call_depth_max` (Current test: 6)
    *   `external_calls` (Current test: 41)
    *   `same_contract_reentry` (Address repetition in call stack)
    *   `same_selector_reentry` (Function selector repetition in call stack)

## 2. Technical Findings: The "Call-Reentrancy" Gap
While the initial traversal works, the current trace analysis on `0xd4fafa...` shows that address/selector repetition alone misses some sophisticated attacks.
*   **Observation**: We see depth 6 and 41 external calls, but `same_contract_reentry` is 0.
*   **Root Cause**: The attack is likely **State-Reentrancy**, not necessarily **Call-Reentrancy**. The exploit mutates state in a way that violates invariant logic without needing to call the *exact same* function address again in a recursive loop.

## 3. Finalized Implementation Strategy: State-Reentrancy
To bridge the detection gap, the engine must transition from "Call Repetition" to **"State Mutation Detection"**.

### A. New Signal Model (Additive Scoring)
We are moving away from multiplicative logic (which collapses to zero on sparse signals) to a robust additive model:
| Signal Component | Weight | Criteria |
| :--- | :--- | :--- |
| `depth_factor` | +1 | `depth >= 2` |
| `external_call_factor` | +2 | `external_calls >= 1` |
| `call_reentry_factor` | +3 | Same address in recursion stack |
| `selector_reentry_factor` | +4 | Same function selector in recursion stack |
| `state_reentry_factor` | +4 | **SSTORE to same slot at different depths** |
| `state_mutation_after_call` | +4 | **Storage write after external call returns** |

**Threshold for Detection**: `score >= 4`

### B. Core Detection Logic: SSTORE Tracking
The `SignalExtractor` will be updated to:
1.  **Track Storage Writes**: Map `(contract_address, storage_slot)` to the `depth` at which the write occurred.
2.  **Detect Double Writes**: If the same `(addr, slot)` is written to at multiple depths (specifically `max(depths) - min(depths) >= 2`), trigger `state_reentry`.
3.  **Heuristic "Write-After-Call"**: 
    *   Mark every node that triggers an external boundary (`node.to != root_to`).
    *   Detect if any subsequent instruction in an ancestor contract performs an `SSTORE`.

## 4. Next Steps (No Changes Applied Yet)
1.  **Verify Data Capture**: Ensure the RPC normalization layer (`rpc_provider.py`) is passing `storage_writes` or `SSTORE` events into the canonical tree.
2.  **Update `SignalExtractor`**: Implement the refined recursive walk that tracks labels for state mutation.
3.  **Calibrate Thresholds**: Test against the `benchmark_classification_fixed.csv` to ensure high precision and recall.

---
**Status**: Research/Planning Phase complete. Awaiting instruction to begin implementation of State-Reentrancy signals.
