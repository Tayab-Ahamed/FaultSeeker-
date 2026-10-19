| Fresh Batch E address endpoint | Hits | Recall | Wilson95% |
|---|---:|---:|---:|
| R@1 | 14/40 | 35.00% | [22.13, 50.49] |
| R@3 | 27/40 | 67.50% | [52.02, 79.92] |
| R@5 | 33/40 | 82.50% | [68.05, 91.25] |

| Original110 grouped5fold OOF, exploratory | R@1 | R@3 | R@5 |
|---|---:|---:|---:|
| Frozen baseline distinct addresses | 55/110 (50.00%) | 68/110 (61.82%) | 76/110 (69.09%) |
| Lane A observed-reference append | 55/110 (50.00%) | 70/110 (63.64%) | 79/110 (71.82%) |
| Lane B verified selector/storage fallback | 55/110 (50.00%) | 68/110 (61.82%) | 76/110 (69.09%) |
| Lane B corrected fixed bigram | 62/110 (56.36%) | 71/110 (64.55%) | 79/110 (71.82%) |
| Lane B nested lexical selector | 59/110 (53.64%) | 72/110 (65.45%) | 79/110 (71.82%) |
| Serial inner-OOF rank stack, best of6 | 59/110 (53.64%) | 72/110 (65.45%) | 79/110 (71.82%) |
| Lane C selected margin + A append | 62/110 (56.36%) | 75/110 (68.18%) | 82/110 (74.55%) |
| Integrated combined method, exact per-row parity | 62/110 (56.36%) | 75/110 (68.18%) | 82/110 (74.55%) |

55% development milestone reached.60% development target66/110 NOT reached. Fresh top1 is35%; desired top1 performance did not survive this fresh sample. No causal model-vs-baseline fresh improvement is claimed because no fresh baseline comparison was preregistered/run. No paper-number claim is supported by this run.

| Request accounting | Count |
|---|---:|
| dRPC network requests | 121 |
| Initial sandbox DNS-blocked dispatch | 1 |
| Total RPC dispatch ledger entries | 122 |
| Public registry requests | 323 |
| Total dispatches including DNS failure | 445 |
| Rate-limit hits | 0 |
| Billing/quota prompts | 0 |
| LLM/provider-generation calls | 0 |
| Batch E ranking pass | 1 |
| Batch E scoring pass | 1 |
| New estimated paid cost | $0 |
| Existing cumulative estimated paid ledger | $1.990589700 |
| Historical pending reservation, unchanged | $0.000090000 |
| Paid cap | $10 |

Billing was not independently invoice-verified. No paid-plan prompt was accepted. Initial sandbox DNSfailure was diagnosed without a key-bearing diagnostic call; one separately logged network-corrected run completed. Prior failed capture remains preserved.

50 source labels were frozen before collection; the fixed first40 all verified, so no reserve substitution or prediction-based exclusion occurred. Ethereum chainID, matching transaction/receipt hashes, successful receipts and callTracer responses were checked. Source bytes and exact header lines are pinned. These are public PoC vulnerable-contract target annotations, not independent root-cause adjudication. Source upstream commit is unavailable; cached bytes are SHA256-pinned. This is a convenience sample, not a random population sample.

Exact function/selector metrics: N/A, no fabricated labels. Generic4byte names are not verifiedABI and may differ from original cast decoding. Unknown names remained literal/lexicallyempty. All323 observed selectors were queried independently of labels. Literal selectors remain in captured canonical traces. Original110 OOF contains109 unique hashes; repeated selection is exploratory. C676 baseline-minus-zero versus B677 difference leaves baseline recall unchanged; Aexpanded target coverage87/110 vs84. Wilson intervals are nominal record-level binomial intervals and do not correct dependence, convenience sampling or model selection.

Selected model SHA256: `80967ef99b633123975d10bab0a6a37f473caf42cd772c9b92fad732985f3037`. Cohort SHA256: `06482a69d165265709167803765664b00947db44d978c8421d824b8c43e1dc94`. Runtime frozen commit: `b7565ef9addf9a67bd3d3bd47fb73c17f6749982`. All40 predictions were completed before scorer accessed target addresses. Offline audit guard blocked any network/subprocess dispatch during inference; permanent score lock was acquired before computing hits. No full-data training accuracy was reported.

Verification:31 focused integrated tests passed after scoring. Serial stack2 isolation tests passed.469 evidence files scanned with0 configured-secret-value matches. Read-only result verifier checks saved ranks/metrics/requestcounts and frozen hashes; it does not rerun ranking/scoring. No full-suite-green claim: frozen spent-batch readers were excluded. No original test, paper or README was edited in this continuous run. Existing unrelated dirty evidence was preserved. No pushes/main commits; parallel agents were stopped at user request and all later work was serial.

