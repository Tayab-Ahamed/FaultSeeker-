# Saved-row scorer strictness audit

**Date:** 2026-10-17  
**Scope:** the 110 saved rows with `status=ok` in the provider-pinned run  
**Mode:** offline only; no RPC, `cast`, trace acquisition, or rerun  
**Change policy:** scorer implementation and existing claims were not changed

This audit compares the current scorer with an evidence-bounded reconstruction
of the original paper's function-localization definition. The pinned authors'
repository contains the benchmark labels and ranking implementation, but no
standalone scoring routine. Therefore, the phrase **original-definition rule**
below means the narrowest rule supported by the paper, the authors' README and
ranker, and the labels; it is not a claim about an unreleased evaluator.

## Phase 1 — source definition

### Paper

The authors' paper describes the reported metric as ranking-position recall:

> “measured by recall at top-1, top-3, and top-5 ranking positions.”

Source: authors' PDF at the pinned source commit, `full_paper/FaultSeeker
LLM-Empowered Framework for Blockchain Transaction.pdf`, extracted text
lines 414–416 (`https://github.com/kairanskrr/FaultSeeker/blob/72753bd833554449efa8499f0d1775a97fb5c696/full_paper/FaultSeeker%20LLM-Empowered%20Framework%20for%20Blockchain%20Transaction.pdf`).

The paper reports the benchmark as 115 transactions and says the fault
annotations are the evaluation ground truth:

> “Our dataset comprises 115 malicious transactions...”

Source: same PDF, extracted text lines 417–418.

> “each transaction includes expert-validated fault annotations that serve as
> ground truth for evaluation.”

Source: same PDF, extracted text lines 426–431.

The paper's task is function localization, not contract-only classification:

> “FaultSeeker ... produces a **ranked list of vulnerable smart contract
> functions** with supporting evidence.”

Source: copied authors' README, `third_party/original_faultseeker/README.md:7`.

The project paper also states the distinction that matters for this audit:

> “If the task is localization, the benchmark should also say which function,
> state variable, or call path is considered ground truth.”

Source: `paper/blockchain_exploit_forensics_survey_ieee.tex:229`.

### Authors' repository and labels

The pinned authors' ranker represents a function candidate with a function and
address together. It constructs a key from both values:

```text
key = call['function'] + '_' + call['address']
```

Source: authors' `faultseeker/function_analysis/function_ranker.py:125-145`,
copied for this audit to the temporary extraction used by the command output.
The same file documents the key format as `function_address` at lines 188–202.

The imported labels encode locations as `address#Contract#member`, and include
both function members and source-line members. For example:

```json
"location": {
  "0x4308d314096878d3bf16c9d8db86101f70bbebf1##:": [
    "0x4308d314096878d3bf16c9d8db86101f70bbebf1#PHIL#simpleToken",
    "0x4308d314096878d3bf16c9d8db86101f70bbebf1#PHIL#:"
  ]
}
```

Source: `benchmark/original_faultseeker/ground_truth/0x20ecd8310a2cc7f7774aa5a045c8a99ad84a8451d6650f24e0911e9f4355b13a.json:11-16`.

Across the 115 labels there are 417 location entries: 183 function entries,
233 source-line entries, and 4 selector-form function entries. The label's
middle `Contract` component is descriptive metadata; the candidate schema in
the saved rows has `code_address` and `function`, not a contract-name field.

### Definition used for this audit

The evidence-bounded original-definition reconstruction is therefore:

1. A hit is a ranked **function-name** match to any function member in the
   transaction's `location` labels.
2. The label's contract name and address are not used as an additional
   requirement by this reconstruction, because the paper specifies ranked
   functions and the published metric definition does not say that contract
   identity is part of the equality test.
3. A four-byte selector is compared as the raw function identifier; no
   selector-to-name lookup is assumed because no authors-side scoring routine
   documenting such a lookup was found.
4. Any labeled function is sufficient, and Top-k means the first k ranked
   candidates.

This is deliberately conservative about what can be attributed to the
authors. It should not be read as proof that their private evaluator ignored
addresses; it is the reproducible paper-level reconstruction requested here.

