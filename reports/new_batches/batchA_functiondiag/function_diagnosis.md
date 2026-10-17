# Batch A function-level diagnosis

**Label: function-level diagnosis, read-only**

Producer-era source commit: `1b1c7395771663622dd14b9731b4b8b471221960`

## Classification counts

| Class | Count | Examples |
| --- | ---: | --- |
| a — label function present in candidates but key format differs | 0 | N/A |
| b — label function absent from candidates at that address | 20 | 0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41, 0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3, 0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870 |
| c — label is semantically a different kind of function than the benchmark ground truth | 2 | 0x422e7b0a449deba30bfe922b5c34282efbdbf860205ff04b14fd8129c5b91433, 0xabfcfaf3620bbb2d41a3ffea6e31e93b9b5f61c061b9cfc5a53c74ebe890294d |
| d — other | 1 | 0x39328ea4377a8887d3f6ce91b2f4c6b19a851e2fc5163e2f83bbc2fc136d0c71 |

## Per-row details

| Transaction | Label function | Source | Semantic location | Top-5 at labeled address | Key basis | Class |
| --- | --- | --- | --- | --- | --- | --- |
| `0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3` | `swap()` | `src/test/2023-06/MIMSpell_exp.sol` | internal_vulnerable_function | r31:- [0xa5d4096b] (unresolved) | selector vs name | b |
| `0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x366df0c20e00666749b16ae00475b3c41834dc659ebb29e059aa9bffa892c038` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x39328ea4377a8887d3f6ce91b2f4c6b19a851e2fc5163e2f83bbc2fc136d0c71` | `mint()` | `src/test/2024-09/Shezmu_exp.sol` | internal_vulnerable_function | r5:decimals [0x313ce567] (resolved); r7:transferfrom [0x23b872dd] (resolved); r12:approve [0x095ea7b3] (resolved); r13:mint [0x40c10f19] (resolved) | name vs name | d |
| `0x422e7b0a449deba30bfe922b5c34282efbdbf860205ff04b14fd8129c5b91433` | `pledgeAndBorrow()` | `src/test/2022-06/XCarnival_exp.sol` | exploit_entry_call | r7:onerc721received [0x150b7a02] (resolved); r12:- [0xe3333ae9] (unresolved); r13:- [0x61bc221a] (unresolved); r14:- [0x023245d7] (unresolved) | selector vs name | c |
| `0x53835af1b7df33435188d2380328b81c0e8a22b01353c76e3dac352275895b45` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x5bbab18059f8c3fec56a0ddcd15feddf7cda8b8007b254436956db1d9ffe72ec` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x6899b8caee16dbd75359cabcd24e32b2362c474cdf39ea810cf4386018761beb` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r12:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x708ffcf4a76bd159056afb17ce6c5f5adcb5899e465bbf038aae79c3cef666ae` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x7cefbfd14497b1c577423d94ea521615991eee2590fab980230d9dd1d80ccf1c` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x84156ea5360b679dfa7cdda80c16aafbfdf1ba20b84bcf76f79666f0c405b86f` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x8bcac5e570aa695b5e0ce7dd58766eaa5830f44bbef5008aef63c6efb036e717` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x914c1ae4f03657064f0b1d5ddc6e06f39e82bce6fb2f726efdca52c092fbfc26` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r12:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0x96bf6bd14a81cf19939c0b966389daed778c3a9528a6c5dd7a4d980dec966388` | `init()` | `src/test/2021-09/DaoMaker_exp.sol` | internal_vulnerable_function | none | no candidate key at labeled address | b |
| `0x9fac5412eb42aab07dcb2c5fbb03669aaa98d9c57849d44d8291d3156d9f4871` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0xa02c180149ce03d1b6e3d412585000b968b7db59a277717ec51d0899c1a3c017` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0xabfcfaf3620bbb2d41a3ffea6e31e93b9b5f61c061b9cfc5a53c74ebe890294d` | `pledgeAndBorrow()` | `src/test/2022-06/XCarnival_exp.sol` | exploit_entry_call | r1:- [0xe4c79a4a] (unresolved); r3:- [0xfe1b7ed5] (unresolved) | selector vs name | c |
| `0xb3af75f703ddc5d15ff872585b7d970c5204b90399a5859ec39e736a2ffbf375` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0xc10ec615e2d18c8a7dad2bb2418c422472565d9622ed851298fc848c3a451387` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r4:- [0x0779afe6] (unresolved); r14:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0xca53e107a9a21d8f431614570a98c4718cca7172415e3fbed8842d426ac3ab54` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0xce0935010baf445e300d4d600caac7fc1fecb5ccb092cdbef57904aa7e5408b2` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |
| `0xff1f352912666796d5cd51b5dfa3e6319544aeb5938e1e9f310fd5fcb02be6da` | `swap()` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | internal_vulnerable_function | r2:- [0x0779afe6] (unresolved); r9:- [0x32854cc2] (unresolved) | selector vs name | b |

The complete label source text, exact address casing, selector-equality status, and per-row candidate details are in `function_diagnosis.json`.
