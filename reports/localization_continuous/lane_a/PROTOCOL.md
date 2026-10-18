# Lane A protocol (frozen before outcomes)

Offline original110 only; use address_ranking_phase1 grouped5fold seed20261018 unchanged. Labels, incident and URL metadata serve evaluation/grouping only. No source lookup or additional manifests. Saved manifest predictions and 1200-character cast output tails are the sole feature evidence. Source/raw files are not candidate inputs.

Candidate extractor consumes only whitelisted prediction fields and trace text. Preserve distinct production address prefix; append parsed trace call addresses and delegate proxy addresses, then valid 20-byte references found in trace arguments/events. Reference-only candidates are unverified contracts and reported separately. Never derive candidates from labels, filenames, incident names, URLs or transaction hashes. Exclude zero address.

Predeclared variants: call_append; reference_append; train_fold_grid. Grid uses baseline reciprocal score plus normalized trace call frequency, delegate support and reference evidence, with coefficients (0,0.25,0.5,1). Select lexicographic training R1/R3/R5 only; fixed iteration ties. Evaluate once per fixed held-out fold. OOF outcomes exploratory; report110 and109 transaction reweighting, coverage, and candidate growth. Promotion requires nonnegative delta at all three cutoffs and at least one positive on both populations. No production changes.

Audit feature purity by poisoned unknown metadata, held-out-label independence of fitted configuration, offline guard and unchanged inputs. Pin hashes and fold membership. Test trace extraction including truncated tail/delegate handling. If no gain, retain honest negative result and evidence limits.
