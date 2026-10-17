# Round 2 ranker work — development-only report

**Label:** development, exploratory
**Branch:** `ranker-upgrades-20261017`
**Scope:** offline saved predictions and labels only
**Network/RPC/cast:** none
**Paper edits:** none
**Push:** none

The 20-row holdout from Round 1 was not evaluated again and was excluded from
every Round 2 analysis. Round 2 uses only the 90-row development population.
No ranker source change was accepted in this round: every tested candidate
either reduced the development result or was identical to the existing rule.

## 1. Current remaining misses

Round 1's current ranker was applied first. The development population has 45
remaining primary Top-5 misses:

| Cause | Count |
|---|---:|
| Trace too shallow | 18 |
| Produced but ranked low | 14 |
| Label/selector mismatch | 12 |
| Candidate never produced | 1 |
| **Total** | **45** |

Artifact:

`reports/original_benchmark/ranker_upgrade/round2_miss_analysis_20261017.json`

Command output:

`reports/original_benchmark/ranker_upgrade/round2_miss_analysis_command_output.txt`

### Five examples per cause where available

#### Trace too shallow — five examples

```text
0x00c5a772a58b117f142b2cbc8721b80d145ef7a910043ad08439863d0e78e300 | bsc | LPMine
0x06d7e7436414c658a33452d28400799f3637e83930dcec39b3bd065dabc6ef04 | eth | Zoomer
0x12fe79f1de8aed0ba947cec4dce5d33368d649903cb45a5d3e915cc459e751fc | eth | GFOX
0x1fe5a53405d00ce2f3e15b214c7486c69cbc5bf165cf9596e86f797f62e81914 | eth | EFVault
0x2a027c8b915c3737942f512fc5d26fd15752d0332353b3059de771a35a606c2d | eth | Balancer
```

The retained evidence for these rows contains neither the target function in
the prediction list nor target function text in the retained cast-output
tail. This is an evidence-bounded diagnosis; no new trace was fetched.

#### Produced but ranked low — five examples

```text
0x256979ae169abb7fbbbbc14188742f4b9debf48b48ad5b5207cadcc99ccb493b | eth | MorphoBlue
0x2881e839d4d562fad5356183e4f6a9d427ba6f475614ce8ef64dbfe557a4a2cc | eth | MahaLend
0x3bba4fb6de00dd38df3ad68e51c19fe575a95a296e0632028f101c5199b6f714 | eth | Burner
0x3d163bfbec5686d428a6d43e45e2626a220cc4fcfac7620c620b82c1f2537c78 | eth | Kashi
0x44aad3b853866468161735496a5d9cc961ce5aa872924c5d78673076b1cd95aa | eth | Indexed Finance
```

Their current function-only candidate ranks were 6, 8, 7, 19, and 10
respectively.

#### Label/selector mismatch — five examples

```text
0x0237855c63eb85c5f437fba5267cc869a08c58a49501e3e5ebec9990bdd97565 | bsc | ChannelsFinance
0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb | eth | ZunamiProtocol
0x1f1aba5bef04b7026ae3cb1cb77987071a8aff9592e785dd99860566ccad83d1 | eth | EFLeverVault
0x26a83db7e28838dd9fee6fb7314ae58dcc6aee9a20bf224c386ff5e80f7e4cf2 | eth | MIMSpell
0x4f4d6909a442b4d86f79a9044dcada6a128ddd9f62c26f410134a72d2fc31389 | eth | MaestroRouter2
```

#### Candidate never produced — one example available

```text
0xe8277ef6ba8611bd12dc5a6e7ca4b984423bc0b3828159f83b466fdcf4fe054f | eth | JokInTheBox
```

Only one case met this evidence-bounded definition, so four additional cases
were not invented.

## 2. Label/selector audit

There were 12 current label/selector-mismatch cases. The audit applied generic
normalization to both sides: case folding, removal of function argument text,
renderer-only value annotations, and the existing selector-to-name cache.
No transaction-specific alias was added.

