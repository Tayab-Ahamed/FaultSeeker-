# Batch A label semantics

**Scope: offline only. No RPC, network, tuning, fixes, or rescoring.**

## 1. Original benchmark ground-truth function definition

The frozen protocol defines the original target as an upstream function-level location:

> “Ground-truth source: upstream function-level `location` mappings.”

> “A target is a function-level location parsed from the upstream `location` mapping. Address and function identity are both required when available.”

Source: `benchmark/protocols/original_benchmark_function_localization_v1.md`, lines 11–15 and 23–27.

The imported ground-truth files are described as:

> “an unmodified copy of the 115 function-localization ground-truth JSON files”

and the attribution file states:

> “No labels, locations, transaction ordering, or source fields were changed.”

Source: `benchmark/original_faultseeker/ATTRIBUTION.md`, lines 3–5 and 17–22.

The ground-truth JSON structure stores a `location` map containing an address, contract/file component, function member, and often a line entry. For example:

```json
"location": {
  "0xe8b3...#...##4115:21": [
    "0xe8b3...#YVCrv3CryptoFeed#latestAnswer",
    "0xe8b3...#YVCrv3CryptoFeed#120:8"
  ]
}
```

Source: `benchmark/original_faultseeker/ground_truth/0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c.json`, lines 10–14.

The ground-truth field therefore records a function-level location identity: address plus function name, with line information when present. The protocol text does not define it as an externally callable transaction entry point.

## 2. Original benchmark trace check

- Ground-truth JSON files: 115.
- Successful original-run rows: 110.
- Successful rows with a parsed ground-truth function: 110/110.
- Local full trace copies available for those successful rows: 4/110.
- Successful rows without a local full trace copy: 106/110.
- Rows checked for an external call: 4.

For the trace check, an external call was counted when a trace node had the labeled ground-truth address as its `to` address and its input selector resolved to the labeled function name using the local selector table. No RPC or network lookup was used.

| Transaction | Ground-truth function | Local trace result |
| --- | --- | --- |
| `0x0788...8cceb` | `cacheAssetPrice` | Does not appear as an external call |
| `0x9582...9313c` | `latestAnswer` | Appears as an external call |
| `0xa6f6...0b2aa` | `doSwapThroughOrionPool` | Does not appear as an external call |
| `0xc310...b111d` | `donateToReserves` | Appears as an external call |

Counts over the rows that could be checked:

- Appears as an external call: **2/4**
- Does not appear as an external call: **2/4**

Evidence: `benchmark/original_faultseeker/ground_truth/*.json`; `reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json`; local trace copies under `reports/cohort_rebuild_v2/traces/`; local matching implementation in `benchmark/honest_eval/localization.py`.

## 3. Batch A full-signature check

The frozen Batch A artifact stores source-labeled fields such as `vulnerable_function`, `vulnerable_function_quote`, and `source_transaction_quote`.

For the 23 valid ETH Batch A rows:

- Rows inspected: 23.
- Labels with a usable full signature containing argument types in the label or quoted source: **0/23**.
- Labels containing only bare function names or empty-parenthesis forms such as `swap()`, `mint()`, `pledgeAndBorrow()`, and `init()`: **23/23**.
- Argument-type guesses made: **none**.
- Selector-based trace checks performed under the requested full-signature rule: **0**.

Evidence: `reports/new_batches/batchA_candidates.json`; `reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json`.

The Batch A source labels use DeFiHackLabs source fields. For example, the artifact stores:

```json
"vulnerable_function": "swap()",
"vulnerable_function_quote": "... vulnerable swap() function ..."
```

and analogous empty-parenthesis forms for the other valid ETH labels.

Source: `reports/new_batches/batchA_candidates.json`.

## 4. Comparison of label definitions

Observed representations:

| Set | Function definition evidence | Full typed signatures available | Rows with trace check |
| --- | --- | ---: | ---: |
| Original benchmark | Address/function entries in upstream `location` mappings; line entries may also be present | Not required by the protocol text | 4/110 available locally |
| Batch A valid ETH rows | DeFiHackLabs source-labeled `vulnerable_function` plus source quotes | 0/23 | 0/23 under the full-signature-only rule |

The two sets use different stored label representations in the checked files: the original benchmark stores address-qualified function-location mappings, while Batch A stores source-labeled vulnerable-function strings and quotes. The Batch A rows supplied no full argument-typed signatures for selector computation under the requested rule.
