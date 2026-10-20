# Transaction-level error attribution

Offline analysis of all 115 cached provider-pinned cases. No ranking, RPC, cast, model, or source-retrieval call was made.

## Aggregate

- Denominator: 115
- Status counts: `{"failed": 5, "ok": 110}`
- Primary classifications: `{"A_cached_execution_trace_failure": 5, "B_no_target_candidate_in_saved_set": 41, "C_target_candidate_ranked_outside_top5": 14, "D_top5_candidate_reconstruction_equality_miss": 2, "E_demonstrated_identity_normalization_mismatch": 3, "localized": 50}`

| Metric | Upstream reconstruction | Current address-aware |
|---|---:|---:|
| R@1 | 27/115 (23.48%) | 25/115 (21.74%) |
| R@3 | 49/115 (42.61%) | 49/115 (42.61%) |
| R@5 | 53/115 (46.09%) | 52/115 (45.22%) |

## Demonstrated normalization/equality issues

- Selector/name resolution cases: `2`.
- Address identity mismatch cases: `3`.

## Highest-value investigation queue

| Priority | Case | Classification | Unresolved question |
|---:|---|---|---|
| 1 | `0x2881e839d4d562fad5356183e4f6a9d427ba6f475614ce8ef64dbfe557a4a2cc` | E_demonstrated_identity_normalization_mismatch | Validate the saved selector/address identity against an exact upstream scoring rule or ABI mapping. |
| 1 | `0x2b6d0af0dc513a15e325703405739057f9de6ef3f99934b957653b8a3fade4c6` | E_demonstrated_identity_normalization_mismatch | Validate the saved selector/address identity against an exact upstream scoring rule or ABI mapping. |
| 1 | `0x6439d63cc57fb68a32ea8ffd8f02496e8abad67292be94904c0b47a4d14ce90d` | D_top5_candidate_reconstruction_equality_miss | Validate the saved selector/address identity against an exact upstream scoring rule or ABI mapping. |
| 1 | `0x72a252277e30ea6a37d2dc9905c280f3bc389b87f72b81a59aa8f50baebd8eaa` | D_top5_candidate_reconstruction_equality_miss | Validate the saved selector/address identity against an exact upstream scoring rule or ABI mapping. |
| 1 | `0xd9b3e229acc755881890394cc76fde0d7b83b1abd4d046b0f69c1fd9fd495ff6` | E_demonstrated_identity_normalization_mismatch | Validate the saved selector/address identity against an exact upstream scoring rule or ABI mapping. |
| 2 | `0x1106418384414ed56cd7cbb9fedc66a02d39b663d580abc618f2d387348354ab` | C_target_candidate_ranked_outside_top5 | Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5. |
| 2 | `0x485e08dc2b6a4b3aeadcb89c3d18a37666dc7d9424961a2091d6b3696792f0f3` | C_target_candidate_ranked_outside_top5 | Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5. |
| 2 | `0x90fb0c9976361f537330a5617a404045ffb3fef5972cf67b531386014eeae7a9` | C_target_candidate_ranked_outside_top5 | Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5. |
| 2 | `0xa4e650772f6e6b7ecc0964fe4c3854850669d1467570a2fa2b6edfa0f112c4b7` | C_target_candidate_ranked_outside_top5 | Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5. |
| 2 | `0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa` | C_target_candidate_ranked_outside_top5 | Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5. |
| 2 | `0xb36486f032a450782d5d2fac118ea90a6d3b08cac3409d949c59b43bcd6dbb8f` | C_target_candidate_ranked_outside_top5 | Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5. |
| 2 | `0xcf834aff4de9992f5da9c443600dad9c6277a8a00de5007842fece51564992db` | C_target_candidate_ranked_outside_top5 | Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5. |
| 2 | `0xf1818f62c635e5c80ef16b7857da812c74ce330ebed46682b4d173bffe84c666` | C_target_candidate_ranked_outside_top5 | Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5. |
| 3 | `0x0237855c63eb85c5f437fba5267cc869a08c58a49501e3e5ebec9990bdd97565` | B_no_target_candidate_in_saved_set | Resolve whether the target-address candidates use a selector/signature that is not represented by the saved function identifier. |
| 3 | `0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb` | B_no_target_candidate_in_saved_set | Resolve whether the target-address candidates use a selector/signature that is not represented by the saved function identifier. |
| 3 | `0x0eb8f8d148508e752d9643ccf49ac4cb0c21cbad346b5bbcf2d06974d31bd5c4` | B_no_target_candidate_in_saved_set | Resolve whether the target-address candidates use a selector/signature that is not represented by the saved function identifier. |
| 3 | `0x160c5950a01b88953648ba90ec0a29b0c5383e055d35a7835d905c53a3dda01e` | B_no_target_candidate_in_saved_set | Resolve whether the target-address candidates use a selector/signature that is not represented by the saved function identifier. |
| 3 | `0x1f1aba5bef04b7026ae3cb1cb77987071a8aff9592e785dd99860566ccad83d1` | B_no_target_candidate_in_saved_set | Resolve whether the target-address candidates use a selector/signature that is not represented by the saved function identifier. |
| 3 | `0x26a83db7e28838dd9fee6fb7314ae58dcc6aee9a20bf224c386ff5e80f7e4cf2` | B_no_target_candidate_in_saved_set | Resolve whether the target-address candidates use a selector/signature that is not represented by the saved function identifier. |
| 3 | `0x4f4d6909a442b4d86f79a9044dcada6a128ddd9f62c26f410134a72d2fc31389` | B_no_target_candidate_in_saved_set | Resolve whether the target-address candidates use a selector/signature that is not represented by the saved function identifier. |

## Scientific boundary

This is a cached diagnostic-prediction analysis, not an exact reproduction of the ASE 2025 system. Candidate absence does not prove trace failure, and saved rankings do not expose the unreleased upstream evaluator's private evidence or tie handling.
