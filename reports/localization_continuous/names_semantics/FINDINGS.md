# B2 lexical result and provenance audit

Best of nine fixed exploratory OOF configurations: C10, lexical multiplier3,
58/72/79 hits at ranks1/3/5, versus baseline55/68/76. Unique109 hits57/71/78,
versus54/67/75. Gains are3/4/3. The requested61 top1 target was not reached.
396 of677 candidate documents contain admitted lexical tokens. All nine results
are retained; the best-result selection is exploratory.

Two unit tests pass. Every fold/configuration was refit after poisoning heldout
labels and text: model coefficients and training vocabulary were identical.
Input hashes were checked unchanged. Candidate population is baseline-only.

Audited acquisition chain: run_original_provider_pinned.py calls the forensics
orchestrator with transaction hash and chain, then FunctionRanker.rank, then
scores the resulting predictions against GT. FunctionRanker emits the function
label from call-derived candidate keys. TraceAnalyzer copies trace function
fields; TxnSequencer obtains cast-style replay text and TraceParser._parse_node
extracts the function string directly from call lines. No target-name filter or
selector_cache lookup was found in this inspected chain. GT is used to identify
the benchmark transactions and score them, not to replace function identifiers.

This audit establishes the repository's observed code path, not independent
historical proof of the decoder's upstream registry provenance. Cast-rendered
names may be generic selector decodings and are not verified contract ABI
identities. No verified-source cache was admitted. Unknown incident aliases and
project-correlated function words remain generalization limitations.
