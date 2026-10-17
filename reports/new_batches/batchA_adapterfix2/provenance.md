# Original benchmark provenance and replay decision

**Label: post-diagnostic, exploratory**

## Producer path

The saved rows were produced through:

```text
scripts/reproduce/run_original_provider_pinned.py
  -> ForensicsOrchestrator(model="llm-free-function-ranker").run(tx_hash, chain)
  -> FunctionRanker().rank(result, {repeated_patterns, function_call_loc_memo})
  -> _score(ground_truth, predictions)
```

The producer-era code is commit `1b1c7395771663622dd14b9731b4b8b471221960` (`fix: isolate provider errors from replay traces`). The run configuration was:

- Run ID: `original-v1-pinned-sequential-20261017`
- Variant: `llm-free`
- Model: `llm-free-function-ranker`
- Protocol: `benchmark/protocols/original_benchmark_function_localization_v1.md`
- Seed: `20261017`
- Ground-truth inputs: 115 files
- Provider policy in the original run: BlockPI for ETH/BSC; dRPC spare not used

The current producer script is byte-identical to the producer-era script. The current orchestrator, captured-input helpers, sequencer, transaction-info collector, and trace analyzer are also unchanged from that commit. The current `FunctionRanker` is different (`b54a1b3`), so the replay used a detached producer worktree at `1b1c739`; the current ranker was not modified.

## Replay method

The replay used only the local full trace and RPC artifacts. Existing captured-input readers (`_CapturedSequencer` and `_CapturedInfo`) supplied I/O to the unmodified producer-era `ForensicsOrchestrator.run`. No custom candidate adapter or manual `ForensicsResult` was used, and no RPC/network call was made.

## Three failing controls

| Control | Saved rank | Original-entrypoint rank | Saved candidates | Original candidates | Rank reproduced? |
| --- | ---: | ---: | ---: | ---: | --- |
| `0x958236...9313c` | 19 | `None` | 100 | 100 | No |
| `0xa6f63f...40b2aa` | 7 | `None` | 7 | 51 | No |
| `0xc310a0...b111d` | `None` | `None` | 20 | 55 | Yes for rank only; candidate list differs |

## Decision: (b)

The original entrypoint does **not** reproduce the saved benchmark ranks on the local full artifacts. Therefore the saved ranks are stale or came from a different code/input state, and the controls are invalid for adapter validation.

There is direct Git evidence for staleness: at archival commit `240fd9f`, the three saved rows had candidate counts/ranks `(100, None)`, `(7, None)`, and `(20, None)`. Commit `70d1b099` later changed only the stored score fields for the first two to ranks `19` and `7`; their candidate lists remained unchanged. The producer-era replay produced the same `None` ranks for those two, while producing candidate counts `51` and `55` from the supplied local full traces. The third row retained saved rank `None` but still differed in candidate count (`20` versus `55`).

Step 5 was not run. No Batch A measurement or new R@1/R@3/R@5 claim was produced.
