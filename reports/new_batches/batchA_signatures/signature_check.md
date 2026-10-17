# Batch A full-signature and selector check

**Source fetch was limited to the five user-authorized raw files. The audit itself used only local files; no RPC, rescoring, fixes, or tuning.**

## Source availability

All five requested files were fetched at commit `7363f76db51f0fea97f8e659b20ee8bdc5fbca25` on `2026-10-17T17:26:14Z` UTC:

- `src/test/2021-09/DaoMaker_exp.sol` — `https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/7363f76db51f0fea97f8e659b20ee8bdc5fbca25/src/test/2021-09/DaoMaker_exp.sol`
- `src/test/2022-06/XCarnival_exp.sol` — `https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/7363f76db51f0fea97f8e659b20ee8bdc5fbca25/src/test/2022-06/XCarnival_exp.sol`
- `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` — `https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/7363f76db51f0fea97f8e659b20ee8bdc5fbca25/src/test/2022-10/RabbyWallet_SwapRouter_exp.sol`
- `src/test/2023-06/MIMSpell_exp.sol` — `https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/7363f76db51f0fea97f8e659b20ee8bdc5fbca25/src/test/2023-06/MIMSpell_exp.sol`
- `src/test/2024-09/Shezmu_exp.sol` — `https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/7363f76db51f0fea97f8e659b20ee8bdc5fbca25/src/test/2024-09/Shezmu_exp.sol`

## Counts

| Count | Value |
| --- | ---: |
| Batch A valid ETH rows | 23 |
| Resolved full argument-typed signatures | 23 |
| Unresolved signatures | 0 |
| In candidates at labeled address | 21 |
| In trace only | 0 |
| Absent | 2 |

## Per-row evidence

| Transaction | Labeled address | PoC | Full signature | Selector | Declaration lines | Call lines | Candidates | Trace prefix | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3` | `0xa5564a2d1190a141cac438c9fde686ac48a18a79` | `MIMSpell_exp.sol` | `swap(address,address,address,uint256,uint256,bytes)` | `0xa5d4096b` | 27,28,29,30,31,32,33,34 | 103 | yes | yes | `in_candidates` |
| `0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x366df0c20e00666749b16ae00475b3c41834dc659ebb29e059aa9bffa892c038` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x39328ea4377a8887d3f6ce91b2f4c6b19a851e2fc5163e2f83bbc2fc136d0c71` | `0x641249db01d5c9a04d1a223765ffd15f95167924` | `Shezmu_exp.sol` | `mint(address,uint256)` | `0x40c10f19` | 69 | 53 | yes | yes | `in_candidates` |
| `0x422e7b0a449deba30bfe922b5c34282efbdbf860205ff04b14fd8129c5b91433` | `0x39360ac1239a0b98cb8076d4135d0f72b7fd9909` | `XCarnival_exp.sol` | `pledgeAndBorrow(address,uint256,uint256,address,uint256)` | `0xe3333ae9` | 43,44,45,46,47,48,49 | 85 | yes | yes | `in_candidates` |
| `0x53835af1b7df33435188d2380328b81c0e8a22b01353c76e3dac352275895b45` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x5bbab18059f8c3fec56a0ddcd15feddf7cda8b8007b254436956db1d9ffe72ec` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x6899b8caee16dbd75359cabcd24e32b2362c474cdf39ea810cf4386018761beb` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x708ffcf4a76bd159056afb17ce6c5f5adcb5899e465bbf038aae79c3cef666ae` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x7cefbfd14497b1c577423d94ea521615991eee2590fab980230d9dd1d80ccf1c` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x84156ea5360b679dfa7cdda80c16aafbfdf1ba20b84bcf76f79666f0c405b86f` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x8bcac5e570aa695b5e0ce7dd58766eaa5830f44bbef5008aef63c6efb036e717` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x914c1ae4f03657064f0b1d5ddc6e06f39e82bce6fb2f726efdca52c092fbfc26` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0x96bf6bd14a81cf19939c0b966389daed778c3a9528a6c5dd7a4d980dec966388` | `0x6e70c88be1d5c2a4c0c8205764d01abe6a3d2e22` | `DaoMaker_exp.sol` | `init(uint256,uint256[],uint256[],address)` | `0x84304ad7` | 19 | 42 | no | no | `absent` |
| `0x9fac5412eb42aab07dcb2c5fbb03669aaa98d9c57849d44d8291d3156d9f4871` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0xa02c180149ce03d1b6e3d412585000b968b7db59a277717ec51d0899c1a3c017` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0xabfcfaf3620bbb2d41a3ffea6e31e93b9b5f61c061b9cfc5a53c74ebe890294d` | `0x39360ac1239a0b98cb8076d4135d0f72b7fd9909` | `XCarnival_exp.sol` | `pledgeAndBorrow(address,uint256,uint256,address,uint256)` | `0xe3333ae9` | 43,44,45,46,47,48,49 | 85 | no | no | `absent` |
| `0xb3af75f703ddc5d15ff872585b7d970c5204b90399a5859ec39e736a2ffbf375` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0xc10ec615e2d18c8a7dad2bb2418c422472565d9622ed851298fc848c3a451387` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0xca53e107a9a21d8f431614570a98c4718cca7172415e3fbed8842d426ac3ab54` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0xce0935010baf445e300d4d600caac7fc1fecb5ccb092cdbef57904aa7e5408b2` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |
| `0xff1f352912666796d5cd51b5dfa3e6319544aeb5938e1e9f310fd5fcb02be6da` | `0x6eb211caf6d304a76efe37d9abdfaddc2d4363d1` | `RabbyWallet_SwapRouter_exp.sol` | `swap(address,uint256,address,uint256,address,address,bytes,uint256)` | `0x32854cc2` | 137,138,139,140,141,142,143,144,145,146 | 104,105,106,107,108,109,110,111,112,113 | yes | yes | `in_candidates` |

The declaration and call line numbers above refer to the fetched PoC files. No types were inferred. Candidate presence comes from the saved candidate-selector evidence at the labeled address; trace presence means the selector matched the prefix of any saved trace call input.