## Phase 2 — side-by-side rules

| Dimension | Current scorer | Original-definition reconstruction | Difference? |
|---|---|---|---|
| Task unit | Function target represented as `(address, function)` | Function name target only | **Yes:** current adds an address equality requirement |
| Contract name | Ignored; parser keeps only address and final member | Ignored; authors' candidate has no contract-name field | No |
| Code address | Reads `address`, then `code_address`, `contract`, or `callee`; saved rows use `code_address` | Not required in the function-only reconstruction | **Yes:** current is stricter on address identity |
| Address normalization | Trim and lowercase (`localization.py:153-154`) | No address comparison in reconstruction; authors ranker lowercases for internal filtering/key lookup (`function_ranker.py:98-100`, `125-145`, `199-202`) | No additional empirical flip beyond the address requirement |
| Function normalization | Trim, lowercase, remove text after `(` (`localization.py:157-158`) | Trim, lowercase, remove text after `(` for the reconstructed function identity | No |
| Selector handling | A 4-byte selector may be resolved to a human name using the selector table (`localization.py:230-235`) | Raw selector remains a selector; no resolution | **Yes:** current can be more permissive |
| Multiple labels per transaction | Union of every parsed function label; any pair can hit (`localization.py:195-207`) | Union of every function member; any name can hit | No |
| Line labels | Parsed into `target.lines`, but default scoring uses `match="function"`; lines do not hit function recall (`localization.py:242-253`) | Paper metric is function ranking; line labels are not function names | No |
| Top-k cut | Uses the saved list order; first k items are examined (`rank_of_first_hit`, `localization.py:248-254`) | Uses ranking position; saved `rank` fields are the same ascending order | No on these rows: all 110 rows have ascending rank fields |
| Candidate field aliases | Accepts four address aliases and three function aliases | Saved rows consistently expose `code_address` and `function` | No observed flip; aliases are unused on these rows |

The current scorer's exact matching path is visible at
`benchmark/honest_eval/localization.py:216-239`; the first-hit and Top-k
behavior is at lines 242–254. The parser's treatment of multiple labels and
line/function targets is at lines 195–207.

## Phase 3 — offline flip counts and examples

The following command was run from the repository root:

```text
python scripts/reproduce/audit_original_scorer_strictness.py
```

Its scope output was:

```json
{
  "scope": {"valid_saved_rows": 110, "rpc": false, "cast": false, "rerun": false},
  "current_rule": {
    "hits_at_1": 25, "hits_at_3": 49, "hits_at_5": 52,
    "recall_at_1": 0.22727272727272727,
    "recall_at_3": 0.44545454545454544,
    "recall_at_5": 0.4727272727272727
  },
  "original_definition_reconstruction": {
    "hits_at_1": 27, "hits_at_3": 49, "hits_at_5": 53,
    "recall_at_1": 0.24545454545454545,
    "recall_at_3": 0.44545454545454544,
    "recall_at_5": 0.4818181818181818
  }
}
```

### Difference-level counts at Top-5

| Difference | Current miss → original hit | Current hit → original miss | Interpretation |
|---|---:|---:|---|
| Address requirement, holding selector behavior constant | 3 | 0 | Three rows have the right function name at a different address |
| Selector name resolution, holding address behavior constant | 0 | 2 | Two current hits depend on resolving `0x2e1a7d4d` to `withdraw` |
| Combined current vs original reconstruction | **3** | **2** | Net change: 52 current Top-5 hits → 53 reconstructed-original hits |
| Function case/signature normalization | 0 | 0 under the evidence-bounded rule | Authors' ranker evidence supports lowercase internal identity; no separate flip |
| Multiple labels / line labels / contract component | 0 | 0 | No observed semantic difference on saved rows |
| Top-k rank field vs list order | 0 | 0 | All 110 saved rows have ascending rank fields |
| Address/function field aliases | 0 | 0 | All saved candidate rows use `code_address`/`function` |

The request asked for five examples in each direction. The saved data contains
only **three** current-miss → reconstructed-original-hit cases and **two**
current-hit → reconstructed-original-miss cases. The command returned no
additional real rows, so this report lists all available examples rather than
inventing two more in either direction.

