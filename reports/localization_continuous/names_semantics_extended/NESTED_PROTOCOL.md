# B5 nested grouped lexical selector

Registered after B4 outcomes, before nested execution. Fixed exact18 B4 configs,
same corrected tokenizer, baseline candidates, numeric features and group weights.
Outer5 phase1 folds unchanged. Within each outer training population, each other
original fold serves as inner validation once (four inner splits); fit on other
three folds. Fit TFIDF/scaling anew per inner split. Select by aggregate inner
top1/top3/top5 hits lexicographically, ties in B4 iteration order. Refit chosen
configuration on all four outer-training folds, score outer holdout once.

Report selected configs and outer OOF110/unique109, plus inner counts marked
selection diagnostics. No outer labels participate in selection. Fixed search
space was informed by prior research outcomes, so nested result remains research
validation rather than a pristine external test. No batches/network/new features.
