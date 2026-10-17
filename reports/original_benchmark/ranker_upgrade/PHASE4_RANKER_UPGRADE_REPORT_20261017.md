# Phase 4 ranker upgrade — offline evidence report

**Date:** 2026-10-17
**Branch:** `ranker-upgrades-20261017`
**Scope:** saved provider-pinned predictions and saved ground truth only
**Network/RPC/cast:** none used in this phase
**Paper edits:** none
**Push:** none

## 1. Frozen holdout

The holdout was selected before inspecting miss causes and committed as:

`reports/original_benchmark/ranker_upgrade/holdout_20261017.json`

| Field | Value |
|---|---|
| Seed | `20261017` |
| Source population | 110 rows with `status=ok` |
| Holdout size | 20 |
| Development size | 90 |
| Stratification | chain × Top-5-hit status |
| Allocation | BSC hit 2, BSC miss 1, ETH hit 8, ETH miss 9 |
| ID-list SHA-256 | `5d7c4fffaa99348a2fa63ba05d9236acba29563ede6c09b957beb9adf6c3f2a7` |
| Freeze commit | `d65ebdd chore: freeze ranker upgrade holdout` |

The holdout IDs were excluded from miss classification, development outputs,
and development scoring. The holdout manifest contains the complete ID list.

## 2. Development miss classification

The remaining 90 rows contain 48 Top-5 misses. The classification command was:

```text
python scripts/research/analyze_ranker_misses.py
```

Artifact:

`reports/original_benchmark/ranker_upgrade/dev_miss_analysis_20261017.json`

Command output was also retained at:

`reports/original_benchmark/ranker_upgrade/dev_miss_analysis_command_output.txt`

### Counts

| Cause | Count | Evidence-bounded definition |
|---|---:|---|
| Trace too shallow | 18 | Target function text absent from retained cast-output tail and predictions |
| Label/selector mismatch | 16 | Target address or function-only candidate exists, but primary identity does not match |
| Produced but ranked low | 13 | Function candidate exists, first appearing after Top-5 |
| Candidate never produced | 1 | Target function text is retained in cast-output tail but absent from predictions |
| **Total** | **48** | |

The retained rows do not contain a complete structured call tree for every
case. Therefore “trace too shallow” is an evidence-bounded diagnosis, not a
new claim that the upstream trace itself was incomplete. Likewise, the single
candidate-never-produced case is the only such case supported by the retained
artifacts; no additional examples were invented to satisfy a quota.

### Five real examples per category where available

#### Trace too shallow — five examples

```text
0x00c5a772a58b117f142b2cbc8721b80d145ef7a910043ad08439863d0e78e300 | bsc | LPMine
0x06d7e7436414c658a33452d28400799f3637e83930dcec39b3bd065dabc6ef04 | eth | Zoomer
0x12fe79f1de8aed0ba947cec4dce5d33368d649903cb45a5d3e915cc459e751fc | eth | GFOX
0x1fe5a53405d00ce2f3e15b214c7486c69cbc5bf165cf9596e86f797f62e81914 | eth | EFVault
0x2a027c8b915c3737942f512fc5d26fd15752d0332353b3059de771a35a606c2d | eth | Balancer
```

Each was reported by the command as:

```text
no target function text retained in cast output tail or predictions
```

#### Label/selector mismatch — five examples

```text
0x0237855c63eb85c5f437fba5267cc869a08c58a49501e3e5ebec9990bdd97565 | bsc | ChannelsFinance | target-address candidate rank 1
0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb | eth | ZunamiProtocol  | target-address candidate rank 32
0x0eb8f8d148508e752d9643ccf49ac4cb0c21cbad346b5bbcf2d06974d31bd5c4 | eth | Game           | target-address candidate rank 1
0x1f1aba5bef04b7026ae3cb1cb77987071a8aff9592e785dd99860566ccad83d1 | eth | EFLeverVault   | target-address candidate rank 18
0x26a83db7e28838dd9fee6fb7314ae58dcc6aee9a20bf224c386ff5e80f7e4cf2 | eth | MIMSpell       | target-address candidate rank 2
```

The command evidence for these rows was:

```text
target address candidate exists but its function label did not match
```

#### Produced but ranked low — five examples

