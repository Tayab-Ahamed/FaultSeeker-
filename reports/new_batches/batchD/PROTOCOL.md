# Batch D: frozen fresh source-backed localization test

Preregistered before RPC collection, candidate production or any Batch D score.
This is an exploratory development upgrade followed by one independent batch
test. It does not validate the paper's 68–81%, .969 F1, or 58% cost claims.

Population: the ten manually source-validated Ethereum PoCs in
`draft_source_rows.json`, in source-path order. This is a convenience sample,
not an exhaustive or randomly sampled population. Include all ten before
looking up traces; no replacements after freeze. Cached public source bytes,
quotes and signature declarations are SHA-256 pinned. Original acquisition
used upstream main URLs and did not record Git commits. Source-supported
invoked victim functions are the labels; they are not independent root-cause
adjudications. Missing public receipts/traces exclude a row before scoring,
with explicit reasons. An honest smaller verified denominator is allowed.

Exclusions: all original ground-truth/classification transaction identities,
Batch A/B/C identities and incident aliases; prior target addresses; all
Batch C screened sources. Ten selected hashes also have zero matches against
prior transaction-named JSON artifacts under reports/ and data/output/.
No prior score was read to select these rows. No synthetic examples are evidence.

Upgrade selection: reject B (zero incremental OOF gain; target-conditioned ABI
acquisition); reject C (primary top-1 regresses). Integrate only corrected D:
110-record production baseline 40/55/58 versus grouped OOF 40/56/58;
109-unique sensitivity 39/54/57 versus 39/55/57. Both improve @20 by one.
These are exploratory OOF development results, not unseen generalization.
Fixes cover true indentation/proxy parent, connected individual URL/name/address
groups and public-cache-only selector matching. The search grid stays fixed.

Deployment weights were fitted once on original110 development only:
trace_evidence=0, count=0, depth=1, proxy=0, saved_rank=1.
Training hits 41/56/58 are not OOF. No Batch D labels or outputs entered training.
The deployed adapter takes the actual production-ranked candidate list and a
deterministic Foundry-shaped rendering of the observed callTracer identities.
No source target, expected selector or expected address enters prediction.
This fresh batch tests that transfer from saved-cast development to live RPC
evidence; there is no retuning or claim that the input channels are identical.

Working source/configuration/model-cache files are pinned by content SHA-256
in freeze.json, rather than claiming an uncommitted change has a commit hash.
No commits or pushes are authorized. Freeze is exclusive and cannot overwrite
an existing batch. Changes after freeze invalidate collection and scoring.

RPC: configured dRPC free-tier endpoint only; one request per second,
no concurrency, no automatic retries. Record every dispatched request.
Stop the entire run on HTTP402, any billing/payment/upgrade prompt, rate limit,
or unhandled transport/JSON failure. Never upgrade, add payment or change plans.
A stop prohibits scoring and no alternative paid route is used. Paid spend
authorized is $0; a free-tier-zero estimate is not an invoice confirmation.

Verification: Ethereum chainID1; transaction/receipt hash equality with the
frozen identity; nonpending transaction; same block number; nonnull callTracer
tree. Complete response bytes are retained with content hashes. Missing chain
evidence is never replaced by a mock or a compiled example contract.

Prediction completes for all verified rows before any target score is computed.
Primary match: exact vulnerable address + Keccak selector of the frozen typed
signature. Sensitivities: address-only and selector-only. Report hits/N and
Wilson95% intervals at1/3/5. No selector guessing from bare function names.

Scoring has an exclusive batch-global lock and exactly one final score file.
No partial numeric output, sample replacement, threshold/weight change or second
score. A crash before any score is produced is not an empirical scoring attempt;
any recovery fix must be labeled exploratory and requires an explicit recorded
decision rather than silently deleting the lock. Never edit the paper.

Commands, from the main checkout on ranker-upgrades-20261017:

```powershell
python scripts/research/batchD_phase2.py freeze
python scripts/research/batchD_phase2.py collect
python scripts/research/batchD_phase2.py score
```
