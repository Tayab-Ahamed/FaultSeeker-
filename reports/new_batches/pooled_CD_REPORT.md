# Frozen C+D pooled localization report

All C/D numbers below aggregate saved first-hit ranks only. No ranking, scoring runner, model, RPC, tuning, candidate generation or batch construction was executed. Post-result miss analysis is **exploratory**.

## C+D pooled: 40 fresh rows

| Match | R@1 | R@3 | R@5 |
|---|---|---|---|
| Address + selector | 5/40 (12.50%; [5.46, 26.11]) | 14/40 (35.00%; [22.13, 50.49]) | 16/40 (40.00%; [26.35, 55.40]) |
| Address only | 9/40 (22.50%; [12.32, 37.50]) | 18/40 (45.00%; [30.71, 60.17]) | 21/40 (52.50%; [37.50, 67.06]) |
| Selector only | 7/40 (17.50%; [8.75, 31.95]) | 14/40 (35.00%; [22.13, 50.49]) | 17/40 (42.50%; [28.51, 57.80]) |

Intervals are two-sided Wilson 95% score intervals (z=1.959963984540054), computed from summed hits and summed denominators, not averages of percentages or interval endpoints. Forty distinct transaction hashes; 30 C + 10 D, no hash overlap. C and D used different frozen configurations, so this is a descriptive mixed-system pool, not a single-system test or a causal upgrade estimate. The sample is source-backed PoC-target convenience data, not independently adjudicated root-cause ground truth. Wilson intervals assume independent Bernoulli outcomes and do not correct for selection bias or incident dependence.

### Batch C separately

| Match | R@1 | R@3 | R@5 |
|---|---|---|---|
| Address + selector | 3/30 (10.00%; [3.46, 25.62]) | 11/30 (36.67%; [21.87, 54.49]) | 12/30 (40.00%; [24.59, 57.68]) |
| Address only | 5/30 (16.67%; [7.34, 33.56]) | 12/30 (40.00%; [24.59, 57.68]) | 15/30 (50.00%; [33.15, 66.85]) |
| Selector only | 5/30 (16.67%; [7.34, 33.56]) | 11/30 (36.67%; [21.87, 54.49]) | 13/30 (43.33%; [27.38, 60.80]) |

### Batch D separately

| Match | R@1 | R@3 | R@5 |
|---|---|---|---|
| Address + selector | 2/10 (20.00%; [5.67, 50.98]) | 3/10 (30.00%; [10.78, 60.32]) | 4/10 (40.00%; [16.82, 68.73]) |
| Address only | 4/10 (40.00%; [16.82, 68.73]) | 6/10 (60.00%; [31.27, 83.18]) | 6/10 (60.00%; [31.27, 83.18]) |
| Selector only | 2/10 (20.00%; [5.67, 50.98]) | 3/10 (30.00%; [10.78, 60.32]) | 4/10 (40.00%; [16.82, 68.73]) |

## Original 110 records — exploratory

| Match | R@1 | R@3 | R@5 |
|---|---|---|---|
| Exact address + selector | N/A | N/A | N/A |
| Address only | 38/110 (34.55%; [26.32, 43.82]) | 67/110 (60.91%; [51.57, 69.51]) | 69/110 (62.73%; [53.41, 71.19]) |
| Exact selector only | N/A | N/A | N/A |
| Recorded address + function identity (different endpoint) | 25/110 (22.73%; [15.89, 31.40]) | 49/110 (44.55%; [35.60, 53.86]) | 52/110 (47.27%; [38.19, 56.54]) |

Exact selector recall over all 110 is **not identifiable from these frozen labels**: only four rows contain literal 4-byte selector targets; the remaining 106 lack explicit selector targets. Human function names without canonical argument types do not determine Ethereum selectors. The selector cache stores names and is not a contract-specific typed ABI. Hashing guessed arities or accepting every selector sharing a name would invent labels. N/A is not zero; no Wilson interval exists for an undefined numerator. The recorded 25/49/52 uses address+function identity, including legacy name resolution, and must not be relabeled address+selector.