### Current miss → original-definition hit (all 3 available)

```text
0x2881e839d4d562fad5356183e4f6a9d427ba6f475614ce8ef64dbfe557a4a2cc
  label function: flashLoan @ 0xfd11aba71c06061f446ade4eec057179f19c23c4
  Top-5: supply@0x76f0c94c..., supply@0xfd11aba..., 1913f161@0x4f7a43..., mint@0x658b0f..., flashLoan@0x76f0c94c...
  current=miss; original-function-only=hit at rank 5

0x2b6d0af0dc513a15e325703405739057f9de6ef3f99934b957653b8a3fade4c6
  label functions: deposit, emergencyWithdraw @ 0xa44e79a2c9a8965e7a6fa77bf0ca8faf50e6c73e
  Top-5: deposit@0x44d1c6..., emergencyWithdraw@0x44d1c6...
  current=miss; original-function-only=hit at ranks 1-2

0xd9b3e229acc755881890394cc76fde0d7b83b1abd4d046b0f69c1fd9fd495ff6
  label functions: onERC721Received, offerBid @ 0xe4764f9cd8ecc9659d3abf35259638b20ac536e4
  Top-5: onERC721Received@0x7c5c9afe..., 980d3675@0xe55607..., offerBid@0x7c5c9afe...
  current=miss; original-function-only=hit at ranks 1 and 3
```

These are address-identity flips: the saved candidate names match a labeled
function, but the candidate `code_address` differs from the labeled address.

### Current hit → original-definition miss (all 2 available)

```text
0x6439d63cc57fb68a32ea8ffd8f02496e8abad67292be94904c0b47a4d14ce90d
  label function: withdraw @ 0x5d16b8ba2a9a4eca6126635a6ffbf05b52727d50
  Top-5 selector: 0x2e1a7d4d@0x5d16b8ba..., 0xa9059cbb@0xe021baa5..., 0x70a08231@0xe021baa5..., ...
  current=hit because selector cache resolves 0x2e1a7d4d → withdraw;
  original raw-selector rule=miss

0x72a252277e30ea6a37d2dc9905c280f3bc389b87f72b81a59aa8f50baebd8eaa
  label functions: withdraw, getPendingRewards @ 0x5d16b8ba2a9a4eca6126635a6ffbf05b52727d50
  Top-5 selector: 0x2e1a7d4d@0x5d16b8ba..., 0xa9059cbb@0xe021baa5..., 0x70a08231@0xe021baa5..., ...
  current=hit because selector cache resolves 0x2e1a7d4d → withdraw;
  original raw-selector rule=miss
```

### Difference-specific command output

The audit script's Top-5 flip summary was:

```text
address_requirement:                 miss_to_hit=3  hit_to_miss=0
selector_name_resolution:             miss_to_hit=0  hit_to_miss=2
combined_current_vs_original:         miss_to_hit=3  hit_to_miss=2
```

No saved row was changed by this audit.

## Phase 4 — two new measurements, side by side

These are both labeled **new measurement** and are restricted to the same 110
valid saved traces. They are not paper values and do not replace the existing
claims report.

| Metric | New measurement — current scorer | New measurement — original-definition reconstruction |
|---|---:|---:|
| Recall@1 (25/110 vs 27/110) | 22.73% | 24.55% |
| Recall@3 (49/110 vs 49/110) | 44.55% | 44.55% |
| Recall@5 (52/110 vs 53/110) | 47.27% | 48.18% |

### Conclusion

The current scorer is stricter than the paper-level reconstruction in one
material way: it requires the candidate's normalized code address to match the
label address in addition to the function name. That accounts for three
current misses becoming function-only hits. It is more permissive in a second
material way: it resolves two saved raw selectors to `withdraw`, producing two
hits that the raw-selector reconstruction does not count. The net effect on
the 110 valid traces is one additional Top-5 hit for the reconstruction.

No scorer change, paper edit, claims overwrite, RPC call, `cast` invocation, or
rerun was performed.
