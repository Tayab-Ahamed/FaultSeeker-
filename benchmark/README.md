# Benchmark Classification — FaultSeeker++

## Overview

This benchmark dataset supports the **FaultSeeker++** research framework for AI-powered blockchain transaction fault localization. It has been expanded from the original FaultSeeker baseline to cover **8 EVM-compatible chains** with transactions spanning **2023–2026**.

| Metric | Original | **Expanded (v2)** |
|--------|----------|-------------------|
| Total Transactions | 115 | **~246** |
| Chains Covered | 2 (ETH, BSC) | **8 (ETH, BSC, Arbitrum, Optimism, Base, Polygon, Avalanche, zkSync)** |
| Year Range | 2021–2023 | **2021–2026** |
| Unique Vuln Types | 65 | **80+** |

---

## Chain Distribution

| Chain | Entries | Notable Anchors |
|-------|---------|-----------------|
| **Ethereum (ETH)** | ~135 | Penpie reentrancy ($27M), UwuLend oracle ($19M), Radiant precision ($4.5M), ResupplyFi inflation ($9.6M), SIR.trading storage collision ($355K), BalancerV2 precision ($120M), GMX reentrancy ($41M) |
| **BSC** | ~25 | FourMeme logic flaw ($183K), MARA price manip, Bankroll ($234K) |
| **Arbitrum** | ~15 | GMX V1 reentrancy ($41M, `0x03182...`), Radiant Capital rounding (`0x1ce7e...`), DeltaPrime input validation |
| **Optimism** | ~15 | ResupplyFi bypass, multiple flash loan + access control cases |
| **Base** | ~15 | CompoundFork flash loan (`0x6ab5b...`), oracle + reentrancy cases |
| **Polygon** | ~11 | 0VIX oracle flash loan ($2M, `0x10f2c...`), GAMEE access control |
| **Avalanche** | ~8 | Platypus Finance logic flaw ($8.5M, `0x1266a...`), DeltaPrime ($12.9K) |
| **zkSync** | ~5 | EraLend read-only reentrancy ($3.4M), zkSync airdrop access control ($5M), Venus donation attack ($717K) |

---

## Year Coverage

| Year | Entries | Source |
|------|---------|--------|
| 2021–2022 | ~45 | Original FaultSeeker baseline |
| 2023 | ~70 | Original baseline + DeFiHackLabs 2023 |
| 2024 | ~81 | DeFiHackLabs 2024 README (ETH, BSC, Arbitrum, Base, Avalanche) |
| 2025–2026 | ~50 | DeFiHackLabs 2025 README + PeckShield/BlockSec/SlowMist verified |

---

## Classification Frameworks

### 1. SWC Registry (Smart Contract Weakness Classification)
- **Version**: SWC-100 through SWC-136
- **Reference**: https://swcregistry.io/

### 2. DASP Top 10 (Decentralized Application Security Project)
- **Version**: 2018
- **Reference**: https://dasp.co/

---

## Classification Statistics (v2 Expanded)

```
Total Transactions Analyzed : ~246
Unique Vulnerability Types  : 80+
Chains Covered              : 8
Frameworks Used             : 2 (SWC Registry, DASP Top 10)
```

### Top Vulnerability Types

| Rank | Vulnerability Type | Count (approx.) |
|------|--------------------|-----------------|
| 1 | Price Manipulation / Oracle | ~48 |
| 2 | Access Control | ~38 |
| 3 | Business Logic Flaw | ~35 |
| 4 | Reentrancy | ~28 |
| 5 | Flash Loan Attack | ~26 |
| 6 | Arithmetic Issues (precision, overflow) | ~24 |
| 7 | Rug Pull | ~15 |
| 8 | Logic Flaw | ~14 |
| 9 | Incorrect Input Validation | ~10 |
| 10 | Donation / Inflation Attack | ~6 |

### SWC Registry Coverage (v2)

```
Total SWC Categories        : 36
Categories with Entries     : 14
Coverage Rate               : 38.9%
```

Top SWC Categories:
1. **SWC-105** (Unprotected Ether Withdrawal): ~38 entries
2. **SWC-107** (Reentrancy): ~28 entries
3. **SWC-123** (Requirement Violation / Logic): ~35 entries
4. **SWC-101** (Integer Overflow/Underflow): ~24 entries
5. **SWC-114** (Transaction Order Dependence): ~4 entries
6. **SWC-124** (Write to Arbitrary Storage): ~4 entries

### DASP Top 10 Coverage (v2)

```
Total DASP Categories       : 10
Categories with Entries     : 7
Coverage Rate               : 70.0%
```

Top DASP Categories:
1. **Unknown Unknowns** (Logic Issues): ~35 entries
2. **Access Control**: ~38 entries
3. **Arithmetic Issues**: ~24 entries
4. **Reentrancy**: ~28 entries
5. **Front-Running**: ~4 entries

---

## Complexity Distribution

| Complexity Class | Description | Approx. Count |
|-----------------|-------------|---------------|
| Simple | ≤5 functions, ≤3 suspicious | ~45 |
| Moderate | 6–30 functions, 3–6 suspicious | ~110 |
| Complex | 31–100 functions, 6–10 suspicious | ~72 |
| Exceptionally Complex | 100+ functions, 10+ suspicious | ~19 |

---

## Key Sources

| Source | URL |
|--------|-----|
| DeFiHackLabs 2024 | https://github.com/SunWeb3Sec/DeFiHackLabs/blob/main/past/2024/README.md |
| DeFiHackLabs 2025 | https://github.com/SunWeb3Sec/DeFiHackLabs/blob/main/past/2025/README.md |
| BlockSec Phalcon | https://phalcon.blocksec.com/explorer/security-incidents |
| PeckShield | https://x.com/peckshield |
| SlowMist | https://x.com/SlowMist_Team |
| CertiK | https://x.com/CertiKAlert |
| TenArmor | https://x.com/TenArmorAlert |
| Rekt News | https://rekt.news |

---

## Validation

Run the validation script to verify dataset integrity:

```bash
cd benchmark
python validate_dataset.py
```

Expected output: **~246 entries, 0 duplicates, 8 chains**.

---

*Last updated: April 2026 — FaultSeeker++ v2 Dataset Expansion (Gap 7)*
