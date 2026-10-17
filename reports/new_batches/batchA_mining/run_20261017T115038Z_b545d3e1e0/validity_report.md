# Batch A Trace Validity Report

Status: **COMPLETE**

## Frozen inputs

- Canonical Batch A: `reports/new_batches/batchA_candidates.json`
- Canonical Batch A SHA-256: `4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21`
- Mining manifest: `reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/manifest.json`
- Mining manifest SHA-256: `a65b7d82317f0dd5b3b1c7c07cf0c5bce1f3e543c73ddd3c99f8c10f27053b7c`

## Counts

| Category | Count |
| --- | ---: |
| Frozen hashes | 40 |
| Attempt artifacts | 40 |
| Raw artifacts | 40 |
| Valid trace payloads | 23 |
| Invalid trace payloads | 1 |
| Missing/failed traces | 16 |
| Questionable traces | 1 |

## Reason counts

| Reason | Count |
| --- | ---: |
| valid | 23 |
| empty | 0 |
| truncated | 0 |
| rpc_limited | 0 |
| malformed | 1 |
| chain_mismatch | 0 |
| other | 0 |

## Valid-set freeze

- Valid-set artifact SHA-256: `fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785`

## Per-artifact decisions

| Seq | Chain | Transaction hash | Status | Classification | Reason |
| ---: | --- | --- | --- | --- | --- |
| 1 | eth | `0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 2 | eth | `0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 3 | eth | `0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 4 | eth | `0x366df0c20e00666749b16ae00475b3c41834dc659ebb29e059aa9bffa892c038` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 5 | eth | `0x39328ea4377a8887d3f6ce91b2f4c6b19a851e2fc5163e2f83bbc2fc136d0c71` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 6 | eth | `0x422e7b0a449deba30bfe922b5c34282efbdbf860205ff04b14fd8129c5b91433` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 7 | eth | `0x53835af1b7df33435188d2380328b81c0e8a22b01353c76e3dac352275895b45` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 8 | eth | `0x5bbab18059f8c3fec56a0ddcd15feddf7cda8b8007b254436956db1d9ffe72ec` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 9 | eth | `0x6899b8caee16dbd75359cabcd24e32b2362c474cdf39ea810cf4386018761beb` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 10 | eth | `0x708ffcf4a76bd159056afb17ce6c5f5adcb5899e465bbf038aae79c3cef666ae` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 11 | eth | `0x7cefbfd14497b1c577423d94ea521615991eee2590fab980230d9dd1d80ccf1c` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 12 | eth | `0x84156ea5360b679dfa7cdda80c16aafbfdf1ba20b84bcf76f79666f0c405b86f` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 13 | eth | `0x8bcac5e570aa695b5e0ce7dd58766eaa5830f44bbef5008aef63c6efb036e717` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 14 | eth | `0x914c1ae4f03657064f0b1d5ddc6e06f39e82bce6fb2f726efdca52c092fbfc26` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 15 | eth | `0x96bf6bd14a81cf19939c0b966389daed778c3a9528a6c5dd7a4d980dec966388` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 16 | eth | `0x9fac5412eb42aab07dcb2c5fbb03669aaa98d9c57849d44d8291d3156d9f4871` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 17 | eth | `0xa02c180149ce03d1b6e3d412585000b968b7db59a277717ec51d0899c1a3c017` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 18 | eth | `0xabfcfaf3620bbb2d41a3ffea6e31e93b9b5f61c061b9cfc5a53c74ebe890294d` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 19 | eth | `0xb3af75f703ddc5d15ff872585b7d970c5204b90399a5859ec39e736a2ffbf375` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 20 | eth | `0xc10ec615e2d18c8a7dad2bb2418c422472565d9622ed851298fc848c3a451387` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 21 | eth | `0xca53e107a9a21d8f431614570a98c4718cca7172415e3fbed8842d426ac3ab54` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 22 | eth | `0xce0935010baf445e300d4d600caac7fc1fecb5ccb092cdbef57904aa7e5408b2` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 23 | eth | `0xf1c1066c259672396b8f242311a9f1c83bfa52c27529d713d80a3da93047c37f` | invalid | malformed | malformed: non-hexadecimal/redacted field in callTracer payload |
| 24 | eth | `0xff1f352912666796d5cd51b5dfa3e6319544aeb5938e1e9f310fd5fcb02be6da` | valid | valid_trace_payload | valid: non-empty, recursively well-formed callTracer payload |
| 25 | base | `0x6be0c4b5414883a933639c136971026977df4737b061f864a4a04e4bd7f07106` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 26 | base | `0x8fcdfcded45100437ff94801090355f2f689941dca75de9a702e01670f361c04` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 27 | base | `0xe63a8df8759f41937432cd34c590d85af61b3343cf438796c6ed2c8f5b906f62` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 28 | polygon | `0x051f80a7ef69e1ffad889ec7e1f7d29a9e80883156b5c8528438b5bb8b7a689a` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 29 | polygon | `0xdd82fde0cc2fb7bdc078aead655f6d5e75a267a47c33fa92b658e3573b93ef0c` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 30 | bsc | `0x36438165d701c883fd9a03631ee0cdeec35a138153720006ab59264db7e075c1` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 31 | bsc | `0x4302de51c8126e7934da9be1affbde73e5153fe1f9d0200a738a269fe07d22c7` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 32 | bsc | `0x55983d8701e40353fee90803688170a16424ee702f6b21bb198bb8e7282112cd` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 33 | bsc | `0x601b8ab0c1d51e71796a0df5453ca671ae23de3d5ec9ffd87b9c378504f99c32` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 34 | bsc | `0x9e328f77809ea3c01833ec7ed8928edb4f5798c96f302b54fc640a22b3dd1a52` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 35 | bsc | `0xa624660c29ee97f3f4ebd36232d8199e7c97533c9db711fa4027994aa11e01b9` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 36 | bsc | `0xae8ca9dc8258ae32899fe641985739c3fa53ab1f603973ac74b424e165c66ccf` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 37 | bsc | `0xb181e88e6b37ee9986f2a57aefb94779402fdb928654aa7c1dda5138b90d0e14` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 38 | bsc | `0xc29c98da0c14f4ca436d38f8238f8da1c84c4b1ee6480c4b4facc4b81a013438` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 39 | bsc | `0xe24ee2af7ceee6d6fad1cacda26004adfe0f44d397a17d2aca56c9a01d759142` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
| 40 | bsc | `0xf77c5904da98d3d4a6e651d0846d35545ef5ca0b969132ae81a9c63e1efc2113` | missing_or_failed | rpc_error | rpc_error:-32000:transaction not found; no trace payload was returned. Preserved separately from invalid trace payloads. |