Address-only uses any explicitly labeled contract address from each row's original `location` map and the saved prediction order. The five failed rows are excluded before the requested N=110 calculation; no failed row was rerun. The 110 records contain 109 unique hashes (SorStaking duplicated), so the displayed intervals are nominal record-level intervals, not 110 independent-transaction guarantees. Each original label file matches its frozen manifest SHA-256.

### Literal-selector subset only — exploratory, n=4 (not representative of 110)

| Match | R@1 | R@3 | R@5 |
|---|---|---|---|
| Address + selector | 0/4 (0.00%; [0.00, 48.99]) | 0/4 (0.00%; [0.00, 48.99]) | 0/4 (0.00%; [0.00, 48.99]) |
| Selector only | 0/4 (0.00%; [0.00, 48.99]) | 0/4 (0.00%; [0.00, 48.99]) | 0/4 (0.00%; [0.00, 48.99]) |

The four exact-selector rows are: `0x06d7e7436414c658a33452d28400799f3637e83930dcec39b3bd065dabc6ef04`, `0x57b589f631f8ff20e2a89a649c4ec2e35be72eaecf155fdfde981c0fec2be5ba`, `0x998f1da472d927e74405b0aa1bbf5c1dbc50d74b39977bed3307ea2ada1f1d3f`, `0xbea605b238c85aabe5edc636219155d8c4879d6b05c48091cf1f7286bd4702ba`. Strict comparisons use only stored `selector`/`function` values with the existing 0x-prefixed, 4-byte rule; no normalization fix is applied.

## Exploratory top-5 miss analysis

A miss means the saved **address+selector** first-hit rank is absent or greater than five. Exactly 24/40 rows miss (C18, D6). Assign one mutually exclusive observed cause per row, in this order:

1. **Not in candidate set**: no exact target pair exists anywhere in the saved list.
2. **Wrong normalization**: an equivalent observed target is rejected solely by representation. None established here.
3. **Address ranked below**: exact pair exists, but even the first candidate for the target address is below five.
4. **Selector mismatch**: the target address is in top-five under a different function selector; the exact pair is lower. This describes mismatching top-five entries, not a fabricated ABI diagnosis.
5. **Other**: remaining cases; none here.

| Primary cause | C | D | Pooled |
|---|---:|---:|---:|
| not in candidate set | 1 | 0 | 1 |
| wrong normalization | 0 | 0 | 0 |
| selector mismatch | 3 | 2 | 5 |
| address ranked below | 14 | 4 | 18 |
| other | 0 | 0 | 0 |
| Total | 18 | 6 | 24 |

Cause attribution is a post-hoc description of stored ranks and candidate identities, not proof of the exploit mechanism or a proposal to fix the system. Twenty-three missed exact pairs are present below rank five. No normalization change is tested or used.

### One line per missed row — exploratory

Ranks are pair / address-only / selector-only; `absent` means no saved match. Candidate count is the complete saved list, not a top-5 truncation.

