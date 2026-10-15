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
