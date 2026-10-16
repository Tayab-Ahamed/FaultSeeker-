# Train-only research checkpoint

Three genuine component invocations are recorded in experiments_log.json. Latest:
`20261015T143221-eb779fdb`. Reproduce with `python scripts/run_authentic_research.py`.
Each run preserves config, seed, system hashes, raw predictions, explicit coverage
and exact compressed source bytes. No threshold, weight, frozen membership or
held-out outcome has been used for tuning.

Frozen train: ten source-adjudicated exploits; call coverage seven; opcode coverage
two. Missing observations stay missing. Structural: TP=3 FP=1 FN=0 TN=3,
precision 0.75, recall 1.0, F1 0.8571428571428571. Repeated-address: TP=3 FP=4
FN=0 TN=0, precision 0.42857142857142855, recall 1.0, F1 0.6.

Full storage detector on Rubic and Euler only: TP=0 FP=1 FN=0 TN=1,
precision 0.0, recall undefined (no positives), F1 0.0. This is not an estimate of
reentrancy sensitivity, not the paper Table V cohort and not overall system F1.
The full-positive coverage gap is being addressed through Revest canonical-prefix
replay. The held-out file has not been loaded and no exam permit is consumed.

Failure analysis: structural-only Beanstalk recursion is not its adjudicated
root cause. Full-detector Euler falsely marks sequential DAI calls at different
depths as nested slot rewrites. All four implicated slot groups have zero actual
ancestor/descendant write-frame pairs. Fixing that semantics is the next train
iteration; it does not require changing paper weights or classification thresholds.

New replay request counts, source hashes and honest capability limitations are in
RPC_TRAIN_CONCLUSION.json. Overall system F1, paired billed inference savings,
source-linked localization and Table VI remain unmeasured. No component statistic
substitutes for them. Claim 13 remains UNVERIFIABLE at the paper's full scope.

## Fourth run: canonical-frame semantic repair

Run `20261015T144524-c6d2fefd` used the same two full-detector train cases.
Euler no longer fires the nested rewrite signal: FP=0 TN=2, accuracy=1.0;
precision, recall and F1 are undefined because no scored row is reentrant.
Structural and repeated-address outcomes did not change. The paired raw evidence
and limitations are in REENTRANCY_ANCESTRY_FIX.json.

Revest first replay was rejected after receipt validation because London mixHash
setup had been skipped. A real local London probe verified the installed setter.
The runner now sets the canonical mixHash before mining for London too, retaining
the equality check. The retry remains an acquisition attempt until every check passes.

## Fifth run: genuine positive capture

Revest passed the complete five-transaction canonical-prefix replay after London
mixHash setup was corrected: 326 SLOADs and 113 SSTOREs, 241 outbound requests.
No difficulty/randao opcode was executed in this target trace.

Run `20261015T145100-560abff3`: full-detector TP=1 FP=0 FN=0 TN=2,
precision=recall=F1=1.0 on three of ten training identities. The new regression
revalidates the saved positive and confirms the ancestry fix preserves its actual
nested-slot signal. This small incomplete-case result does not meet the full
population experiment requirement and does not promote claim 13. Structural and
repeated-address results remain unchanged on their seven call traces.

REENTRANCY_POSITIVE_TRAIN.json pins the actual run, positive capture and request
record. Held-out data and the final exam remain unused. Cumulative recorded
spend estimate/allocation is $1.820964, not a confirmed invoice.

## Sixth component run and real production Stage 1

Run `20261015T150659-1141df8b` adds the accepted Inverse Finance opcode
capture: 628 SLOADs, 162 SSTOREs, exact signed transaction/receipt/environment
checks, 13 upstream requests and 362 exact-parent prestate cache hits.
Full component: TP=1 FP=0 FN=0 TN=3, F1=1.0 on only four of ten train
identities. There is only one scored positive. This is incomplete-case train
performance, not full-system F1 or paper metric verification.

Production run `20261015T150951-4a3803b0` executes the actual Stage 1
orchestrator and FunctionRanker on seven of ten train identities with socket
connections prohibited. All seven rule verdicts are EXPLOIT; the exploit-only
population does not establish general exploit precision. Reentrancy component
F1 is 0.8571428571428571. Stage 2/3, localization ground-truth scoring, paired
billed inference savings and Table VI remain unmeasured.

A diagnostic Beanstalk retry used 239 upstream requests and was rejected: the
first thirteen canonical prefix transactions mined, while the target stayed
pending. The hash-bound pool, nonce and block observations are retained under
`opcodes/failures/`; rejection is not an accepted opcode capture. Cumulative
recorded spend estimate/allocation after this attempt is $1.823988. This is not
a confirmed invoice. Held-out outcomes and the one-time final exam remain unused.

## Seventh component run, broader production coverage and source-linked ranking

Actual public-provider captures add Grim Finance (248 Fantom frames) and Hundred
Finance (519 Gnosis frames). Run `20261015T161923-4650ee37` scores nine of ten
train call traces: structural TP5 FP1 FN0 TN3, F1=0.9090909090909091;
repeated TP5 FP4 FN0 TN0, F1=0.7142857142857143. Full opcodes remain four
train cases, TP1 FP0 FN0 TN3. No threshold or weight changed.