Executed from repository root:

```powershell
python scripts/research/verify_selected_localizer_parity.py
python scripts/research/freeze_selected_localizer.py
python scripts/research/build_batch_e.py
python scripts/research/collect_batch_e.py
python scripts/research/collect_batch_e.py network-retry
python scripts/research/decode_batch_e.py
python scripts/research/score_batch_e.py
```

These are executed-once provenance commands, not permission to rerun frozen stages. Safe read-only verification command:

```powershell
python scripts/research/verify_batch_e_result.py
```

Current state: Batch E is spent and must stay frozen. No tuning, rescoring or fresh batch generation follows this result without a new task. The60% target remains unmet.

```text
localization-continuous-merge
22831be research: record single fresh Batch E address score14 27 33 of40
b7565ef research: freeze complete selector evidence and offline one-shot runtime
259d7f7 test: verify decoded runtime preserves selectors before fresh scoring
cc580a1 research: preserve40 verified fresh Ethereum captures before inference
5594186 research: add label-separated one-shot frozen Batch E inference and scoring
4ed70a7 research: add complete observed-selector registry acquisition without labels
b3c07ec research: preserve DNS-blocked dispatch and allow one network-corrected capture
734b725 research: add throttled frozen Batch E RPC collection without scoring
5b1fe10 research: freeze50 fresh source labels for40-row Batch E
26495b6 research: add cached-source Batch E labeling and identity exclusions
7f5e3c7 research: preregister fresh address-only Batch E before acquisition
251701e research: freeze selected localizer weights before fresh evidence
f38bbce research: add one-time selected-model freeze without training metrics
6c56e9c research: verify exact original110 selected-localizer parity
60c7274 research: wire selected learned localizer and strict parity check

localization-coverage
f35eb78 research: verify C11 outcomes and clarify zero-address prefix coverage
3a8c42c research: add offline-tested fresh evaluation safety gates
6209948 research: inventory shared candidate contracts without changing folds
25e6f25 research: clarify lexical adjacency and target-only contract grouping limits
9eaa4d8 research: independently verify B4 C8 counts hashes folds and merge gates
1586d10 research: verify corrected lexical OOF counts and review combined isolation
b5efc8a research: review fold isolation and lexical selector ambiguity
21d1ec8 research: record rejected OOF topology grids and reusable features
85cbe55 research: preregister saved path topology experiment
6ea6471 research: audit scoped original runtime cache completeness
c08e5e4 research: add pure trace candidate coverage and grouped OOF evidence
2ffbe86 research: pin lane A coverage protocol
09c5446 research: preserve original110 address OOF foundation
522d5f9 results: record Batch C phase 2 scoring
7493545 fix: accept pre-Byzantium receipts with root (exploratory, before Batch C scoring)

localization-selector
3d8f8a9 research: record honest serial nested stacking outcomes
2458063 research: implement serial inner-fold rank stacking with isolation tests
ce19620 research: preregister inner-OOF rank stacking
275ddfa research: preserve aborted duplicate kernel attempt
25e7ebf research: preregister five nonlinear lexical kernels
2444d1a research: independently verify label-free hybrid append
3fb33c9 research: add response-bound generic registry decoder
65e2e5b research: freeze response-bound generic decoding policy
0e5b7e9 research: specify provenance requirements for prospective generic decoder
d39ab57 research: preserve nested59-hit result and fresh-decoder limitation
cfc7784 research: record62-hit lexical result and preregister nested selector
9a81a48 research: preregister finite lexical representation diagnostic
2742f04 research: exclude bare selectors and preserve corrected lexical OOF
fa59672 research: preregister exclusion of bare selector identifiers
8725d71 research: preregister grouped nested lexical selection

localization-learned
a426355 research: preserve rejected token interaction OOF results
40edc05 research: preregister lexical rank structural interactions
e68318e research: record kernel results and exact candidate pool audit
180eac0 research: preregister nonlinear kernel ranking models
11b5467 research: record margin and weak regularization outcomes
23a8297 research: record relative numeric sublinear experiment
a67de5e research: preregister linear margin and weak regularization diagnostics
1385fec research: preregister relative numeric sublinear lexical models
140aeef research: preserve baseline rank loss trials and 62 73 82 hybrid
56ebedc research: preregister baseline pairwise listwise and append hybrid
b3b9a2e research: record expanded bigram results
4e7fae7 research: preregister expanded bigram address models
1f58994 research: record corrected lexical combined rankers
5d98787 research: preregister corrected combined lexical evaluation
9461460 research: preserve interrupted lexical mixture experiment

```
