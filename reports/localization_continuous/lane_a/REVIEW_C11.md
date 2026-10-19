# C11 independent review

All six frozen results11 variants independently recomputed from saved OOF rankings against original110 labels, including unique109. All counts, recorded hashes,110 fixed fold assignments and training/test membership audits match. No scoring/model refit occurred.

| Variant |110 hits|109 hits|
|---|---|---|
| logistic1 |57/71/80|56/70/79|
| logistic10 |60/72/80|59/71/79|
| logistic100 |56/73/82|56/72/81|
| listwise.001 |60/69/80|59/68/79|
| listwise.01 |60/71/78|59/70/77|
| listwise.1 |58/70/77|57/69/76|

All rankings contain unique addresses and exactly the A-expanded candidate set. Appended reference-only suffix retains A encounter order and never precedes a trained candidate. Precise prefix qualification: C11's A preparation excludes zero address, leaving676 baseline candidates rather than677. Row109 contains the single removed zero. The other109 records preserve their full baseline candidate prefix. This filter was predeclared in A and is label independent. Zero appears in no original110 target set. Dropping zero alone from baseline saved order leaves55/68/76 unchanged. Do not call C11 an exact677-candidate baseline model; B4 retains the original677 candidates and is distinct. Earlier B4/C8 review's C8 expanded-set claim remains correct.

The results11 coverage field84 describes pre-append training coverage; final saved expanded rankings cover87. Report both meanings explicitly rather than interpreting84 as final coverage.

Reviewed transforms: mean-centering and leader-gap numeric features use only candidates from the same row, with no labels. The fitted numeric scaler, TFIDF vocabulary/IDF and optimization batches use only training indices. Corrected lexical tokenizer excludes8hex identifiers. SublinearTF and unigram+bigram representation are fixed in protocol11. The six outer-result configurations remain exploratory; winner selection has no independent confirmation. Relative-feature computation is row-local, not a fitted cross-row transform. No feature-isolation blocker found.

Best top1-first C11 result60/72/80 passes baseline no-regression on110 and109 but remains below B4's62 top1. C11 cannot be preferred over B4 for a top1-first gate based on these results. No frozen result, candidate set or fold was changed during review.