Production run `20261015T162935-701ee97b` executes real Stage1 and FunctionRanker
on nine train identities, no network dispatch. Its explicit count-ranked function
serialization preserves the existing stable encounter-order tie policy. On two
source-supported function-identity cases, Euler ranks33 and Revest ranks24;
top1=0, top5=0, MRR=0.03598484848484848. The failure is count priority: often
called helper functions precede the source-supported root-cause function. These
are actual deterministic baseline results, not multi-agent localization or
held-out numbers. Source names, labels and targets never entered prediction.

## Preregistered distinct EOA control study

32 actual Ethereum transfers admitted from eight fixed preregistered blocks,
with 32 distinct hashes, senders and destinations. 302 candidates were inspected;
receipts and explicit hash-tagged parent/inclusion code observations support
each admission. 201 upstream logical RPC requests cost an estimated $0.001206;
cumulative recorded estimate/allocation is $1.825284, not a confirmed invoice.

Production run `20261015T163542-28c7cef6` scored actual Stage1 observations on
30 authenticated call traces; two transport failures remain missing. All thirty
are UNCERTAIN: observed BENIGN-skip eligibility is 0/30. Context/token/storage
coverage is incomplete; no coverage flag was invented to force a BENIGN skip.
EOA execution controls do not establish general legitimate-contract error rates
or the paper's 40-percent paired latency claim. No held-out exam was dispatched.


### Approved cloud pilot stopped and diagnosed

Six HTTP-200 Agnes 2.5 Flash requests completed with per-call spend receipts, but no case completed. Model response 6 contains valid Markdown-fenced JSON; the gateway adapter omitted the existing safe parser. A test-first offline regression reproduces and fixes that omission without another live call. The pilot remains UNSCORED; the consumed dispatch permit is preserved. Batch conservative estimate $0.0229949; cumulative at batch end $1.8482789 (not an invoice). Held-out remains sealed. See provider_pilot/STOPPED_BATCH_DIAGNOSIS.json and the hash-bound run summary.


### Native Gnosis opcodes integrated into TRAIN

The Hundred Finance Gnosis historical node capture is separately validated from Anvil prefix replay. Actual receipt identity, gas, 519 frames and all 1354 SLOAD / 186 SSTORE owners agree. Four metered attempts (one sandbox connection failure, then three successful RPC methods) cost a conservative $0.000024. Eighth TRAIN component run 20261015T180152-ca8176ca covers five full-opcode cases: TP2 FP0 FN0 TN3, F1 1.0; this is a small availability-selected component population, never overall or held-out performance. Structural nine-case F1 remains 0.90909.


### Two bounded cloud batches terminal

The first six and follow-up fourteen calls total exactly twenty, all HTTP 200 with agnes-2.5-flash and genuine usage-backed ledger settlements. First batch stopped on parser error; follow-up demonstrates the parser fix on real fenced responses and stops at its cap. Zero complete cases means localization and confidence quality remain unscored. Combined conservative model cost $0.1008808; cumulative ledger at completion $1.9261888 / $10, billing unconfirmed. The second batch consumed 1126.531 seconds of transport time, including one 198.515-second response: the configured socket timeout does not enforce a total wall-clock deadline. Five real roles fired; children filtering and final ranks were not reached. No pilot authorization remains and held-out stays sealed. See provider_pilot/COMBINED_PILOT_REPORT.json.


### Offline source/selection boundary corrections

A source cache miss previously constructed the live downloader directly, bypassing the injected verified-source factory. All fallback lookups now use that factory, explicit misses are cached for the transaction, and provenance errors propagate. Model narrowing now rejects malformed/empty/unknown/duplicate selections, offers only the current subset on later passes, and uses correct function-name keys for created-contract candidates. Subagent review and test-first regressions cover both selection branches and actual cached Revest source with live download construction prohibited. Earlier pilot snapshots retain the old bypass; whether it executed cannot be established from their transport records. They remain unscored. No new model/RPC requests or spend; held-out untouched. See SOURCE_SELECTION_BOUNDARY_REVIEW.json.


### Alternate BSC probe and safe HTTP diagnostics

One PublicNode BSC eth_chainId attempt failed before identity verification. No trace or receipt request followed, and no retry was made; this does not prove tracing unsupported. Legacy failure records contain only RuntimeError, so the original HTTP status cannot be recovered. The shared meter now preserves only a validated numeric status in a RuntimeError-compatible typed error, and future probe records can retain that number without credential-bearing URLs/headers/bodies. Twenty-one focused offline tests cover the new diagnostics and bounded probe. One metered RPC attempt adds a conservative $0.000006; cumulative ledger $1.9261948 / $10, billing unconfirmed. No new inference calls; held-out untouched. See BSC_HTTP_DIAGNOSTICS_REVIEW.json. Local Ollama metadata was separately checked without inference and connection was refused (10061).

## Exact saved-observation prefix replay (claim 30)

