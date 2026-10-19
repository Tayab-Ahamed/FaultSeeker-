# Reviewed OOF checkpoint

Original110,109 unique, fixed five grouped folds. All exploratory; model development and selection use this population. No fresh result is claimed.

| Method | R@1 | R@3 | R@5 |
|---|---|---|---|
| Frozen distinct-address baseline | 55/110 (50.00%; [40.82, 59.18]) | 68/110 (61.82%; [52.49, 70.35]) | 76/110 (69.09%; [59.93, 76.96]) |
| A reference append | 55/110 (50.00%; [40.82, 59.18]) | 70/110 (63.64%; [54.33, 72.02]) | 79/110 (71.82%; [62.79, 79.38]) |
| B corrected unigram | 58/110 (52.73%; [43.46, 61.81]) | 70/110 (63.64%; [54.33, 72.02]) | 77/110 (70.00%; [60.88, 77.77]) |
| B fixed bigram | 62/110 (56.36%; [47.04, 65.26]) | 71/110 (64.55%; [55.25, 72.86]) | 79/110 (71.82%; [62.79, 79.38]) |
| B nested selection | 59/110 (53.64%; [44.35, 62.67]) | 72/110 (65.45%; [56.18, 73.68]) | 79/110 (71.82%; [62.79, 79.38]) |
| A+B hybrid | 62/110 (56.36%; [47.04, 65.26]) | 73/110 (66.36%; [57.11, 74.51]) | 82/110 (74.55%; [65.67, 81.76]) |

First milestone61hits reached by fixed B4/hybrid;66hits not reached. Nested selector is59hits, so fixed winner gains are not independent model-selection validation. Nominal Wilson intervals do not account for connected groups, repeated model selection or duplicate transaction weighting.

A improves coverage84to87; only candidate identities observed in saved trace text were added. Some references are event arguments, not independently verified deployed contracts. B verified ABI/storage lane has no admissible cache and contributes no measured signal. The safe generic registry decoder preserves literal selectors and hashes recorded responses; no new external responses have been acquired. Training cast names and future generic names may differ; deployment parity remains a limitation to resolve before fresh scoring.

Requests this continuous run0RPC/0provider/0registry; rate hits0; new paid spend$0. BatchE not built/scored. Papers, README and main unchanged.
