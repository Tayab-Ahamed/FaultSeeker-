# Provider-pinned original-benchmark diagnosis

This is diagnosis only. No detector, ranker, threshold, case selection, or paper file was changed.

## Before and after the labelled retry pass

| View | Before retry Recall@1/3/5 | After retry Recall@1/3/5 |
|---|---:|---:|
| All 115 cases | 0.000000 / 0.000000 / 0.000000 | 0.000000 / 0.000000 / 0.000000 |
| Valid trace subset (95 → 110) | 0.000000 / 0.000000 / 0.000000 | 0.000000 / 0.000000 / 0.000000 |

Primary pass: 95 ok, 20 failed, 12 replay mismatches. Retry pass: 20 attempted, 15 recovered, 5 remained failed.

## Final result views

- All 115 denominator: n_ok=110, n_failed=5, mismatches=14, Recall@1/3/5=0.000000/0.000000/0.000000.
- Valid trace subset: n=110, mismatches included as valid results, Recall@1/3/5=0.000000/0.000000/0.000000.

## Missed-case diagnosis

Categories are mutually exclusive and prioritized: no trace, mismatch, label issue, wrong chain, then ranker miss.

| Cause category | Count | Five examples (or N/A for zero count) |
|---|---:|---|
| No trace | 5 | 0x04e16a79ff928db2fa88619cdd045cdfc7979a61d836c9c9e585b3d6f6d8bc31, 0x1a7ee0a7efc70ed7429edef069a1dd001fbff378748d91f17ab1876dc6d10392, 0x37acd17a80a5f95728459bfea85cb2e1f64b4c75cf4a4c8dcb61964e26860882, 0x7c5a909b45014e35ddb89697f6be38d08eff30e7c3d3d553033a6efc3b444fdd, 0xb072f2e88058c147d8ff643694b43a42e36525b7173ce1daf76e6c06170b0e77 |
| Mismatch | 14 | 0x09925028ce5d6a54801d04ff8f39e79af6c24289e84b301ddcdb6adfa51e901b, 0x24a68d2a4bbb02f398d3601acfd87b09f543d935fc24862c314aaf64c295acdb, 0x3f1973fe56de5ecd59a815d3b14741cf48385903b0ccfe248f7f10c2765061f7, 0x4e5bb7e3f552f5ee6ee97db9a9fcf07287aae9a1974e24999690855741121aff, 0x57b589f631f8ff20e2a89a649c4ec2e35be72eaecf155fdfde981c0fec2be5ba |
| Ranker miss | 96 | 0x00c5a772a58b117f142b2cbc8721b80d145ef7a910043ad08439863d0e78e300, 0x0237855c63eb85c5f437fba5267cc869a08c58a49501e3e5ebec9990bdd97565, 0x06d7e7436414c658a33452d28400799f3637e83930dcec39b3bd065dabc6ef04, 0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb, 0x07e5568b71f1f4d9234d5925473c598865c5ee1800348c1c4b044c6f0223f308 |
| Wrong chain | 0 | N/A (zero cases) |
| Label issue | 0 | N/A (zero cases) |

### Failure details

| Transaction | Chain | Failure kind | Exit code | stderr / retained reason |
|---|---|---|---:|---|
| 0x04e16a79ff928db2fa88619cdd045cdfc7979a61d836c9c9e585b3d6f6d8bc31 | eth | TimeoutError | N/A | cast timeout after 90s: 0x04e16a79ff928db2fa88619cdd045cdfc7979a61d836c9c9e585b3d6f6d8bc31 |
| 0x1a7ee0a7efc70ed7429edef069a1dd001fbff378748d91f17ab1876dc6d10392 | eth | TimeoutError | 0 | cast timeout after 90s: 0x1a7ee0a7efc70ed7429edef069a1dd001fbff378748d91f17ab1876dc6d10392 |
| 0x37acd17a80a5f95728459bfea85cb2e1f64b4c75cf4a4c8dcb61964e26860882 | eth | TimeoutError | 0 | cast timeout after 90s: 0x37acd17a80a5f95728459bfea85cb2e1f64b4c75cf4a4c8dcb61964e26860882 |
| 0x7c5a909b45014e35ddb89697f6be38d08eff30e7c3d3d553033a6efc3b444fdd | eth | TimeoutError | 0 | cast timeout after 90s: 0x7c5a909b45014e35ddb89697f6be38d08eff30e7c3d3d553033a6efc3b444fdd |
| 0xb072f2e88058c147d8ff643694b43a42e36525b7173ce1daf76e6c06170b0e77 | eth | TimeoutError | 0 | cast timeout after 90s: 0xb072f2e88058c147d8ff643694b43a42e36525b7173ce1daf76e6c06170b0e77 |

Raw per-transaction rows remain under `raw/`; the final manifest is `manifest.json`.
