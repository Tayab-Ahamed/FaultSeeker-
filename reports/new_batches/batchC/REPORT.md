# Batch C phase 1 report

**Frozen: 30 distinct Ethereum-mainnet incidents, DeFiHackLabs-sourced.**

This phase performed only public raw-file collection and local source screening. No RPC, node tracing, transaction lookup, scoring, ranker invocation, Batch B result inspection, or result-file change was performed.

Pinned source commit: `7363f76db51f0fea97f8e659b20ee8bdc5fbca25`
Frozen canonical JSON SHA-256: `3ab15ab445e00613b1fb7a48e32c94f22f7a03f451182ff2fac5912b3aaa2dc2`
Fetched source files retained in the manifest: **120**

## Counts by vulnerability category

| Category | Count |
| --- | ---: |
| Access Control | 1 |
| Access Control / Unlimited Mint | 1 |
| Arbitrary Call / Vault Accounting | 1 |
| Bridge / Access Control | 1 |
| Bridge / Arbitrary Call | 2 |
| DEX / Calldata Validation | 1 |
| DEX / Deflationary Token | 1 |
| DEX Aggregator / Approval Abuse | 1 |
| Lending / Accounting | 1 |
| Lending / Arbitrary Call | 1 |
| Lending / Delegate Approval | 1 |
| Lending / Fake Token | 1 |
| Lending / Health Factor | 1 |
| Lending / Market Accounting | 1 |
| Lending / Oracle Manipulation | 2 |
| Lending / Share Price Manipulation | 1 |
| NFT Lending / Collateral Accounting | 1 |
| NFT Lending / Repayment Accounting | 1 |
| Options / Accounting | 1 |
| Price Manipulation / Vault Accounting | 1 |
| Proxy / Access Control | 1 |
| Reentrancy / State Accounting | 1 |
| Reward Accounting / Token Inflation | 1 |
| Token / Allowance Validation | 1 |
| Token / Integer Overflow | 1 |
| Token / Signature Validation | 1 |
| Vault / Price Manipulation | 1 |
| Vault / Share Accounting | 1 |

## Counts by incident year

| Year | Count |
| --- | ---: |
| 2017 | 1 |
| 2018 | 3 |
| 2020 | 2 |
| 2021 | 5 |
| 2022 | 1 |
| 2023 | 4 |
| 2024 | 4 |
| 2025 | 10 |

## Exclusions

