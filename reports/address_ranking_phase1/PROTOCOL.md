# Phase 1 address ranking — offline development protocol

Frozen before executing these variants. No Batch C/D files may be read, listed,
hashed, scored or used for model/variant selection. No new batch, RPC, model API,
install, paper edit, commit or push. This protocol and evaluator concern only
the frozen original manifest's 110 successful records (109 unique hashes).

Primary endpoint: first correct explicitly labeled contract address among the
top1/3/5 **distinct addresses**. Each address occupies exactly one slot. Labels
are all explicit valid addresses in each row-bound original location map; no
signature guessing, selector enrichment or externally inferred targets.
Baseline: current production rerank_saved_predictions, then deduplicate addresses
in their first-occurrence order. Also report its undeduplicated function-slot
address hits as a separate reference, never as the equal-budget baseline.

Three variants, fixed before observing their OOF outcomes:

1. reciprocal_sum: sum of reciprocal production function ranks per address.
   Parameter-free, stable baseline order resolves exact ties.
2. structural_grid: linear combinations of evidence-only address summaries.
   Configurations are all 27 combinations alpha,beta,gamma in {0,.5,1}:
   score = (1-alpha)*best_reciprocal + alpha*normalized_reciprocal_sum
           + beta*structural - gamma*normalized_terminal_fanout.
   structural is the arithmetic mean of within-row normalized log(1+callcount),
   maximum call-path length, and log(1+call-path concentration).
   Fanout counts distinct caller-path/terminal-position observations; concentration
   is summed function-call count divided by distinct caller paths (minimum1).
3. delegate_context_grid: same 27 configurations, with delta in {0,.5,1}
   adding delta*max(normalized_reciprocal_sum of observed delegate neighbors).
   Proxy/implementation edges come only from explicit saved cast delegatecalls
   with an observed parent, and only when both addresses already belong to the
   common candidate pool. This shares evidence, not target identity or credit;
   no aliases are automatically scored as correct and no addresses are added.

All within-row normalizations depend only on that row's candidate evidence.
No ground-truth address value, incident name, URL, correctness flag, saved score,
or target frequency is a ranking feature. Standardizers are not fitted globally.

Five outer folds, deterministic seed20261018. Connected components union repeated
transaction IDs, incident names, every individual disclosure/source URL, and
every target contract address, transitively. Grouping uses labels only to prevent
overlap, never to score candidates. Balance components by descending size, with
SHA256(seed:group-id) tie ordering. No group or duplicate may cross a fold.

The finite configuration grid is selected separately using only each outer
training partition's labels: lexicographic training hits@1, then@3, then@5;
earliest enumerated configuration wins an exact tie. No outer validation result
selects that fold's configuration. Parameter-free reciprocal_sum has no fitting.
Report raw per-row OOF ranks, fold membership/configurations, candidate coverage,
input/source hashes, baseline and each variant's Wilson95% intervals.

Pick at most one variant: no lower pooled OOF hits at any of1/3/5, at least one
strict improvement over distinct-address baseline; the same condition must hold
after deweighting the one duplicate from those same OOF predictions. This is a
109-unique sensitivity, not an independently refitted109-row CV. If several
qualify, prefer lexicographic OOF hits@1/@3/@5, then fewer configurations, then
variant name. If none qualifies, stop with no selection. No production routing
or CLI behavior is changed in this phase, even if a variant is provisionally
selected. No deployment fit or fresh evaluation is performed.

Leakage checks: zero crossfold hashes/incident names/individual URLs/target
addresses; label changes do not affect feature extraction; validation-label
changes cannot affect training selection; explicit input allowlist permits only
the original manifest, its110 row-bound original GT files and original
classification CSV. Content hashes before/after verify those inputs unchanged.
Tests may use fixtures for software behavior, never research evidence.

All outcomes remain exploratory development evidence: upstream ranker rules and
feature design were previously informed by this development population, and
selection across these three OOF results adds model-selection uncertainty.
Wilson intervals are nominal record-level binomial intervals and do not correct
for duplicated records, connected incidents or model-selection uncertainty.
