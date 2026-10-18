# B4 fixed lexical representation diagnostic

Registered after corrected B2, before this run. Original110 baseline candidates
only, same phase1 folds and corrected no-eight-hex tokenizer. Fixed18 configs:
TF-IDF representation unigram, word unigram+bigram, or char_wb3-5 on the same
admitted word documents; C in1,10,100; lexical multiplier1,3. All vocabulary,
IDF, numeric scaling and classifiers fit inside training folds. Numeric features
unchanged. Row weights additionally divided by connected-group size; this is a
joint representation/regularization/group-weight diagnostic, not an isolated
attribution. No lexicon of target names or manually selected function words.

Report every outer OOF result, unique109 metrics and poisoning checks. Top1
target61 is desired, not permission for post-hoc exception rules. Selection
among18 outer results remains exploratory. No network/cache/batch access.
