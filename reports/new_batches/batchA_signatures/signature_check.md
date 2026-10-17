# Batch A full-signature check

**Offline only. No source fetch, RPC, network, tuning, fixes, or rescoring.**

## Source availability

The DeFiHackLabs PoC files named by the frozen labels are not cached locally. No files were fetched. Needed files:

- `src/test/2021-09/DaoMaker_exp.sol`
- `src/test/2022-06/XCarnival_exp.sol`
- `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol`
- `src/test/2023-06/MIMSpell_exp.sol`
- `src/test/2024-09/Shezmu_exp.sol`

## Counts

| Count | Value |
| --- | ---: |
| Batch A valid ETH rows | 23 |
| Resolved full argument-typed signatures | 0 |
| Unresolved signatures | 23 |
| Appears in candidates | 0 (no selectors computed) |
| In trace only | 0 (no selectors computed) |
| Absent | 0 (no selectors computed) |

## Per-row source references

The line numbers below are the line fields recorded in the frozen label artifact. The source files required to verify them are not present locally.

| Transaction | Source file | Source transaction line | Vulnerable-function line | Label | Signature status |
| --- | --- | ---: | ---: | --- | --- |
| `0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 31 | 100 | `swap()` | unresolved: source file not cached |
| `0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3` | `src/test/2023-06/MIMSpell_exp.sol` | 11 | 86 | `swap()` | unresolved: source file not cached |
| `0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 17 | 100 | `swap()` | unresolved: source file not cached |
| `0x366df0c20e00666749b16ae00475b3c41834dc659ebb29e059aa9bffa892c038` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 19 | 100 | `swap()` | unresolved: source file not cached |
| `0x39328ea4377a8887d3f6ce91b2f4c6b19a851e2fc5163e2f83bbc2fc136d0c71` | `src/test/2024-09/Shezmu_exp.sol` | 11 | 50 | `mint()` | unresolved: source file not cached |
| `0x422e7b0a449deba30bfe922b5c34282efbdbf860205ff04b14fd8129c5b91433` | `src/test/2022-06/XCarnival_exp.sol` | 27 | 84 | `pledgeAndBorrow()` | unresolved: source file not cached |
| `0x53835af1b7df33435188d2380328b81c0e8a22b01353c76e3dac352275895b45` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 16 | 100 | `swap()` | unresolved: source file not cached |
| `0x5bbab18059f8c3fec56a0ddcd15feddf7cda8b8007b254436956db1d9ffe72ec` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 29 | 100 | `swap()` | unresolved: source file not cached |
| `0x6899b8caee16dbd75359cabcd24e32b2362c474cdf39ea810cf4386018761beb` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 30 | 100 | `swap()` | unresolved: source file not cached |
| `0x708ffcf4a76bd159056afb17ce6c5f5adcb5899e465bbf038aae79c3cef666ae` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 27 | 100 | `swap()` | unresolved: source file not cached |
| `0x7cefbfd14497b1c577423d94ea521615991eee2590fab980230d9dd1d80ccf1c` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 24 | 100 | `swap()` | unresolved: source file not cached |
| `0x84156ea5360b679dfa7cdda80c16aafbfdf1ba20b84bcf76f79666f0c405b86f` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 22 | 100 | `swap()` | unresolved: source file not cached |
| `0x8bcac5e570aa695b5e0ce7dd58766eaa5830f44bbef5008aef63c6efb036e717` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 25 | 100 | `swap()` | unresolved: source file not cached |
| `0x914c1ae4f03657064f0b1d5ddc6e06f39e82bce6fb2f726efdca52c092fbfc26` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 12 | 100 | `swap()` | unresolved: source file not cached |
| `0x96bf6bd14a81cf19939c0b966389daed778c3a9528a6c5dd7a4d980dec966388` | `src/test/2021-09/DaoMaker_exp.sol` | 9 | 15 | `init()` | unresolved: source file not cached |
| `0x9fac5412eb42aab07dcb2c5fbb03669aaa98d9c57849d44d8291d3156d9f4871` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 20 | 100 | `swap()` | unresolved: source file not cached |
| `0xa02c180149ce03d1b6e3d412585000b968b7db59a277717ec51d0899c1a3c017` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 13 | 100 | `swap()` | unresolved: source file not cached |
| `0xabfcfaf3620bbb2d41a3ffea6e31e93b9b5f61c061b9cfc5a53c74ebe890294d` | `src/test/2022-06/XCarnival_exp.sol` | 28 | 84 | `pledgeAndBorrow()` | unresolved: source file not cached |
| `0xb3af75f703ddc5d15ff872585b7d970c5204b90399a5859ec39e736a2ffbf375` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 26 | 100 | `swap()` | unresolved: source file not cached |
| `0xc10ec615e2d18c8a7dad2bb2418c422472565d9622ed851298fc848c3a451387` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 23 | 100 | `swap()` | unresolved: source file not cached |
| `0xca53e107a9a21d8f431614570a98c4718cca7172415e3fbed8842d426ac3ab54` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 28 | 100 | `swap()` | unresolved: source file not cached |
| `0xce0935010baf445e300d4d600caac7fc1fecb5ccb092cdbef57904aa7e5408b2` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 18 | 100 | `swap()` | unresolved: source file not cached |
| `0xff1f352912666796d5cd51b5dfa3e6319544aeb5938e1e9f310fd5fcb02be6da` | `src/test/2022-10/RabbyWallet_SwapRouter_exp.sol` | 21 | 100 | `swap()` | unresolved: source file not cached |

No argument types were guessed or inferred. Because zero full signatures were resolved, no keccak selector was computed and no candidate/trace selector classification was performed.
