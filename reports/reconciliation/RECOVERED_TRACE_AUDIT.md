# Recovered original-benchmark trace audit

This report audits previously captured, redacted dRPC callTracer responses. It does not make new RPC requests, rerun ranking, or infer function names from untyped labels.

| Measure | Result |
|---|---:|
| Captured rows | 9 |
| Failed attempts | 6 |
| Captured rows with imported original ground truth | 4 |
| Captured rows with observed target address | 4 |
| Transaction hash checks passed | 9 |
| Exact function identities established from typed public evidence plus trace | 4 |

| Stable ID | Ground-truth address | Observed? | Observed selectors | Identity status |
|---|---|---:|---|---|
| `base:0x8fcdfcded45100437ff94801090355f2f689941dca75de9a702e01670f361c04` | `n/a` | false | `none` | NO_IMPORTED_GROUND_TRUTH |
| ↳ typed evidence |  |  |  | none |
| `base:0xbb837d417b76dd237b4418e1695a50941a69259a1c4dee561ea57d982b9f10ec` | `n/a` | false | `none` | NO_IMPORTED_GROUND_TRUTH |
| ↳ typed evidence |  |  |  | none |
| `eth:0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb` | `0xb40b6608b2743e691c9b54ddbdee7bf03cd79f1c` | true | `0x095ea7b3, 0x23b872dd, 0x70a08231, 0xa9059cbb, 0xd341ea79` | ESTABLISHED_BY_TYPED_SIGNATURE_AND_TRACE |
| ↳ typed evidence |  |  |  | cacheAssetPrice()=0xd341ea79 (etherscan_verified_exact_match) |
| `eth:0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c` | `0xe8b3bc58774857732c6c1147bfc9b9e5fb6f427c` | true | `0x313ce567, 0x50d25bcd` | ESTABLISHED_BY_TYPED_SIGNATURE_AND_TRACE |
| ↳ typed evidence |  |  |  | latestAnswer()=0x50d25bcd (etherscan_verified_exact_match) |
| `eth:0x9a97d85642f956ad7a6b852cf7bed6f9669e2c2815f3279855acf7f1328e7d46` | `n/a` | false | `none` | NO_IMPORTED_GROUND_TRUTH |
| ↳ typed evidence |  |  |  | none |
| `eth:0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa` | `0x420a50a62b17c18b36c64478784536ba980feac8` | true | `0x0f04ba67, 0xd5f724f3` | ESTABLISHED_BY_TYPED_SIGNATURE_AND_TRACE |
| ↳ typed evidence |  |  |  | doSwapThroughOrionPool(address,address,(uint112,uint112,address,bool,bool,bool,bool,bool,address,address[]))=0xd5f724f3 (etherscan_verified_exact_match) |
| `eth:0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d` | `0xe025e3ca2be02316033184551d4d3aa22024d9dc` | true | `0x03ddf252, 0x1b2ef1ca, 0x36f022aa, 0x441a3e70, 0xe2bbb158` | ESTABLISHED_BY_TYPED_SIGNATURE_AND_TRACE |
| ↳ typed evidence |  |  |  | donateToReserves(uint256,uint256)=0x36f022aa (openchain_signature_database_has_verified_contract) |
| `polygon:0x0053490215baf541362fc78be0de98e3147f40223238d5b12512b3e26c0a2c2f` | `n/a` | false | `none` | NO_IMPORTED_GROUND_TRUTH |
| ↳ typed evidence |  |  |  | none |
| `polygon:0x10f2c28f5d6cd8d7b56210b4d5e0cece27e45a30808cd3d3443c05d4275bb008` | `n/a` | false | `none` | NO_IMPORTED_GROUND_TRUTH |
| ↳ typed evidence |  |  |  | none |

For four captured original rows, a public typed-signature source now maps the imported label to an observed selector. This establishes the observed function identity for those rows only; it does not reproduce the original paper scorer or prove the remaining 111 identities.

Source manifest SHA-256: `10a1ef2665e9e5cac16204ca397b22ca96574d24ab651133f21a132161d967e7`