| File | Incident | Reason |
| --- | --- | --- |
| `src/test/2017-11/Parity_kill_exp.sol` | Parity_kill_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2020-08/Opyn_exp.sol` | Opyn_exp | Target signature is imported rather than locally source-resolved in the fetched PoC. |
| `src/test/2020-09/bzx_exp.sol` | bzx_exp | Target signature is imported rather than locally source-resolved in the fetched PoC. |
| `src/test/2020-10/HarvestFinance_exp.sol` | HarvestFinance_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2020-12/Cover_exp.sol` | Cover_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2021-01/Sushi_Badger_Digg_exp.sol` | Sushi_Badger_Digg_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2021-03/dodo_flashloan_exp.sol` | dodo_flashloan_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2021-04/Uranium_exp.sol` | Uranium_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2021-05/Spartan_exp.sol` | Spartan_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2021-05/ValueDefi_exp.sol` | ValueDefi_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2021-06/88mph_exp.sol` | 88mph_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2021-06/Eleven_exp.sol` | Eleven_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2021-06/SafeDollar_exp.sol` | SafeDollar_exp | PoC forks polygon, not Ethereum mainnet. |
| `src/test/2021-06/xWin_exp.sol` | xWin_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2021-07/Chainswap_exp1.sol` | Chainswap_exp1 | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2021-07/Levyathan_exp.sol` | Levyathan_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2021-08/WaultFinance_exp.sol` | WaultFinance_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2021-09/Nimbus_exp.sol` | Nimbus_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2021-09/NowSwap_exp.sol` | NowSwap_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2021-10/IndexedFinance_exp.sol` | IndexedFinance_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2021-12/Grim_exp.sol` | Grim_exp | PoC forks fantom, not Ethereum mainnet. |
| `src/test/2021-12/NerveBridge_exp.sol` | NerveBridge_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2021-12/Visor_exp.sol` | Visor_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-01/Anyswap_exp.sol` | Anyswap_exp | Target signature is imported rather than locally source-resolved in the fetched PoC. |
| `src/test/2022-02/Meter_exp.sol` | Meter_exp | PoC forks moonriver, not Ethereum mainnet. |
| `src/test/2022-03/Agave_exp.sol` | Agave_exp | PoC forks gnosis, not Ethereum mainnet. |
| `src/test/2022-03/Auctus_exp.sol` | Auctus_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-03/CompoundTusd_exp.sol` | CompoundTusd_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-03/Fantasm_exp.sol` | Fantasm_exp | PoC forks fantom, not Ethereum mainnet. |
| `src/test/2022-03/OneRing_exp.sol` | OneRing_exp | PoC forks fantom, not Ethereum mainnet. |
| `src/test/2022-03/Paraluni_exp.sol` | Paraluni_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-03/Revest_exp.sol` | Revest_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-03/Ronin_exp.sol` | Ronin_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-03/TreasureDAO_exp.sol` | TreasureDAO_exp | PoC forks arbitrum, not Ethereum mainnet. |
| `src/test/2022-04/Beanstalk_exp.sol` | Beanstalk_exp | Target signature is imported rather than locally source-resolved in the fetched PoC. |
| `src/test/2022-04/Elephant_Money_exp.sol` | Elephant_Money_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-04/Gym_1_exp.sol` | Gym_1_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-04/Rari_exp.sol` | Rari_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-04/Saddle_exp.sol` | Saddle_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-05/FortressLoans_exp.sol` | FortressLoans_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-05/HackDao_exp.sol` | HackDao_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-06/InverseFinance_exp.sol` | InverseFinance_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-06/Optimism_exp.sol` | Optimism_exp | PoC forks optimism, not Ethereum mainnet. |
| `src/test/2022-06/XCarnival_exp.sol` | XCarnival_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2022-07/FlippazOne_exp.sol` | FlippazOne_exp | No explicit transaction hash is present in the fetched PoC source. |
| `src/test/2022-07/Quixotic_exp.sol` | Quixotic_exp | PoC forks optimism, not Ethereum mainnet. |
| `src/test/2022-08/EGD_Finance_exp.sol` | EGD_Finance_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-08/ReaperFarm_exp.sol` | ReaperFarm_exp | PoC forks fantom, not Ethereum mainnet. |
| `src/test/2022-09/BXH_exp.sol` | BXH_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-10/BabySwap_exp.sol` | BabySwap_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-10/TransitSwap_exp.sol` | TransitSwap_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2022-11/DFX_exp.sol` | DFX_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2022-11/Kashi_exp.sol` | Kashi_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2022-12/Lodestar_exp.sol` | Lodestar_exp | PoC forks arbitrum, not Ethereum mainnet. |
| `src/test/2023-01/BonqDAO_exp.sol` | BonqDAO_exp | Raw file was not present at the pinned commit (HTTP fetch failed); no candidate was synthesized. |
| `src/test/2023-02/Platypus_exp.sol` | Platypus_exp | PoC forks avalanche, not Ethereum mainnet. |
| `src/test/2023-02/dForce_exp.sol` | dForce_exp | PoC forks arbitrum, not Ethereum mainnet. |
| `src/test/2023-03/Euler_exp.sol` | Euler_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2023-04/Allbridge_exp.sol` | Allbridge_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2023-04/Sentiment_exp.sol` | Sentiment_exp | PoC forks arbitrum, not Ethereum mainnet. |
| `src/test/2023-05/Jimbo_exp.sol` | Jimbo_exp | PoC forks arbitrum, not Ethereum mainnet. |
| `src/test/2023-06/MidasCapitalXYZ_exp.sol` | MidasCapitalXYZ_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2023-07/ArcadiaFi_exp.sol` | ArcadiaFi_exp | PoC forks optimism, not Ethereum mainnet. |
| `src/test/2023-07/Platypus02_exp.sol` | Platypus02_exp | PoC forks avalanche, not Ethereum mainnet. |
| `src/test/2023-08/Exactly_exp.sol` | Exactly_exp | PoC forks optimism, not Ethereum mainnet. |
| `src/test/2023-08/Zunami_exp.sol` | Zunami_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2023-09/DEXRouter_exp.sol` | DEXRouter_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2023-10/MaestroRouter2_exp.sol` | MaestroRouter2_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2023-10/StarsArena_exp.sol` | StarsArena_exp | PoC forks avalanche, not Ethereum mainnet. |
| `src/test/2023-11/KyberSwap_exp.eth.1.sol` | KyberSwap_exp.eth.1 | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2023-11/Raft_exp.sol` | Raft_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2024-01/RadiantCapital_exp.sol` | RadiantCapital_exp | PoC forks arbitrum, not Ethereum mainnet. |
| `src/test/2024-02/Seneca_exp.sol` | Seneca_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2024-03/UnizenIO_exp.sol` | UnizenIO_exp | Target signature is imported rather than locally source-resolved in the fetched PoC. |
| `src/test/2024-04/PikeFinance_exp.sol` | PikeFinance_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2024-04/HedgeyFinance_exp.sol` | HedgeyFinance_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2024-05/PredyFinance_exp.sol` | PredyFinance_exp | PoC forks arbitrum, not Ethereum mainnet. |
| `src/test/2024-06/Velocore_exp.sol` | Velocore_exp | PoC forks linea, not Ethereum mainnet. |
| `src/test/2024-07/Minterest_exp.sol` | Minterest_exp | PoC forks mantle, not Ethereum mainnet. |
| `src/test/2024-08/Convergence_exp.sol` | Convergence_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2024-09/Shezmu_exp.sol` | Shezmu_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2024-10/MorphoBlue_exp.sol` | MorphoBlue_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2024-11/DeltaPrime_exp.sol` | DeltaPrime_exp | PoC forks arbitrum, not Ethereum mainnet. |
| `src/test/2024-12/Pledge_exp.sol` | Pledge_exp | PoC forks bsc, not Ethereum mainnet. |
| `src/test/2025-01/ODOS_exp.sol` | ODOS_exp | PoC forks base, not Ethereum mainnet. |
| `src/test/2025-02/Bybit_exp.sol` | Bybit_exp | Public PoC contains private-key material; it was not retained in the repository or selected for Batch C. |
| `src/test/2025-03/Euler_exp.sol` | Euler_exp | Raw file was not present at the pinned commit (HTTP fetch failed); no candidate was synthesized. |
| `src/test/2025-04/ImpermaxV3_exp.sol` | ImpermaxV3_exp | PoC forks base, not Ethereum mainnet. |
| `src/test/2025-05/UsualMoney_exp.sol` | UsualMoney_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2025-06/ResupplyFi_exp.sol` | ResupplyFi_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |
| `src/test/2025-08/SizeCredit_exp.sol` | SizeCredit_exp | Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted. |

The exclusion scan used 115 local ground-truth JSON hashes, 110 local provider-pinned benchmark hashes, all 40 Batch A hashes, and all 20 Batch B hashes. No frozen Batch C transaction intersected those sets. Batch B results and ranker output were not read or used for selection.

## Later verification gate

When Batch C is eventually opened, use the same gate as Batch B: a transaction is verified only when the returned transaction hash and receipt transaction hash equal the frozen hash, transaction and receipt block numbers match, the transaction is not pending, and a valid full Ethereum trace is available. Any mismatch excludes the row before scoring.
