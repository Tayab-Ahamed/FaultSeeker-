# Batch A selector check

**Label: selector check, offline**

| Class | Count | Examples |
| --- | ---: | --- |
| 1 — selector present in candidates, name unresolved | 0 | N/A |
| 2 — selector in trace but not a candidate | 0 | N/A |
| 3 — selector never appears in trace | 21 | 0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41, 0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3, 0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870 |
| 4 — cannot determine (name only) | 0 | N/A |

| Transaction | Function | Selector | At address in candidates? | Anywhere in candidates? | In trace? | Called at labeled address? | Source target statement | Class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3` | `swap()` | `0x8119c065` | False | False | False | False | not stated | 3 |
| `0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x366df0c20e00666749b16ae00475b3c41834dc659ebb29e059aa9bffa892c038` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x39328ea4377a8887d3f6ce91b2f4c6b19a851e2fc5163e2f83bbc2fc136d0c71` | `mint()` | `0x1249c58b` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x53835af1b7df33435188d2380328b81c0e8a22b01353c76e3dac352275895b45` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x5bbab18059f8c3fec56a0ddcd15feddf7cda8b8007b254436956db1d9ffe72ec` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x6899b8caee16dbd75359cabcd24e32b2362c474cdf39ea810cf4386018761beb` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x708ffcf4a76bd159056afb17ce6c5f5adcb5899e465bbf038aae79c3cef666ae` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x7cefbfd14497b1c577423d94ea521615991eee2590fab980230d9dd1d80ccf1c` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x84156ea5360b679dfa7cdda80c16aafbfdf1ba20b84bcf76f79666f0c405b86f` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x8bcac5e570aa695b5e0ce7dd58766eaa5830f44bbef5008aef63c6efb036e717` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x914c1ae4f03657064f0b1d5ddc6e06f39e82bce6fb2f726efdca52c092fbfc26` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x96bf6bd14a81cf19939c0b966389daed778c3a9528a6c5dd7a4d980dec966388` | `init()` | `0xe1c7392a` | False | False | False | False | internal vulnerable function stated | 3 |
| `0x9fac5412eb42aab07dcb2c5fbb03669aaa98d9c57849d44d8291d3156d9f4871` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0xa02c180149ce03d1b6e3d412585000b968b7db59a277717ec51d0899c1a3c017` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0xb3af75f703ddc5d15ff872585b7d970c5204b90399a5859ec39e736a2ffbf375` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0xc10ec615e2d18c8a7dad2bb2418c422472565d9622ed851298fc848c3a451387` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0xca53e107a9a21d8f431614570a98c4718cca7172415e3fbed8842d426ac3ab54` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0xce0935010baf445e300d4d600caac7fc1fecb5ccb092cdbef57904aa7e5408b2` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |
| `0xff1f352912666796d5cd51b5dfa3e6319544aeb5938e1e9f310fd5fcb02be6da` | `swap()` | `0x8119c065` | False | False | False | False | internal vulnerable function stated | 3 |

Full per-row trace/candidate selector evidence is in `selector_check.json`.
