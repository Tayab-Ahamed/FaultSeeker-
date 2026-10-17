# Batch A selector alignment

**post-hoc label alignment, exploratory, N=23, ETH only, DeFiHackLabs-sourced**

No RPC, network, ranker invocation, rescoring, tuning, or production-code change was performed. The saved producer-era candidate evidence was reused from the dRPC final replay artifacts.

The alignment key was chosen after seeing the name-matching zeros. It is the labeled vulnerable address plus the keccak256 selector of the resolved full signature.

## Metrics

| Alignment | R@1 | R@3 | R@5 | N |
| --- | ---: | ---: | ---: | ---: |
| Address + selector (primary) | 0/23 (0.000000) | 0/23 (0.000000) | 0/23 (0.000000) | 23 |
| Address-only (comparison) | 1/23 (0.043478) | 18/23 (0.782609) | 20/23 (0.869565) | 23 |

## Per-row ranks

`address+selector rank` is the global rank of the first saved candidate matching both the labeled address and resolved selector. `address-only rank` is the first saved candidate matching only the labeled address.

| Tx prefix | Address+selector rank | Address-only rank | Candidate count | Selector |
| --- | ---: | ---: | ---: | --- |
| `0x07887fff` | 9 | 2 | 10 | `0x32854cc2` |
| `0x2c9f87e2` | 31 | 31 | 32 | `0xa5d4096b` |
| `0x32259275` | 9 | 2 | 10 | `0x32854cc2` |
| `0x366df0c2` | 9 | 2 | 10 | `0x32854cc2` |
| `0x39328ea4` | 13 | 5 | 18 | `0x40c10f19` |
| `0x422e7b0a` | 12 | 7 | 31 | `0xe3333ae9` |
| `0x53835af1` | 9 | 2 | 10 | `0x32854cc2` |
| `0x5bbab180` | 9 | 2 | 10 | `0x32854cc2` |
| `0x6899b8ca` | 12 | 2 | 13 | `0x32854cc2` |
| `0x708ffcf4` | 9 | 2 | 10 | `0x32854cc2` |
| `0x7cefbfd1` | 9 | 2 | 10 | `0x32854cc2` |
| `0x84156ea5` | 9 | 2 | 10 | `0x32854cc2` |
| `0x8bcac5e5` | 9 | 2 | 10 | `0x32854cc2` |
| `0x914c1ae4` | 12 | 2 | 13 | `0x32854cc2` |
| `0x96bf6bd1` | None | None | 4 | `0x84304ad7` |
| `0x9fac5412` | 9 | 2 | 10 | `0x32854cc2` |
| `0xa02c1801` | 9 | 2 | 10 | `0x32854cc2` |
| `0xabfcfaf3` | None | 1 | 88 | `0xe3333ae9` |
| `0xb3af75f7` | 9 | 2 | 10 | `0x32854cc2` |
| `0xc10ec615` | 14 | 4 | 15 | `0x32854cc2` |
| `0xca53e107` | 9 | 2 | 10 | `0x32854cc2` |
| `0xce093501` | 9 | 2 | 10 | `0x32854cc2` |
| `0xff1f3529` | 9 | 2 | 10 | `0x32854cc2` |

## Caveats

- Selector alignment is exploratory and differs from the benchmark's name-based scoring.
- The address+selector alignment key was selected after the name-matching results were zero.
- Two rows have absent selectors and therefore `None` address+selector ranks.
- This is a single-chain ETH-only sample with N=23.
- Labels were taken from the DeFiHackLabs PoC source declarations and call lines; no types were guessed.
- The saved full-list artifact records 89 candidates for `0xabfcfaf3...`, while the drpc_final summary records 88; the table uses the drpc_final count and the selector is absent in both saved address-level evidence sets.