| Audit result | Count | Meaning |
|---|---:|---|
| Address-identity mismatch with function-equivalent candidate | 1 | ParticleTrade: function names equivalent, but predicted address differs from the labeled address |
| True target-address wrong-label miss | 11 | The target address appeared, but no generic function/selector normalization matched the labeled target function |
| Selector-to-name naming issue | 0 | No safe case found |
| Overload-signature naming issue | 0 | No safe case found |
| Renderer-annotation naming issue | 0 | Already handled by Round 1 canonicalization |

The one function-equivalent case is an address-identity problem, not a safe
name normalization opportunity. It may reflect proxy/implementation identity,
cases are true misses under the primary address-plus-function identity rule.

**Round-2 normalization decision:** no change. Stripping leading underscores,
for example, would conflate distinct Solidity functions such as `_transfer`

## 3. Scoring-signal trials

The current Round 1 rule is count descending, then maximum supporting call depth,
then stable encounter order. Each alternative was tested independently on all
90 development rows. The saved prediction fields contain `count` and call
depths, but no storage-write or value-flow fields.

Artifact:

`reports/original_benchmark/ranker_upgrade/round2_signal_trials_20261017.json`

All values below are **development, exploratory** measurements.

| Trial | Primary R@1 | Primary R@3 | Primary R@5 | Function-only R@1 | Function-only R@3 | Function-only R@5 | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| Current count → max depth | 29/90 | 44/90 | 45/90 | 31/90 | 45/90 | 46/90 | Baseline retained |
| Max depth → count | 27/90 | 39/90 | 42/90 | 29/90 | 41/90 | 44/90 | Drop |
| Depth span → count | 27/90 | 41/90 | 43/90 | 29/90 | 42/90 | 44/90 | Drop |
| Count → depth span | 29/90 | 44/90 | 45/90 | 31/90 | 45/90 | 46/90 | Identical; drop |
| Frequency only | 29/90 | 44/90 | 45/90 | 31/90 | 45/90 | 46/90 | Identical; drop |

Storage-write and value-flow signals were unavailable in the saved prediction
artifacts, so they were not fabricated or approximated.

## 4. Round-2 before/after

Because no normalization or scoring change passed the development-only test,
the accepted ranker remains unchanged. The Round-2 before/after is therefore
intentionally identical:

| Metric | Before Round 2 | After Round 2 |
|---|---:|---:|
| Primary Recall@1 | 29/90 = 32.22% | 29/90 = 32.22% |
| Primary Recall@3 | 44/90 = 48.89% | 44/90 = 48.89% |
| Primary Recall@5 | 45/90 = 50.00% | 45/90 = 50.00% |
| Function-only Recall@1 | 31/90 = 34.44% | 31/90 = 34.44% |
| Function-only Recall@3 | 45/90 = 50.00% | 45/90 = 50.00% |
| Function-only Recall@5 | 46/90 = 51.11% | 46/90 = 51.11% |

## 5. What remains unfixed

- 18 cases lack enough retained trace evidence for a ranker-only repair.
- 14 cases have a target function candidate, but current evidence ordering does
  not place it in Top-5.
- 11 cases have a target-address candidate with a genuinely different function
  label under generic normalization.
- 1 case has a function-equivalent candidate at a different address.
- 1 case has target function text in the retained cast tail but no prediction.
- Storage-write and value-flow ranking signals cannot be tested from the saved
  prediction schema.

To make a fresh generalization claim, the project would need a new, never-
inspected labeled transaction cohort with independent annotations, frozen chain
stratification, complete structured traces, explicit proxy/implementation
identity mappings, and recorded storage-write/value-flow features. The spent
20-row holdout must not be reused for that purpose.

## 6. Verification

Full test command:

```text
python -m pytest tests -q -p no:cacheprovider
```

Round 2 adds no ranker code change. The final commit contains only this report,
the current-ranker reclassification/trial scripts, and their development-only
artifacts. No paper, claims file, holdout result, RPC output, or network data
was added.
