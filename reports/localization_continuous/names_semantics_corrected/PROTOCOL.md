# Corrected lexical identifier protocol

Preregistered after independent review identified bare eight-hex-character
selectors in the B2 tokenizer. Preserve all original results as lexical-mixture
exploratory results. Original nested protocol is paused before execution.

Repeat the same nine fixed C/lexical-scale configurations, same baseline
candidates, numeric features, folds, row weights, TF-IDF fitting, poisoning
checks, and scoring as B2. Only change: exclude identifier fullmatches of
[0-9a-fA-F]{8} before word splitting. No adaptive changes from old outer outcomes.
Report every corrected OOF variant and unique109 metrics, with old input/output
artifacts untouched. Names that happen to be exact eight-character hex words
are conservatively excluded too. Explicit 0x labels remain excluded.