Two offline diagnostic runs under gateway_prefix_replay each matched five of 14 saved HTTP request/response observations, then stopped before returning response six (REQUEST_BYTES_DIVERGED). Current and historical source snapshots are bound separately. The second run uses the standard $10 cap in its isolated temporary accounting ledger; the first preserves an earlier diagnostic cap. Neither run dispatched inference/RPC, attempted network access, consumed a permit, changed the real ledger, used held-out inputs, or produced quality metrics. Production wall-time budgets are not reproduced. These are debug runs, not train optimization iterations; claim 30 remains UNVERIFIABLE.

## Additional-info identity and pilot domain-error boundary (claim 22)

Fixed character-indexed model references, inconsistent child pair ordering and silent substitution of a requested source owner. Whole model requests now validate before any call/source lookup. Cloud/local prompts use explicit full-address/function objects. An optional error policy records sanitized failure metadata; the pilot terminates on domain errors before another reservation or dispatch. Tests include the actual malformed fifth historical response and the real analysis recovery loop. Focused validation: 74 passed. A new strict offline replay matches four saved observations then stops at the changed fifth prompt; zero new network requests, unchanged real ledger, no held-out access and no quality score. The 20-call allowance remains exhausted; claim 22 remains UNVERIFIABLE pending complete genuine model-assisted outputs.

## Repeated-pattern evidence preservation (claim 22)

The count ranker previously deduplicated every eligible repeated pattern under an empty key and returned shared mutable input records. Exact full-evidence duplicates alone are now removed; distinct owners/order/depth/repeat counts survive and retained records are deep copied. A real recorded production TRAIN run (20261015T192119-77fe3b52) covers nine of ten cases with no network. Reentrancy component F1 remains 0.9090909. The two source-linked deterministic localization ranks remain 33/24, top1=0, top5=0, MRR=0.03598484848484848; no gain is claimed. BSC remains unavailable, models were not executed and held-out stays sealed.

## Executed storage source spans reach production prompts (claim 22)

The verified-source adapter now maps bound historical storage-operation PCs through the compiler map with PUSH-aware instruction indexes, UTF8 byte ranges and validated immutable/link patches. Delegated executing code is separate from storage ownership; entry selectors group observations without asserting AST function ownership. Actual processing prompts receive mapped spans and the capture binding. Exact source paths, slots, reverted status and every occurrence are retained. Three offline input-evidence exports preserve source snapshots for successive integration revisions; these are not optimization/quality iterations. Latest export: execution_source_spans/20261016T001414-e8718971/summary.json. Euler maps 232/543 operations (311 missing runtime-source); Revest maps 227/439 (212 missing). Eight/eighteen code-address ABI-selector pairs carry spans. Focused tests: 41 passed. No new network or inference requests, unchanged cumulative conservative ledger $1.9261948, held-out untouched. No localization gain claimed; claim 22 remains UNVERIFIABLE.

## BSC live structured HTTP diagnostic (claim 25)

A new bounded PublicNode probe on 2026-10-16 stopped at eth_chainId with HTTP 403 after one metered request; no trace or receipt dispatch followed. Old artifacts are preserved unchanged. Chain identity and archive/tracer support remain unknown; no acquisition/index admission is made. Request estimate $0.000006; cumulative conservative ledger $1.9262008, billing unconfirmed. Evidence: bsc_trace_publicnode_http_diagnostic/20261016T013315/decision.json. Claim 25 remains UNVERIFIABLE, held-out untouched.

## Abort completion-state and proposed bounded follow-up (claim 22)

Both analysis-loop paths now record TimeoutError on detected time-budget expiry or two empty tasks, so aborted work cannot report analysis_complete=True. Existing loop time/iteration/adequacy policies remain; this does not establish a hard socket wall-time deadline. Test-first: 10 failed/6 passed before timeout fix; 47 focused tests pass after fixes including a shared-ledger incremental-cap check. A further at-most-20 TRAIN request proposal with a $0.20 incremental conservative estimate ceiling is prepared under provider_pilot/next_20; approved=False and no dispatch permit exists. The original twenty-call allowance remains consumed. Current-code offline replay matches one saved request then diverges before returning response two; it made zero network/inference calls and left the real ledger unchanged. Claim 22 remains UNVERIFIABLE; held-out sealed.

## Observed finding identities and operative model ranking (claim 22)

Whole model findings now validate against the actual execution memo; unsupported identities, malformed evidence and invalid confidence fail before mutation, zero confidence remains zero and depth comes only from observed calls. Finalization consumes a validated full model ordering and preserves shallower candidates for actual Stage3 scoring. This removes an unused-ranking/deepest-only path without changing Eq4 weights or thresholds. Focused tests: 79 passed, including actual analysis-loop rejection and real Stage3 handoff. Existing non-original test fixtures were updated to valid ranking/memo schemas; original-test integrity check reports no unauthorized source changes. New strict replay matches one saved request then stops before response two; both reviewed proposal payload previews match current request bytes. No model/network calls or new accuracy metric. Proposal remains unapproved; claim 22 stays UNVERIFIABLE.
