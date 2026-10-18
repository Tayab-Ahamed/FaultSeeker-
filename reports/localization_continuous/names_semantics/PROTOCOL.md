# B2 lexical function semantics preregistration

Original110 offline only, baseline distinct addresses and exact phase1 grouped
fivefold split. Target top1 >=61 is a desired outcome, never a stopping rule for
adaptive search. No new caches, selectors, storage slots, addresses, or batches.

Documents per baseline candidate concatenate function identifiers from saved
prediction function/function_name fields and actual parsed saved trace calls at
that address. Only a leading Solidity-style identifier is admitted; strip ABI
arguments, split camelCase/underscores, reject hex labels, remove numeric tokens.
Do not consume GT function names, tx/contract identifiers, incident/URL/filename,
publisher information, or other prediction fields. Identifier words can correlate
with projects; grouped target-address/incident evaluation mitigates but cannot
eliminate unrecognized semantic identity correlations. This is lexical evidence,
not verified ABI or selector matching.

Fixed nine pointwise logistic configurations: C in (0.1,1,10) crossed with lexical
TF-IDF multiplier (0.3,1,3). TF-IDF unigram vocabulary, IDF, and numeric standard
scaler fit only on outer training candidates. Numeric fields: phase1 five
behavioral features and baseline position reciprocal. Weight each training row
equally, dividing its weight across its candidate addresses. Stable original
candidate ordering breaks ties. No class balancing or feature/hyperparameter
selection. Report all nine OOF outcomes and unique109 first-occurrence
reweighting; any best variant is exploratory, not an independent test result.

Validate heldout-label poisoning, no heldout-vocabulary fit, feature whitelist,
and candidate preservation. Persist input/dependency hashes and fold assignments.
No production behavior edits. No invented function names: missing text is empty.
