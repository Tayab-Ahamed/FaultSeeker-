# Independent C10 hybrid review

Reviewed address_append_hybrid_lane_c.py, PROTOCOL10.md, saved hybrid result and
source B4 result. All110 hybrid rankings preserve the full B4 prefix, contain
distinct addresses, and bind the source result by matching SHA256. Independent
original110 scoring reproduced62/73/82 exactly; reported unique10961/72/81.

No target values or labels enter append construction: it extracts A candidates
from saved whitelisted predictions and saved trace text, then appends addresses
absent from the existing OOF ranking. Targets score the constructed output only.
No fitting occurs in the append adapter. Existing B4 folds are asserted equal
to phase1 folds. No blocking label leakage found in this transformation.

The62 top1 is inherited from the selected fixed B4 variant, not new model gain.
B4 variant selection was exploratory; its nested selector reaches59 instead.
Thus hybrid62/73/82 is exploratory and cannot inherit nested validation merely
because its source rankings were individually OOF. Reference additions remain
unverified address mentions. Fresh raw-selector/decoded-name incompatibility
remains unresolved. Review did not modify C files or run new experiments.
