# Recovered trace inventory

Cross-check of the nine bounded-run rows against already-present local evidence. No new requests or scores were run.

| Recovery class | Count |
|---|---:|
| `captured_trace_recovered_but_function_gt_unavailable` | 9 |
| `external_capture_failed_local_trace_recovered_but_function_gt_unavailable` | 4 |
| `externally_blocked_no_local_call_tree` | 2 |

| Stable ID | External | Local trace | Function-level GT | Recovery class |
|---|---|---|---|---|
| `base:0x8fcdfcded45100437ff94801090355f2f689941dca75de9a702e01670f361c04` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |
| `base:0xbb837d417b76dd237b4418e1695a50941a69259a1c4dee561ea57d982b9f10ec` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |
| `bsc:0x13d19809b19ac512da6d110764caee75e2157ea62cb70937c8d9471afcb061bf` | FAILED | none | 0 location keys | `externally_blocked_no_local_call_tree` |
| `bsc:0x13d19809b19ac512da6d110764caee75e2157ea62cb70937c8d9471afcb061bf` | FAILED | none | 0 location keys | `externally_blocked_no_local_call_tree` |
| `eth:0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |
| `eth:0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |
| `eth:0x9a97d85642f956ad7a6b852cf7bed6f9669e2c2815f3279855acf7f1328e7d46` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |
| `eth:0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |
| `eth:0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |
| `fantom:0x19315e5b150d0a83e797203bb9c957ec1fa8a6f404f4f761d970cb29a74a5dd6` | FAILED | integrated_chain_trace_probe | 0 location keys | `external_capture_failed_local_trace_recovered_but_function_gt_unavailable` |
| `fantom:0x19315e5b150d0a83e797203bb9c957ec1fa8a6f404f4f761d970cb29a74a5dd6` | FAILED | integrated_chain_trace_probe | 0 location keys | `external_capture_failed_local_trace_recovered_but_function_gt_unavailable` |
| `gnosis:0x534b84f657883ddc1b66a314e8b392feb35024afdec61dfe8e7c510cfac1a098` | FAILED | integrated_chain_trace_probe | 0 location keys | `external_capture_failed_local_trace_recovered_but_function_gt_unavailable` |
| `gnosis:0x534b84f657883ddc1b66a314e8b392feb35024afdec61dfe8e7c510cfac1a098` | FAILED | integrated_chain_trace_probe | 0 location keys | `external_capture_failed_local_trace_recovered_but_function_gt_unavailable` |
| `polygon:0x0053490215baf541362fc78be0de98e3147f40223238d5b12512b3e26c0a2c2f` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |
| `polygon:0x10f2c28f5d6cd8d7b56210b4d5e0cece27e45a30808cd3d3443c05d4275bb008` | CAPTURED | cohort_rebuild_v2_trace | 0 location keys | `captured_trace_recovered_but_function_gt_unavailable` |

Local call trees exist for all nine rows, but current-cohort ground truth provides no independently source-bound function locations for the five non-original rows and three failed external rows. The BSC failed attempt has no local call-tree artifact; its dRPC retries are blocked by provider rate limits.

Machine-readable artifact: `reports/reconciliation/recovered_trace_inventory_20261019.json`.
