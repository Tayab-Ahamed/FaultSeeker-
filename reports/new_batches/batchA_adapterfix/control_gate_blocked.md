# Batch A adapter-fix control gate

**Label: post-diagnostic adapter fix, exploratory**

The single permitted run stopped before any of the four controls completed. The patched adapter reached a state-name typo in the new original-path bridge (`tx_hash` versus the orchestrator's `txn_hash`). That typo was corrected after the stop, but the controls were not retried, per the one-run/no-retry instruction.

- Controls executed: 0/4
- Batch A measurement: not run
- RPC/network calls: none
- Ranker/scorer/weights: unchanged
- Frozen Batch A and valid set: unchanged
