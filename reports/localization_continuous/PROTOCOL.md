# Continuous localization protocol

Development population: original110 records only,109 unique transactions. Fixed incident/chain-contract/source-URL/duplicate connected groups and five folds from address_ranking_phase1; baseline implementation is unchanged from e6f8da0271f00223346a74ffcf32bb34b54383dd.

All development access excludes reports/new_batches. Only the explicitly requested historical aggregate report was inspected before development; no spent B/C/D per-row outcomes may guide changes. Original labels may define groups and training objectives, never inference features. Cache admission requires runtime or independently sourced provenance, not target-conditioned source lookup. Report only OOF outcomes; repeated development and selection remain exploratory. Nominal record-level Wilson intervals do not account for dependence/model selection.

Three isolated branches: localization-coverage, localization-selector, localization-learned. Each records its feature protocol, software tests, input hashes and experimental results. No dependency installs. Commit only task-owned files, never pre-existing unrelated changes.

Merge gate: admit only leak-reviewed variants with some OOF recall gain and no R@1/3/5 regression versus the equal-budget baseline, on110 records and109 unique reweighting. Candidate coverage alone is not a ranking gain; coverage features may be evaluated by a fold-trained learner before selection. Combined OOF must be measured, not inferred by adding lane gains. Reweighting is not a109-row refit.

Primary endpoint: distinct-address R@1, then R@3/5. Function/selector endpoints must state label availability; never relabel address hits as function hits. Dev thresholds: at least61/110 and then66/110 top-one hits. Real improvement can fall short; do not manufacture it.

Only after merge review may Batch E be assembled. Its at-least40 fresh Ethereum incidents must be disjoint by incident/contract from original development and all earlier batches, labeled before ranking, with source evidence pinned. Prior identity metadata may be used only for exclusion; never prior predictions/outcomes. Freeze cohort hash, final committed ranker/configuration before collection/scoring. Produce all predictions without labels then score once with an exclusive lock. No reuse of E after observation.

Free-tier requests only, no key persistence/printing, throttle, bounded exponential backoff on429, stop immediately on billing/paid-plan/free-quota exhaustion. Log every dispatch and limit hit. If data, quota, execution or usage prevents completion, preserve work and report the exact limitation; no claimed fresh metrics without a completed frozen run.