```text
0x1106418384414ed56cd7cbb9fedc66a02d39b663d580abc618f2d387348354ab | eth | GoodCompound   | first function rank 7
0x3d163bfbec5686d428a6d43e45e2626a220cc4fcfac7620c620b82c1f2537c78 | eth | Kashi          | first function rank 18
0x44aad3b853866468161735496a5d9cc961ce5aa872924c5d78673076b1cd95aa | eth | Indexed Finance | first function rank 11
0x485e08dc2b6a4b3aeadcb89c3d18a37666dc7d9424961a2091d6b3696792f0f3 | eth | KyberSwap      | first function rank 10
0x90fb0c9976361f537330a5617a404045ffb3fef5972cf67b531386014eeae7a9 | eth | SushiSwap      | first function rank 10
```

#### Candidate never produced — one evidence-supported example

Only one such example exists in the 90-row development population:

```text
0xe8277ef6ba8611bd12dc5a6e7ca4b984423bc0b3828159f83b466fdcf4fe054f | eth | JokInTheBox
```

The command evidence was:

```text
target function text retained in cast output tail but absent from predictions
```

The saved evidence does not contain five cases in this category, so the report
does not manufacture four more.

## 3. General ranker changes

The implementation changes are in:

`faultseeker/function_analysis/function_ranker.py`

Tests added/updated:

- `tests/test_ranker_pattern_integrity.py`
- `tests/test_explicit_function_rank_order.py`

### Change A — renderer-annotation canonicalization and grouping

Call renderers can append value annotations such as:

```text
makeBid{value: 14700000000000001}
```

The ranker now removes only the renderer-only trailing `{...}` annotation,
preserves ABI parentheses, and groups candidates by canonical function label
and address. The raw candidate is not keyed to any transaction, label, or
paper number.

### Change B — deterministic depth-aware tie ordering

Candidates remain ordered by descending distinct-call count. When counts tie,
This is a general evidence-ordering rule; it has no transaction-specific
condition, threshold tuned to a paper value, or label lookup from ground truth.

The raw trace-too-shallow category was the largest category, but its retained
rows do not expose missing candidates from which an offline ranker can create
new evidence. The second change therefore improves ordering of candidates that
are present while making no claim to repair absent trace evidence.

## 4. Development before/after — new offline measurement

Command:

```text
python scripts/research/evaluate_ranker_upgrade_offline.py
```

Artifact:

`reports/original_benchmark/ranker_upgrade/dev_rerank_comparison_20261017.json`

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Primary Recall@1 | 19/90 = 21.11% | 29/90 = 32.22% | +11.11 pp |
| Primary Recall@3 | 39/90 = 43.33% | 44/90 = 48.89% | +5.56 pp |
| Primary Recall@5 | 42/90 = 46.67% | 45/90 = 50.00% | +3.33 pp |
| Function-only Recall@1 | 22/90 = 24.44% | 31/90 = 34.44% | +10.00 pp |
| Function-only Recall@3 | 40/90 = 44.44% | 45/90 = 50.00% | +5.56 pp |
| Function-only Recall@5 | 44/90 = 48.89% | 46/90 = 51.11% | +2.22 pp |

The two changes altered saved prediction ordering/grouping for 89 of the 90
development rows. These are measurements on the already-inspected 110-row
source population, not a clean generalization result.

## 5. One-shot holdout — new measurement

After code freeze, the holdout was evaluated once using:

```text
python scripts/research/evaluate_ranker_holdout_once.py
```

Artifact:

`reports/original_benchmark/ranker_upgrade/holdout_new_measurement_20261017.json`

| Metric | One-shot holdout result |
|---|---:|
| Primary Recall@1 | 7/20 = 35.00% |
| Primary Recall@3 | 10/20 = 50.00% |
| Primary Recall@5 | 10/20 = 50.00% |
| Function-only Recall@1 | 8/20 = 40.00% |
| Function-only Recall@3 | 11/20 = 55.00% |
| Function-only Recall@5 | 11/20 = 55.00% |

This is labeled **new measurement**, is non-synthetic, used no network/RPC/cast
calls, and was not retuned after observing the result. The ranker source hash
at the one-shot evaluation was:

```text
acf6e1874aad2817ce9576a109a5acd922f2d7cb1d2b8c6e283672d926bd32f2
```

Because all 110 source rows had been inspected earlier, including the frozen
holdout's source population, these results are exploratory and must not be
presented as a clean generalization claim.

## 6. Verification and commit scope

Full test command:

```text
python -m pytest tests -q -p no:cacheprovider
996 passed, 7 skipped in 149.65s (0:02:29)
```

The final commit on this branch contains only the ranker code/tests, offline
research scripts, and new evidence artifacts under `reports/`. No paper file,
existing claims file, secret, endpoint, or push is included.
