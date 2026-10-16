# Canonical-history paper versus repository map

All quantitative project assertions, formulas/settings and Tables IV-VI in uploaded eight-page implementation paper; repeated mentions consolidated. External literature grouped separately. Bibliographic indices, author contact digits, pagination and equation/figure numbers are identifiers, not measured claims. Extended JISA audit results explicitly separate.

No paper edits. No empirical promotion from fixture results, source declarations, model inputs or proxy classifiers.

**Correction to supplied premise:** the early CSV contains246 parsed unique records;248 physical data lines include two blanks. Fifteen hashes are malformed. Eight chains occur in all four CSV versions. This does not authenticate the claimed study.

## Numerical map

| Paper number/assertion | Verdict | Honest replacement and scope | Evidence |
|---|---|---|---|
| 246 authentic exploits (2021-2026) | COUNT-EXISTS-AUTHENTICITY-UNVERIFIED | 246 unique records existed, with 15 malformed EVM hashes; frozen fca6b99 has 231, current main 183 | cohort_history.json |
| 6 incident sources; 2 independent corroborating sources per incident | UNSUPPORTED | Source catalog and incident disclosure/detection links recovered; no complete per-row independence/adjudication chain | manifest.json; cohort_history.json |
| 2 qualified independent annotators; approximately 8% disagreement | UNSUPPORTED | 115 original files / 114 unique transaction hashes; 48 Oct 6 reconstructions separate; no annotator attestations or disagreement log | cohort_history.json |
| 10 EVM chains; Table III 10+ | CONTRADICTED-COHORT | 8 chains in every fixed CSV version; wider candidate pool is a different, unvalidated population | cohort_history.json |
| Ethereum 47.6%, other chains 52.4% | CONTRADICTED-FROZEN-CSV | 132/231 = 57.1429% Ethereum, 42.8571% others; not adjudicated population estimates | cohort_history.json |
| 80+ vulnerability types with SWC/DASP labels | LABEL-STRINGS-ONLY | 82 distinct vuln_type strings at fca6b99; 89 in early 246 and 69 in current 183. Semantic uniqueness and correctness unadjudicated | cohort_history.json |
| Simple: 6.5% | CONTRADICTED-FROZEN-CSV | 19/231 = 8.2251% legacy labels; authentic trace-based class adjudication unavailable | cohort_history.json |
| Moderate: 33.3% | CONTRADICTED-FROZEN-CSV | 62/231 = 26.8398% legacy labels; authentic trace-based class adjudication unavailable | cohort_history.json |
| Complex: 32.5% | CONTRADICTED-FROZEN-CSV | 91/231 = 39.3939% legacy labels; authentic trace-based class adjudication unavailable | cohort_history.json |
| Exceptionally Complex: 27.6% | CONTRADICTED-FROZEN-CSV | 59/231 = 25.5411% legacy labels; authentic trace-based class adjudication unavailable | cohort_history.json |
| Moderate + Complex 65.8%; bins <=5, 6-50, 51-500, >500 functions | PROPORTIONS-UNSUPPORTED | 153/231 = 66.2338% by stored class; bins are definitions, not proof that class assignments obey them | cohort_history.json |
| 18/246 = 7.3% reentrancy | CONTRADICTED-LABEL-COUNT | 17/231 = 7.3593% at fca6b99; 19/246 early, 17/213 Oct 6, 16/183 current; labels are not independently verified exploit outcomes | cohort_history.json |
| Table V SSTORE P=.89, R=.83, F1=.86 | UNSUPPORTED | Undefined: canonical recompute evaluated 0 transactions | findings.json; snapshots/*/reports/research_results/reentrancy_metrics.json |
| Table V structural P=.72, R=.67, F1=.69 | UNSUPPORTED | No empirical precision, recall or F1; Oct 6 structural F1 null | findings.json |
| Table V repeated-address P=.54, R=.61, F1=.57 | UNSUPPORTED | No empirical precision, recall or F1; Oct 6 baseline F1 null | findings.json |
| 17 / 29 percentage-point F1 gains | UNSUPPORTED | Undefined without paired detector predictions on adjudicated data; proxy classification F1 is a different endpoint | findings.json |
| 18 positives with rounded P=.89 and R=.83 | INCOMPATIBLE-WITH-SINGLE-POOLED-MATRIX | No integer pooled confusion matrix fits both rounded values; macro/trial averaging would require its missing definition | ../claim_closure/numeric_constraints.json |
| 100 paired transactions, tier mix 5:3:2 (~50/30/20%) | ASSUMED-NOT-OBSERVED | No authenticated paired workload/query log; these fractions are modeling inputs | findings.json |
| Tier 1 $0; Tier 2 hybrid $0.05 vs cloud $0.12; Tier 3 $0.12 both | MODEL-INPUTS | Local API fee assumed zero; query costs assumed, not observed token usage or total ownership cost | findings.json |
| Approximately 58% overall inference saving | CONTRADICTED-ARITHMETIC | 35% modeled; measured savings unavailable | findings.json |
| 58% origin | ARITHMETIC-ONLY | (0.12-0.05)/0.12 = 58.3333% Tier-2-only; mixture hybrid $0.039 vs cloud $0.060/query, 35% overall | findings.json |
| GPT-4o-mini $0.15 input/$0.60 output per million tokens; ~4 characters/token | HISTORICAL-ASSUMPTIONS | Versioned price estimates and character-token approximation are not dated invoices or actual token measurements | manifest.json; ../claim_closure/environment.json |
| Hybrid/cloud ranking differences <5% of transactions; Tier 3 quality maintained | UNSUPPORTED | No paired ranked outputs/quality measurements | findings.json |
| Approximately 40% clean traffic skips Stage 2; bypassing filter increases time ~40% | UNMEASURED | BENIGN skip mechanism tested; neither population rate nor paired latency effect measured | findings.json; ../claim_closure/claims/20.json |
| 23% of Cloudflare explorer challenges bypassed via JSON-RPC fallback | UNSUPPORTED | RPC fallback capability is not a challenged-request success denominator; no authorized recorded cohort | ../claim_closure/claims/27.json |
| Table VI reentrancy PMS/CES/TCS/LCS/overall: .82/.71/.76/.73/.76 | UNSUPPORTED | No observed per-function component vectors or declared aggregation; no substitute from gas/call-count features | ../claim_closure/claims/28.json |
| Table VI flash loan PMS/CES/TCS/LCS/overall: .78/.64/.82/.70/.74 | UNSUPPORTED | No observed per-function component vectors or declared aggregation; no substitute from gas/call-count features | ../claim_closure/claims/28.json |
| Table VI price manipulation PMS/CES/TCS/LCS/overall: .75/.60/.79/.68/.71 | UNSUPPORTED | No observed per-function component vectors or declared aggregation; no substitute from gas/call-count features | ../claim_closure/claims/28.json |
| Table VI access control PMS/CES/TCS/LCS/overall: .70/.68/.65/.72/.69 | UNSUPPORTED | No observed per-function component vectors or declared aggregation; no substitute from gas/call-count features | ../claim_closure/claims/28.json |
| Table VI logic bug PMS/CES/TCS/LCS/overall: .55/.58/.60/.61/.58 | UNSUPPORTED | No observed per-function component vectors or declared aggregation; no substitute from gas/call-count features | ../claim_closure/claims/28.json |
| 20 randomly selected cases; top-1 68% to 81% | UNSUPPORTED | No selected cases, policy or paired rankings in recovered history; n=20 binary accuracy has 5-percentage-point steps | history_search.json; guidance_history_search.txt |
| Compound cToken legitimate recursion true negative | UNIDENTIFIED-CASE | Narrative recovered in historical JSON but no transaction hash/trace/source mapping; Compound exploit annotations do not identify this benign control | history_search.json; manifest.json |
| 201 passing tests | VERIFIED-LOCAL-SCOPE | 201 original cases still pass with original source hashes unchanged; current full suite separately reported | ../claim_closure/claims/02.json |
| 3 stages; 5 signal categories; 3 router tiers; zero Stage 1 LLM calls | MECHANISM-OR-DEFINITION-SCOPE | Executed local mechanisms, not population-quality measurements | ../claim_closure/claims/09,16,19,20,23 |
| Table IV weights .55/.25/.20/.10/.10; depth span >=2, slot writes >=2 | MECHANISM-OR-DEFINITION-SCOPE | Paper profile executed by existing behavioral/compiled tests; canonical legacy JSON has write_before_and_after=.20 instead of paper .10 | ../claim_closure/claims/09,10 |
| 5 tiers >=.80/.55/.30/.10; structural 3 signals x.75 capped .80; mutex 1->2->1 | MECHANISM-OR-DEFINITION-SCOPE | Paper profile verified locally. Oct 6 canonical detector uses four different thresholds; its output is not the five-tier paper evaluation | ../claim_closure/claims/09,11,12 |
| EXPLOIT confidence >=.85, BENIGN bypass and UNCERTAIN escalation | MECHANISM-OR-DEFINITION-SCOPE | Executed local control flow, not measured false-positive/negative rates | ../claim_closure/claims/20 |
| Weights .30/.25/.25/.20; normalized [0,1] | MECHANISM-OR-DEFINITION-SCOPE | Executed relative heuristic score; paper itself says regression calibration is future work, despite calibrated label in figure | ../claim_closure/claims/23 |
| PMS 15 patterns +.20, repeat bonus .30; CES base .30 +.30 source +.20 confirmation; TCS .40 +up to .60; LCS default .50 | MECHANISM-OR-DEFINITION-SCOPE | Scoring definitions, not empirical calibration/quality evidence | ../claim_closure/claims/23 |
| 5 interpretability levels, very high >=.90, very low <.30 | MECHANISM-OR-DEFINITION-SCOPE | Display thresholds, not calibrated probabilities | ../claim_closure/claims/23 |
| EMA alpha=.2; LRU 512 entries, TTL 600s | MECHANISM-OR-DEFINITION-SCOPE | Local mechanism tests; chain/archive availability and real failover evidence remain scoped | ../claim_closure/claims/25 |
| 11 flash-loan borrow tokens; 10 callback tokens; 15 privileged selectors | MECHANISM-OR-DEFINITION-SCOPE | Pattern-list sizes are implementation definitions, not 80+ validated vulnerability coverage | ../claim_closure/claims/09 |
| 2 HITL checkpoints, 5 guidance types | MECHANISM-OR-DEFINITION-SCOPE | Feedback behavior exercised; 68->81% empirical effect remains unsupported | ../claim_closure/claims/24 |
| 6 provider backends | MECHANISM-OR-DEFINITION-SCOPE | Adapter construction tested; native/live family coverage incomplete, Ollama unreachable in previous run | ../claim_closure/claims/17 |
| Ubuntu22.04, Python3.10+, Foundry0.2.x, web3 6.x | MECHANISM-OR-DEFINITION-SCOPE | Declared historical environment, not proof all historical measurements ran there; current tests run in Windows/Python3.11 with local binaries | ../claim_closure/claims/31 |
| $100B secured; $3.8B lost in 2022; 16.7 analyst-hours; literature 84/115 incidents, 40+ Slither patterns, 0% complex-case recall | EXTERNAL-LITERATURE-NOT-REPOSITORY-EVIDENCE | Not verified by implementation/Git history; check cited primary publications separately. No replacement inferred | Uploaded paper pp1-3 |
| Text says 4 generations; Table I contains Gen1 through Gen5, periods 2016-2026; Table II 12 systems | DOCUMENT-INTERNAL-COUNTS | Table I has five generations; Table II has twelve rows. Publication dates/chronology require cited literature | Uploaded paper pp2-3 |
| F1 .969, FPR .003, +14.7pp, CI [.961,.975] | INVALID-EMPIRICAL-EVIDENCE | Legacy harness reads labels; old .9687 proxy CSV even has CI low .9798 > point estimate. Recovered audit rejects paper CI; no genuine matching run | manifest.json; recovered PAPER_CLAIM_AUDIT.md |
| Older strict harness .859, CI [.822,.895] | REPRODUCED-FEATURE-HARNESS | .8593, CI [.8223,.8950], TP174 FP0 TN1000 FN57; July 50853e4 heuristic formula, not live LLM/full pipeline and not calibrated OOF | reruns/50853*/status.json |
| Honest five-fold result .759 | REPRODUCED-FEATURE-HARNESS | .7586, CI [.7071,.8040], P.88 R.6667 FPR.021, TP154 FP21 TN979 FN77; frozen231 exploit +1000 benign-feature rows | reruns/8e02*/status.json |
| Stored -TIG F1 .6565 | RERUN-DISAGREES | Byte-pinned rerun .6531 (TP128 FN103), not .6565 (TP129 FN102); other seven scorer results match. No tuning to reproduce the discrepant row | reruns/8e02*/status.json; findings.json |
| Static .4808, dynamic .3733, LLM-only .6120; ablations .7556/.6565/.6889/.7586 | PROXY-CLASSIFIER-SCOPE | Rerun static .4808, dynamic .3733, formula named LLM-only .6120; -FAEGL .7556, -TIG .6531, -calib .6889, -routing .7586. Routing ablation returns same scorer, not actual routing experiment | reruns/8e02*/status.json; snapshots/*/benchmark/run_honest_experiments.py |
| Retention >=.94; .9412/.9647/1/1/.9529 | UNSUPPORTED-EMPIRICAL-OUTCOME | Old harness uses synthetic two-node trace and literal analyzer deltas; newer CSV retains illustrative .85 baseline scores without raw challenged production runs | manifest.json |
| Localization top-1 6.09% | RECORDED-NOT-REPRODUCED | Stored 7/115 targets =6.09%, top3 23/115=20%, top5 36/115=31.30%, top10 48/115=41.74%, MRR .173; 115 GT files cover114 unique transactions. Raw rankings unavailable in all53 reachable commits | findings.json; history_search.json |
| 1059 exploits +10000 benign =11059; 231 fully annotated; 124/121 tests in earlier audit | MIXED-POPULATIONS | 1059 includes828 candidate exploits, not all validated; extended CV uses1231 records=231+1000. 115 original GT files cover114 unique hashes; declarations are not independent labels | manifest.json; cohort_history.json |
| Stage1 2.3+/-0.4s; cloud 8.1+/-1.2s; hybrid 3.4+/-0.8s | REMOVED-UNMEASURED | Oct 6 artifact latency=null; no production timing observations to substitute | findings.json |

## Reopened registry decisions

| Claim | Status / paper verdict | Evidence decision | Single next input bundle |
|---|---|---|---|
| 3 | UNVERIFIABLE / COUNT-EXISTS-AUTHENTICITY-UNVERIFIED | Early 246 unique records existed (15 malformed hashes), then231/213/183. Original115 files cover114 unique tx; reconstructions48 are separate. No fully authenticated 246-row adjudicated cohort. | Frozen cohort with complete independent provenance and qualified annotation records |
| 4 | UNVERIFIABLE / PARTIAL-PROVENANCE-RECOVERED | Original April3 GT and source catalog/disclosure links are recovered, not manufactured in October. They do not contain two qualified annotator attestations or a complete independent evidence chain per row. | Per-row independent corroboration plus signed independent annotation/consensus ledger |
| 5 | UNVERIFIABLE / CONTRADICTED-FROZEN-CSV | Every fixedCSV version has8chains, not10; fca6b99 Ethereum132/231=57.1429%, not47.6%. Unvalidated candidate-pool coverage is a different denominator. | Accepted frozen study cohort and independently verified chain membership |
| 6 | UNVERIFIABLE / STRINGS-COUNTED-NOT-ADJUDICATED | fca6b99 has82 distinct vulnerability strings with SWC/DASP columns; original GT supports partial named targets but semantic taxonomy uniqueness/correctness is not adjudicated. | Adjudicated SWC/DASP label mapping and semantic deduplication for the frozen cohort |
| 7 | UNVERIFIABLE / CONTRADICTED-FROZEN-CSV | 231-row class counts Simple19/Moderate62/Complex91/Exceptional59 differ from paper proportions. The early246 also differs (20/71/93/62). | Trace-verified function-count bins for the authentic paper cohort |
| 8 | UNVERIFIABLE / CONTRADICTED-LABEL-COUNT | 17 reentrancy strings among231 and213,16amongcurrent183,19amongearly246. No18-row authenticated study. Label counts are now checkable, label truth is separate. | Independently adjudicated reentrancy positives in the frozen evaluation cohort |
| 13 | UNVERIFIABLE / PUBLISHED-METRICS-UNSUPPORTED | Historical .86/.69/.57 were literal result declarations; Oct6 recompute evaluates0 and emitsnull F1. Reproduced .7586/.8593 feature classification has a different target and cannot validate TableV. | Paired raw detector predictions/confusion counts on adjudicated positives and negatives with defined averaging |
| 14 | UNVERIFIABLE / PUBLISHED-GAINS-UNSUPPORTED | 17/29pp are arithmetic between unsupported TableV declarations. Feature-harness ablations are different mechanisms/endpoints; even -TIG recorded .6565 differs from rerun .6531. | Paired executed SSTORE/structural/repeated-address outcomes on the same adjudicated rows |
| 15 | UNVERIFIABLE / CASE-NARRATIVE-RECOVERED-HASH-MISSING | Historical reentrancy_metrics.json contains the cToken narrative with no hash. Compound-related exploit annotations cannot identify the legitimate recursive transaction. | Exact legitimate cToken case-study transaction plus source linkage |
| 17 | UNVERIFIABLE / LIVE-CONFORMANCE-STILL-INCOMPLETE | Canonical adapter/pricing declarations add no authenticated Claude/Qwen/Ollama response. Prior gateway failures remain recorded; native adapters untested, not inferred failed. | Eligible live family access including a reachable installed Ollama model |
| 18 | UNVERIFIABLE / 58-PERCENT-OVERALL-CONTRADICTED | Canonical Oct6 removes58%; the published mixture computes35% modeled, with no observed100-case paired workload. No ranking-quality comparison or token billing log. | Frozen100-case paired workload with observed usage, pricing and quality outputs |
| 21 | UNVERIFIABLE / RATE-UNMEASURED | Canonical runtime artifact explicitly marks benign prefilter rate unmeasured. Executed skip mechanism does not establish40% of traffic or paired latency effect. | Verified benign workload and paired prefilter latency observations |
| 22 | UNVERIFIABLE / HISTORICAL-AGGREGATE-RECOVERED | Recovered top1 7/115=6.09% and114 per-tx provenance entries; original GT contains one duplicate transaction explaining target/tx difference. No tracked raw ranked outputs in any reachable canonical commit; cannot rerun localization. | Original per-transaction ranked predictions tied to traces/models and source-linked GT |
| 25 | UNVERIFIABLE / CAPABILITY-DECLARATIONS-NOT-LIVE-PROOF | Canonical data covers8chains; ten-chain provider declarations and protocol add no live archive/opcode/failover observations beyond prior Ethereum probes and replay. | Required-chain archive/debug observations and live provider recovery evidence |
| 27 | UNVERIFIABLE / RATE-UNSUPPORTED | Recovered protocol and audit do not supply challenged-request denominator or successes for23%. Ethereum RPC success is not an explorer WAF bypass experiment. | Authorized challenged explorer-request corpus with recovery logs and denominator |
| 28 | UNVERIFIABLE / NO-PRODUCTION-SCORE-VECTORS | No TableVI component observations; CV classifier derives proxy factors from four numeric trace features, not PMS/CES/TCS/LCS for actual candidate functions. | Raw production per-function four-factor scores with adjudicated categories and declared averaging |
| 29 | UNVERIFIABLE / GUIDANCE-RESULT-UNSUPPORTED | All53 reachable canonical text versions searched: no68%-to81% paired study; binary n20 increments5pp. 6.09% localization belongs to another study, not guidance. | Original20-case selection/policy and paired rankings with explicit aggregation definition |
| 30 | UNVERIFIABLE / PARTIAL-REPRODUCTION-NOT-PAPER-REPLICATION | Canonical protocol recovered; two historical proxy/feature harnesses actually reproduced offline without tuning. They do not reproduce TableV/VI/guidance or authenticate the paper cohort. | Authentic paper-study input/output artifacts and exact experiment protocol |

## Result lineage and limits

- `manifest.json` binds every cached upstream file to a full commit, Git blob identity and SHA-256; `cohort_history.json` records all four distinct fixed-CSV blobs across53 commits/two advertised branches. No assertion about unadvertised/private/unreachable history.
- Original115 GT JSONs first added Apr3 are physically separate from48 Oct6 reconstructions. They contain114 unique hashes, all present in frozen231. This recovers genuine historical annotations, not complete paper-standard adjudication.
- The115-target/114-transaction localization denominator includes duplicate SorStaking. The evaluator can count one transaction twice. Reported7/115 cannot be reinterpreted as seven distinct transaction hits without raw predictions.
- Oct6 reentrancy artifact identifies213 input rows but names fca6b99 (whose committed CSV has231). Its SHA256 exactly matches CRLF rendering of the213-row later blob; no byte hash is silently normalized. The metrics remain null because no trace bundles were evaluated.
- `reruns/50853*/` reproduces the older .8593 [.8223,.8950] feature heuristic. `reruns/8e02*/` reproduces .7586 [.7071,.8040] out-of-fold feature classification. Each run freezes exact source/input bytes and default parameters; all network calls prohibited. Neither invokes actual LLMs, static tools or SSTORE detector.
- Seven of eight current recorded scorer rows reproduce exactly. -TIG differs (TP128/FN103 instead of129/102). Difference is reported, not repaired by threshold or weight changes. The old strict .859 table is historical, not an alternative headline for the newer CV run.
- `SYNTHETIC_DO_NOT_CITE` correctly rejects label-reading legacy outputs. Its later statement that .969 is real is stale; trust executable method and frozen inputs over README/result labels. `DATASET_INTEGRITY.md` also still describes231 while HEAD contains183.
- Main-result .759 and older .859 were computed by code on stored features; that is stronger than a literal number but weaker than authenticated end-to-end experimental evidence. Ground-truth quality remains a separate requirement.
- TableVI weighted means also differ slightly from products of rounded displayed components; without unrounded observations/aggregation this is rounding ambiguity, not grounds to invent corrected empirical values.
- Existing13 VERIFIED claims retain their previously documented implementation/sample scopes. The18 reopened publication claims remain UNVERIFIABLE, now with explicit contradiction/support verdicts and recovered evidence.

## Accounting and review

New paid/model/RPC calls:0. New paid spend:$0. Historical canonical-audit snapshot only: cumulative conservative ledger $0.809168 / $10 at that audit; subsequent work changed the ledger. See ../cohort_rebuild_v2/provider_pilot/FAILURE_AND_LEDGER_RECONCILIATION.json for the later accounting reconciliation. Fetch and offline arithmetic incur no provider charges.

Kluster waived for local development only; before any PR or push, repository AGENTS.md rules apply in full and Kluster review is re-enabled. No push performed.

Per-decision commits and post-commit full-suite records are published in `verification.json` after decisions complete. Original201 test-source digests are checked at every gate.

## Additional strict-control audit

The older .8593 run uses **1000 benign rows with exactly one distinct four-feature vector**. Its coverage gate checked populated columns but did not detect this degeneracy. The .8593 table is reproducible arithmetic on an unsuitable control population, not a stronger alternative to the later CV result. Exact input identity and counted vector are in `strict_control_audit.json`. This additional finding does not promote any claim or change the immutable decision-map JSON.

## Complexity definition check

Applying the stated 5/50/500 boundaries to the stored `functioncall_count` column gives 14/136/49/32 records in the four bins at 231 rows, and 14/148/50/34 at 246 rows. These differ both from the stored class labels and the paper proportions. Call count is not proven to mean unique functions, so these are conditional descriptive bins, not replacement authenticated complexity outcomes. Ethereum is 142/246 (57.7236%) in the early CSV, as well as 132/231 (57.1429%) in the requested frozen version. Exact input hashes and all version counts: `cohort_definition_audit.json`.


## Subsequent authentic TRAIN evidence (checkpoint, not final exam)

The numerical map above records the canonical-history audit. New provenance-complete work admits 14 exploits across six chains, frozen into 10 TRAIN and four sealed held-out identities; it does not authenticate 246 exploits across ten chains. Source-consensus annotation follows the user-approved two-independent-security-publisher policy, not invented human reviewer attestations.

| Claim / endpoint | New actual observation | Scope / remaining limitation |
|---|---|---|
| Table V structural reentrancy | P=5/6, R=5/5, F1=0.9090909091, nine observed TRAIN cases | One of ten TRAIN cases lacks a call trace; not overall exploit F1 |
| Table V repeated-call baseline | P=5/9, R=5/5, F1=0.7142857143, nine observed TRAIN cases | Same available call-trace population |
| Table V full opcode detector | TP2 / FP0 / FN0 / TN3; P=R=F1=1.0 | Five availability-selected TRAIN cases only; no full-cohort or held-out inference |
| Paired 17 / 29 point gains | 0 / 42.8571428571 percentage points | Same five identities for all three variants; deltas -17 / +13.8571428571 points; not the paper population |
| Localization top-1 / top-5 / MRR | Count ranking: 0 / 0 / 0.03598484848 on two source-linked cases | Deterministic count ranking, not complete model-assisted localization |
| Multi-agent quality / claimed localization gains | Unmeasured | Twenty actual Agnes 2.5 Flash requests across two stopped/capped batches produced zero complete cases; partial answers are unscored |
| Benign prefilter | 30 actual Stage1 controls UNCERTAIN; zero skip-eligible | 32 distinct EOA transfers admitted; 30 call traces, two failures. No paired speedup or general benign-contract rate inferred |
| Native historical storage evidence | Gnosis: 236237 steps, 1354 SLOAD, 186 SSTORE, 519 frames | Direct native node trace, receipt identity and normalization checked; four metered attempts including one failed connection |
| 58% cost savings | Unmeasured | Pilot is cloud-only, without paired local/cloud quality or billed savings. Real token usage does not turn a conservative price estimate into an invoice |

Evidence: ../cohort_rebuild_v2/experiments/20261015T180152-ca8176ca/summary.json; ../cohort_rebuild_v2/paired_gains/20261015T180152-ca8176ca/summary.json; ../cohort_rebuild_v2/provider_pilot/COMBINED_PILOT_REPORT.json. Both model batches together used exactly 20 requests, conservative estimate $0.1008808. Cumulative ledger at second batch completion: $1.9261888 / $10, billing unconfirmed. Paper unchanged; held-out final exam not consumed. This checkpoint does not claim Phase 2 or Phase 3 complete.

### Execution-backed source evidence checkpoint (2026-10-16)

Claim 22 remains UNVERIFIABLE. Actual source-mapping runs link 232/543 Euler and 227/439 Revest TRAIN storage operations to verified source byte/line spans; remaining operations lack cached runtime source. These counts measure input evidence coverage, not localization accuracy. Production processing prompts now consume the spans with capture hashes; no model-assisted case has completed. The latest deterministic TRAIN localization remains top-1=0, top-5=0, MRR=0.03598484848484848 over two available cases (ranks 33/24); overall component F1 remains 0.9090909 over nine available cases. No held-out exam or new gateway request was dispatched. Reproduce input evidence with `python scripts/export_train_execution_source_spans.py`; latest source-bound export: `reports/cohort_rebuild_v2/execution_source_spans/20261016T001414-e8718971/summary.json`.


### Real TRAIN semantic failure: Beanstalk

The accepted Beanstalk execution transaction `eth:0xcd314668aaa9bbfebaf1a0bd2b6553d01dd58899c508d4729fa7311dc5d33ad7` reproduces a structural score of 0.80 / CONFIRMED_REENTRANCY from its authentic captured call tree. Same-function/cross-function callback nesting is present inside an address CertiK identifies as the attacker contract. The accepted CertiK/Halborn-backed root-cause annotation is flash-loan governance capture, with reentrancy_label=false. Thus callback existence and exploit causality are different endpoints here; the negative root-cause label is retained.

Evidence: ../cohort_rebuild_v2/BEANSTALK_REAL_FAILURE_ANALYSIS.json binds the actual successful call paths, transaction/receipt admission, publisher artifacts, annotation and relevant unchanged detector sources. This is one selected TRAIN failure diagnosis, not a new F1 estimate, ablation, localization result or held-out observation. No weights, thresholds or labels changed. The five-case full-opcode result cannot resolve this transaction because it lacks a full opcode observation in that experiment. Claim 13 remains UNVERIFIABLE for the paper's overall F1/CI. No synthetic data or new network calls were used.

The follow-up real-input collision check reproduced all nine structural observations with unchanged relevant detector source. `same_function_reentry / cross_function_reentry / reentry_before_return = true / true / true` occurs in five reentrancy positives and one governance-capture negative. A deterministic classifier using only those three bits cannot distinguish these six cases through weights or cutoffs. This is not an impossibility claim about richer storage evidence or the full multi-agent system. Negative means a non-reentrancy exploit root cause, not benign behavior. Counts, input hashes, annotations, missing one-of-ten TRAIN observation and no-tuning scope: ../cohort_rebuild_v2/REAL_TRAIN_STRUCTURAL_COLLISION.json.

Annotation wording clarification: independent support means two independent security publishers. Codex authored the public-source-consensus annotations; independent human review is not claimed. The original logged diagnostic bytes remain unchanged; REAL_TRAIN_FAILURE_ANALYSIS_REVIEW.json (under reports/cohort_rebuild_v2) records this clarification and the real-evidence review.

## Current TRAIN model completion checkpoint (2026-10-16)

Claim22 remains UNVERIFIABLE. Batch20261016T050541-198e808b had7 HTTP200 responses but0 complete cases; malformed additional-info identifiers were rejected. The subsequent production input fix separates incoming owner/functions from actual direct child calls and retains strict validation. Batch20261016T053800-c8aba919 had3 HTTP200 responses, then request4 exceeded the300s total transport deadline;0 complete cases. It never reached the changed prompt. No model-assisted localization number replaces the paper claim. Both terminal batches and their source snapshots/receipts are bound in reports/cohort_rebuild_v2/provider_pilot/STANDING_BATCH_20261016T050541_STATUS.json and STANDING_BATCH_20261016T053800_STATUS.json. Latest authoritative cumulative conservative estimate:$1.973901 of$10; billing unconfirmed. Held-out exam remains unconsumed. No paper edits.

## Cohort admission checkpoint (2026-10-16)

Claim3 remains UNVERIFIABLE: the live provenance-complete manifest contains14 admitted unique transactions across6chains, leaving232 rows to the246 target. Three source-reviewed Arbitrum candidates remain quarantined: a seven-request single-object probe confirmed chain ID42161 but returned null transactions and receipts for every exact hash, as earlier batch requests did. This rules out request representation as a supported explanation for these observations; it does not prove nonexistence or failure of all providers. Exact missing evidence and bindings: reports/cohort_rebuild_v2/ARBITRUM_SINGLE_OBJECT_FINDING.json. Incremental conservative estimate:$0.000042; cumulative:$1.973943, billing unconfirmed. Frozen split unchanged; no model request or held-out observation.

Claim4 annotation-standard clarification: the explicit user-approved method is Codex-authored adjudication backed by agreement between two independent security publishers, not nonexistent independent human reviewers/signatures. A fresh assembled cached-evidence admission recheck of1108 candidates finds17 recorded source-consensus-complete rows and14 fully admitted rows, matching the manifest. The three other source-reviewed rows lack matching RPC transaction/receipt evidence. Full intended-cohort coverage remains UNVERIFIABLE. Evidence: reports/cohort_rebuild_v2/ADJUDICATION_STANDARD_RECONCILIATION.json. No network/model calls, fixture-based claim evidence, split changes or held-out evaluation.

New source-only progress: SwapX BSC hash3ee23c...00160 now has Codex-authored agreement records from BlockSec and PeckShield on unauthorized use of approved ERC20 tokens. Both artifacts link the same exact transaction. DASP Access Control is mapped; SWC stays unmapped. The one-request RPC probe failed during chain identification before transaction/receipt fetch; no cause is guessed. This candidate is quarantined, not added to the14 admitted rows or evaluation split. reports/cohort_rebuild_v2/SWAPX_SOURCE_ADJUDICATION.json binds both sources, annotation, row and RPC outcome. Latest cumulative conservative estimate:$1.973949; billing unconfirmed.

## Additional provenance-complete exploit (2026-10-16)

XCarnival eth:abfcfaf...90294d now passes the actual admission gate with two independent publisher mechanism accounts, documented exact exploit-stage identity, source-consensus annotation, and live matching successful transaction/receipt. This gives15 provenance-complete unique identities available:14 in the existing frozen study plus1 accepted unassigned addition. It is not included in TRAIN or held-out evaluation. A versioned expansion must be preregistered without moving trained rows into held-out or opening the existing seal. Source-linked deployed function/line targets remain unavailable. Level e1f257...27165 is source-annotated but not RPC-verified, so remains quarantined; sibling/setup transfers are explicitly excluded. Evidence: reports/cohort_rebuild_v2/LEVEL_XCARNIVAL_ADJUDICATION.json. Three new metered RPC requests; cumulative conservative estimate:$1.973967, billing unconfirmed. No model calls or paper-metric claims.

## NomadBridge and TeamFinance admission checkpoint (2026-10-16)

Real two-publisher source-consensus adjudication and matching successful Ethereum transaction/receipt checks admit the exact NomadBridge100WBTC exploit payout and TeamFinance unauthorized migration execution. Provenance-complete available identities now total17:14 in the original frozen study plus3 accepted unassigned additions. No new row enters TRAIN or held-out; no split/threshold/paper change. Deployed-source localization targets stay unavailable where not recovered. Exact exclusions distinguish Nomad initialization/deposit and TeamFinance setup transactions. Cached source links correct an Orion hash from legacy Ethereum to BSC; it remains unadmitted without BSC RPC. Two extracted Sushi hashes are proven prefixes of longer encoded route calldata, not transaction references. Evidence: reports/cohort_rebuild_v2/NOMAD_TEAMFINANCE_ADMISSIONS.json and its bound additional candidate manifest. Five new metered RPC reads; cumulative conservative estimate:$1.973997, billing unconfirmed. No model requests or measured performance gains.

## Successful official BSC fallback (2026-10-16)

SwapX, Level and the corrected BSC Orion hash now pass full source/RPC admission using the previously successful official-public-BSC endpoint. Seven metered reads confirmed chain ID56 and all three matching successful transaction/receipt pairs. Earlier failed dRPC probes and quarantined records remain preserved. Provenance-complete available identities total20:14 in the unchanged frozen study plus6 accepted unassigned additions. The Orion BSC record is not the already admitted Ethereum Orion transaction. No new row is assigned to TRAIN or held-out and no new model result is inferred. Evidence: reports/cohort_rebuild_v2/BSC_FALLBACK_ADMISSIONS.json and its bound versioned additional manifest. Conservative incremental estimate:$0.000042; cumulative:$1.974039; public-provider billing unconfirmed. Paper unchanged.

## Preregistered20-row version (2026-10-16)

The20 provenance-complete rows are now published in benchmark/versions/cohort_v3_20261016 with CSV, bound GT, manifest and14TRAIN/6heldout partitions. All original10TRAIN and4heldout assignments remain unchanged; the old cohort files stay byte-identical. Orion BSC is grouped with the original heldout Orion Ethereum incident. New assignments depend only on pinned memberships, source-supported incident alias, seed1729, chain and complexity class. No vulnerability labels, quality scores or paper targets control allocation. The parent heldout partition payload was never opened; no evaluation or new model/RPC call occurred. Exact preregistration and publication evidence: reports/cohort_rebuild_v3/protocol.json, publication.json and membership_proof.json. Local TRAIN commands require explicit --split-file benchmark/versions/cohort_v3_20261016/eval_split.json to select this version. Claim3 remains UNVERIFIABLE for246rows/10chains: actual count20 across6chains.

## Actual v3 TRAIN baseline (2026-10-16)

The preregistered20-row version has14TRAIN identities. Real cached-input component and production Stage1 runs observe9/14:structural TP5 FP1 FN0 TN3,precision0.8333333333,recall1,F1=0.9090909091; repeated-address F1=0.7142857143. Full-storage F1=1.0 is limited to5 available cases (2positive,3negative), not the full TRAIN set. All five missing captures remain explicit. No overall-system F1, paper CI, billed savings or model-assisted localization number is inferred. Exact commands and hash-bound outputs: reports/cohort_rebuild_v3/BASELINE_REAL_TRAIN.json. Zero new RPC/model calls or spend; held-out sealed, final exam unconsumed, weights/thresholds unchanged. Claim13 remains UNVERIFIABLE for its full paper scope.