| Batch / incident | Transaction | Target address / selector | Saved ranks | Candidates | Cause and observed evidence |
|---|---|---|---|---:|---|
| C — Pickle Finance evil jar | `0xe72d4e7ba9b5af0cf2a8cfb1e30fd9f388df0ab3da79790be842bfbed11087b0` | `0x6847259b2b3a4c17e7c43c54409810af48ba5210` / `0xff3f1869` | 9 / 9 / 9 | 111 | **address ranked below** — Exact target pair exists at #9; first target-address candidate is #9, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xe72d4e7ba9b5af0cf2a8cfb1e30fd9f388df0ab3da79790be842bfbed11087b0.json`. |
| C — Rari Capital fake-token lending | `0x171072422efb5cd461546bfe986017d9b5aa427ff1c07ebe8acc064b13a7b7be` | `0x67b66c99d3eb37fa76aa3ed1ff33e8e39f0b9c7a` / `0x2118c75c` | 60 / 9 / 60 | 66 | **address ranked below** — Exact target pair exists at #60; first target-address candidate is #9, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0x171072422efb5cd461546bfe986017d9b5aa427ff1c07ebe8acc064b13a7b7be.json`. |
| C — Poly Network cross-chain manager | `0xb1f70464bd95b774c6ce60fc706eb5f9e35cb5f06e6cfe7c17dcda46ffd59581` | `0x838bf9e95cb12dd76a54c9f9d2e3082eaf928270` / `0xd450e04c` | 14 / 14 / 14 | 14 | **address ranked below** — Exact target pair exists at #14; first target-address candidate is #14, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xb1f70464bd95b774c6ce60fc706eb5f9e35cb5f06e6cfe7c17dcda46ffd59581.json`. |
| C — Yearn yUSDT share-price manipulation | `0x055cec4fa4614836e54ea2e5cd3d14247ff3d61b85aa2a41f8cc876d131e0328` | `0xf013406a0b1d544238083df0b93ad0d2cbe0f65f` / `0x40c10f19` | 52 / 7 / 47 | 62 | **address ranked below** — Exact target pair exists at #52; first target-address candidate is #7, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0x055cec4fa4614836e54ea2e5cd3d14247ff3d61b85aa2a41f8cc876d131e0328.json`. |
| C — Pine Protocol NFT lending repayment | `0xec7523660f8b66d9e4a5931d97ad8b30acc679c973b20038ba4c15d4336b393d` | `0xc3f4659588b13f23e09ec54783a3c407e39ad589` / `0xb1e8f8ef` | absent / absent / absent | 12 | **not in candidate set** — Exact target pair absent from all saved candidates; target address absent from candidates. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xec7523660f8b66d9e4a5931d97ad8b30acc679c973b20038ba4c15d4336b393d.json`. |
| C — Convergence reward distributor | `0x636be30e58acce0629b2bf975b5c3133840cd7d41ffc3b903720c528f01c65d9` | `0x2b083beaac310cc5e190b1d2507038ccb03e7606` / `0x23446652` | 19 / 19 / 13 | 25 | **address ranked below** — Exact target pair exists at #19; first target-address candidate is #19, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0x636be30e58acce0629b2bf975b5c3133840cd7d41ffc3b903720c528f01c65d9.json`. |
| C — Socket vulnerable route arbitrary call | `0xc6c3331fa8c2d30e1ef208424c08c039a89e510df2fb6ae31e5aa40722e28fd6` | `0xcc5fda5e3ca925bd0bb428c8b2669496ee43067e` / `0x7899f9ed` | 9 / 9 / 9 | 12 | **address ranked below** — Exact target pair exists at #9; first target-address candidate is #9, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xc6c3331fa8c2d30e1ef208424c08c039a89e510df2fb6ae31e5aa40722e28fd6.json`. |
| C — Pike Finance proxy initialization | `0xe2912b8bf34d561983f2ae95f34e33ecc7792a2905a3e317fcc98052bce66431` | `0xfc7599cffea9de127a9f9c748ccb451a34d2f063` / `0x4f1ef286` | 6 / 5 / 4 | 7 | **selector mismatch** — Target-address top-5 entries have different selectors (#5 `0xfb5e556c`); exact target pair exists at #6. This is function-rank displacement, not evidence of a malformed selector. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xe2912b8bf34d561983f2ae95f34e33ecc7792a2905a3e317fcc98052bce66431.json`. |
| C — Prisma delegate approval abuse | `0x00c503b595946bccaea3d58025b5f9b3726177bbdc9674e634244135282116c7` | `0x72c590349535ad52e6953744cb2a36b409542719` / `0xc3c854b6` | 41 / 41 / 41 | 63 | **address ranked below** — Exact target pair exists at #41; first target-address candidate is #41, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0x00c503b595946bccaea3d58025b5f9b3726177bbdc9674e634244135282116c7.json`. |
| C — Resupply reUSD oracle manipulation | `0xffbbd492e0605a8bb6d490c3cd879e87ff60862b0684160d08fd5711e7a872d3` | `0x6e90c85a495d54c6d7e1f3400fef1f6e59f86bd6` / `0xd6bda0c0` | 87 / 40 / 87 | 110 | **address ranked below** — Exact target pair exists at #87; first target-address candidate is #40, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xffbbd492e0605a8bb6d490c3cd879e87ff60862b0684160d08fd5711e7a872d3.json`. |
| C — LlamaLend Convex strategy share accounting | `0x2ff7c23dca7e9a86c70004696802cbd37d6a77fc4f3e02522b16617045b764f6` | `0x75b7db3e11138134fe4744553b5e5e3d6546d289` / `0xba087652` | 78 / 62 / 49 | 91 | **address ranked below** — Exact target pair exists at #78; first target-address candidate is #62, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0x2ff7c23dca7e9a86c70004696802cbd37d6a77fc4f3e02522b16617045b764f6.json`. |
| C — ParaSpace Ape collateral borrowing | `0xe3f0d14cfb6076cabdc9057001c3fafe28767a192e88005bc37bd7d385a1116a` | `0x638a98bbb92a7582d07c52ff407d49664dc8b3ee` / `0x1d5d7237` | 11 / 8 / 11 | 139 | **address ranked below** — Exact target pair exists at #11; first target-address candidate is #8, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xe3f0d14cfb6076cabdc9057001c3fafe28767a192e88005bc37bd7d385a1116a.json`. |
| C — Leverage SIR vault initialization | `0xa05f047ddfdad9126624c4496b5d4a59f961ee7c091e7b4e38cee86f1335736f` | `0xb91ae2c8365fd45030aba84a4666c4db074e53e7` / `0x3aa88670` | 51 / 11 / 51 | 60 | **address ranked below** — Exact target pair exists at #51; first target-address candidate is #11, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xa05f047ddfdad9126624c4496b5d4a59f961ee7c091e7b4e38cee86f1335736f.json`. |
| C — Silo leverage helper arbitrary borrow | `0x1f15a193db3f44713d56c4be6679b194f78c2bcdd2ced5b0c7495b7406f5e87a` | `0x160287e2d3fdcde9e91317982fc1cc01c1f94085` / `0xd5164184` | 44 / 21 / 43 | 56 | **address ranked below** — Exact target pair exists at #44; first target-address candidate is #21, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0x1f15a193db3f44713d56c4be6679b194f78c2bcdd2ced5b0c7495b7406f5e87a.json`. |
| C — UniLend health-factor accounting | `0x44037ffc0993327176975e08789b71c1058318f48ddeff25890a577d6555b6ba` | `0x7f2e24d2394f2bdabb464b888cb02eba6d15b958` / `0x8dee9460` | 41 / 2 / 41 | 59 | **selector mismatch** — Target-address top-5 entries have different selectors (#2 `0xabdb31e4`, #3 `0xe96466d0`); exact target pair exists at #41. This is function-rank displacement, not evidence of a malformed selector. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0x44037ffc0993327176975e08789b71c1058318f48ddeff25890a577d6555b6ba.json`. |
| C — Blueberry market entry accounting | `0xf0464b01d962f714eee9d4392b2494524d0e10ce3eb3723873afd1346b8b06e4` | `0xffadb0bba4379dfabfb20ca6823f6ec439429ec2` / `0xc2998238` | 59 / 5 / 59 | 77 | **selector mismatch** — Target-address top-5 entries have different selectors (#5 `0x929fe9a1`); exact target pair exists at #59. This is function-rank displacement, not evidence of a malformed selector. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xf0464b01d962f714eee9d4392b2494524d0e10ce3eb3723873afd1346b8b06e4.json`. |
| C — 1inch Fusion settlement calldata corruption | `0x62734ce80311e64630a009dd101a967ea0a9c012fabbfce8eac90f0f4ca090d6` | `0xa88800cd213da5ae406ce248380802bd53b47647` / `0x0965d04b` | 12 / 8 / 12 | 14 | **address ranked below** — Exact target pair exists at #12; first target-address candidate is #8, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0x62734ce80311e64630a009dd101a967ea0a9c012fabbfce8eac90f0f4ca090d6.json`. |
| C — ParaSwap stale DAI approval drain | `0xed5f932a136ef95b943951ce103b3edbe600bf2c2607edff7b6ea9ada35ca300` | `0xdef171fe48cf0115b1d80b88dc8eab59176fee57` / `0x54e3f31b` | 8 / 8 / 6 | 16 | **address ranked below** — Exact target pair exists at #8; first target-address candidate is #8, outside top-5. Saved list: `reports/new_batches/batchC/phase2/run_20261018T111234Z/candidates/0xed5f932a136ef95b943951ce103b3edbe600bf2c2607edff7b6ea9ada35ca300.json`. |
| D — N00d | `0x8037b3dc0bf9d5d396c10506824096afb8125ea96ada011d35faa89fa3893aea` | `0x3561081260186e69369e6c32f280836554292e08` / `0xa59f3e0c` | 6 / 6 / 6 | 19 | **address ranked below** — Exact target pair exists at #6; first target-address candidate is #6, outside top-5. Saved list: `reports/new_batches/batchD/phase2/candidates/0x8037b3dc0bf9d5d396c10506824096afb8125ea96ada011d35faa89fa3893aea.json`. |
| D — ERC20 Token Bank | `0x578a195e05f04b19fd8af6358dc6407aa1add87c3167f053beb990d6b4735f26` | `0x765b8d7cd8ff304f796f4b6fb1bcf78698333f6d` / `0xfcb5d44d` | 51 / 51 / 51 | 64 | **address ranked below** — Exact target pair exists at #51; first target-address candidate is #51, outside top-5. Saved list: `reports/new_batches/batchD/phase2/candidates/0x578a195e05f04b19fd8af6358dc6407aa1add87c3167f053beb990d6b4735f26.json`. |
| D — Bao | `0xdd7dd68cd879d07cfc2cb74606baa2a5bf18df0e3bda9f6b43f904f4f7bbdfc1` | `0xb0f8fe96b4880adbdede0ddf446bd1e7ef122c4e` / `0x852a12e3` | 147 / 57 / 137 | 199 | **address ranked below** — Exact target pair exists at #147; first target-address candidate is #57, outside top-5. Saved list: `reports/new_batches/batchD/phase2/candidates/0xdd7dd68cd879d07cfc2cb74606baa2a5bf18df0e3bda9f6b43f904f4f7bbdfc1.json`. |
| D — Floor DAO | `0x1274b32d4dfacd2703ad032e8bd669a83f012dde9d27ed92e4e7da0387adafe4` | `0x759c6de5bca9ade8a1a2719a31553c4b7de02539` / `0x990966d5` | 15 / 3 / 15 | 30 | **selector mismatch** — Target-address top-5 entries have different selectors (#3 `0xd866c9d8`); exact target pair exists at #15. This is function-rank displacement, not evidence of a malformed selector. Saved list: `reports/new_batches/batchD/phase2/candidates/0x1274b32d4dfacd2703ad032e8bd669a83f012dde9d27ed92e4e7da0387adafe4.json`. |
| D — Jump Farm | `0x6189ad07894507d15c5dff83f547294e72f18561dc5662a8113f7eb932a5b079` | `0x05999eb831ae28ca920ce645a5164fbdb1d74fe9` / `0x21d0af34` | 11 / 1 / 11 | 40 | **selector mismatch** — Target-address top-5 entries have different selectors (#1 `0xadc9772e`); exact target pair exists at #11. This is function-rank displacement, not evidence of a malformed selector. Saved list: `reports/new_batches/batchD/phase2/candidates/0x6189ad07894507d15c5dff83f547294e72f18561dc5662a8113f7eb932a5b079.json`. |
| D — DePay Router | `0x9a036058afb58169bfa91a826f5fcf4c0a376e650960669361d61bef99205f35` | `0xae60ac8e69414c2dc362d0e6a03af643d1d85b92` / `0xb7d29a35` | 29 / 29 / 29 | 40 | **address ranked below** — Exact target pair exists at #29; first target-address candidate is #29, outside top-5. Saved list: `reports/new_batches/batchD/phase2/candidates/0x9a036058afb58169bfa91a826f5fcf4c0a376e650960669361d61bef99205f35.json`. |

Pine Protocol cross-check: the cached C raw callTracer tree contains zero `to` calls to the frozen target address and zero calls using its target selector. This supports observed target absence; the frozen files do not establish whether annotation/transaction selection, execution context, or capture coverage explains that absence. No replacement label is inferred.

## Why address-only exceeds address+selector — code and observed rows

The address-only hit set is a superset by construction. `scripts/research/batchC_phase2.py:471–485` reads one address and one strict 4-byte selector from each candidate; lines479–480 accept any candidate at the target address, while lines483–484 require the same list item to match both target address and target selector. Lines477–478 accept only a 0x-prefixed, ten-character selector and perform no name-to-selector inference. D uses this identical comparator at `scripts/research/batchD_phase2.py:229`. This is a deliberate difference in endpoint strictness, not evidence of a normalization bug.

The lists rank **functions at addresses**, not one item per contract. In `faultseeker/function_analysis/function_ranker.py:303–310`, ordering uses call-path concentration, terminal fanout, depth and count. Lines321–331 emit an independent function/address candidate and attach a selector only when the function is already a 4-byte hex identity (line326). None of these keys knows the expected vulnerable selector. Thus a different function at the correct address can rank well while the labeled function ranks poorly. The RPC route preserves observed calldata selectors: `faultseeker/utils/rpc_provider.py:875` takes input[:10]; `faultseeker/data_collection/txn_sequencer.py:21–38` carries the selector into the legacy function field. D preserves raw input[:10] in its additional trace view at `scripts/research/batchD_phase2.py:64–75`, then prepares/ranks candidates at lines220–221 before any target comparison.

| Batch | Extra address-only hits @1 | @3 | @5 |
|---|---:|---:|---:|
| C | 2 | 1 | 3 |
| D | 2 | 3 | 2 |
| Pooled | 4 | 4 | 5 |

Concrete @1 differences: C Balancer and tCDP each have target-address rank1 versus exact-pair rank2; D Jump Farm is address rank1 versus pair11, and Unicly NFT is address rank1 versus pair4. At top-five, C Pike is address5/pair6, UniLend address2/pair41, Blueberry address5/pair59; D Floor DAO address3/pair15 and Jump Farm address1/pair11. These five observed displacements explain the entire pooled top-five difference (21 address hits versus16 pair hits). No presumed selector spelling fix or proxy heuristic is needed to explain the gap.

## Input fingerprints and preservation

Only `reports/new_batches/pooled_CD_REPORT.md` was written. No source or frozen artifact was changed; no score entry point or ranker was invoked; no tests, installs, external calls, commits or pushes were performed. Every file under frozen batchC/ and batchD/ plus the original manifest and selected label files was SHA-256 checked before and after report generation.

| Input | SHA-256 |
|---|---|
| `reports/new_batches/batchC/phase2/run_20261018T111234Z/scoring.json` | `97581c03a24434d92809d5acab06d9114c4ee5e117898b14a3e25692c2cd5697` |
| `reports/new_batches/batchC/batchC_candidates.json` | `fb3bf4f823b1307f18020020a9400095f601f02830815ed3fc0e0a2990a61f85` |
| `reports/new_batches/batchD/phase2/scoring.json` | `fcb1ffaa1ab99e4123713b378bb3cdf3c6e82c871c7a79f7efec8d8111f5066a` |
| `reports/new_batches/batchD/batchD_candidates.json` | `8ee43216455de81f2bddd515e6b2e3141edf4e21a6bb0b710726aff6780a6f99` |
| `reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json` | `0d8fa473b4abb83024c11300572c1fc3a2eaf4f63b90fc152abe743c01c75ee5` |

Original selected-label filename→SHA256 map digest (canonical compact sorted JSON): `0c7303fd993b409d69990eb448ffa76c855f16c3537b84cacf999f7145e7758f`. Candidate lists reside under each scoring directory's `candidates/`; all40 were read without changing their order. Raw Pine evidence: `reports/new_batches/batchC/phase2/run_20261018T111234Z/trace_raw/0xec7523660f8b66d9e4a5931d97ad8b30acc679c973b20038ba4c15d4336b393d.json`.
