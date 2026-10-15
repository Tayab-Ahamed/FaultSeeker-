# Canonical evidence review: complete 31-claim registry

13 VERIFIED within existing implementation/sample scopes; 18 UNVERIFIABLE publication outcomes after canonical review. No claim promoted from inference, literal reports, proxy models or fixtures.

Detailed numbers and scope: [paper versus repository map](PAPER_VS_REPO.md). Exact cached bytes and Git identities: [manifest](manifest.json).

| Claim | Title | Status | Canonical verdict | Decision commit |
|---|---|---|---|---|
| 1 | Open source release | VERIFIED | Prior verification scope unchanged | `164e65e393fe800f087de8c70661d55abfd3b9b2` |
| 2 | 201 original tests pass | VERIFIED | Prior verification scope unchanged | `af5eabef3266f097d83724497b31e68f36f3b89c` |
| 3 | Authentic 246-row cohort | UNVERIFIABLE | COUNT-EXISTS-AUTHENTICITY-UNVERIFIED | `c0ae6c5e796b2d612e64a6f4805c893846ad98c6` |
| 4 | Real transactions, two independent sources, annotations | UNVERIFIABLE | PARTIAL-PROVENANCE-RECOVERED | `a689f78e62945b77b21b2ec074ab612af76bd42b` |
| 5 | Ten chains and Ethereum 47.6% | UNVERIFIABLE | CONTRADICTED-FROZEN-CSV | `54959e4cbe20bffd0716735084ad401fd78d9583` |
| 6 | More than 80 vulnerability labels | UNVERIFIABLE | STRINGS-COUNTED-NOT-ADJUDICATED | `9bcbfd1351b49dfe39bef74e58f870aed522c4d4` |
| 7 | Class proportions 6.5/33.3/32.5/27.6% | UNVERIFIABLE | CONTRADICTED-FROZEN-CSV | `c9b71291b466eb027f50cd453fe997e2ba2d71e2` |
| 8 | 18 reentrant incidents among 246 | UNVERIFIABLE | CONTRADICTED-LABEL-COUNT | `574de8d9651bbc3cf82d68ee7e89215eeff1424e` |
| 9 | Storage-aware detector, guards and delegatecall | VERIFIED | Prior verification scope unchanged | `0f4f630c5676505a894d8c1e43c392566e5af230` |
| 10 | Five storage signal weights | VERIFIED | Prior verification scope unchanged | `97d18113487f51a0a15ed10fcfb08cf426aa67d0` |
| 11 | Five confidence tiers | VERIFIED | Prior verification scope unchanged | `ecb86ccb3219a814f32e5fe8d804fa2105882cab` |
| 12 | Three structural signals, .75 penalty, .80 cap | VERIFIED | Prior verification scope unchanged | `8814f6be18117572b47d9d853a1c1efe7628668d` |
| 13 | Detector precision/recall/F1 and baselines | UNVERIFIABLE | PUBLISHED-METRICS-UNSUPPORTED | `a2f891c9b0e883f1a2d58d2764beddb2d5262134` |
| 14 | 17/29 percentage-point gains | UNVERIFIABLE | PUBLISHED-GAINS-UNSUPPORTED | `bc0841022265818b34997c3120a498b1c3da7be6` |
| 15 | Compound case study | UNVERIFIABLE | CASE-NARRATIVE-RECOVERED-HASH-MISSING | `87c79d1db54afe4d5b58733ca33c45c12bcea61f` |
| 16 | Query routing with theta gate | VERIFIED | Prior verification scope unchanged | `b1a9e6ef591c721a6ae836c6f89ec182635952de` |
| 17 | Six provider families | UNVERIFIABLE | LIVE-CONFORMANCE-STILL-INCOMPLETE | `986a11f589db79eb8c654c945e1627ed8eebbed1` |
| 18 | 58% cost savings, 100 transactions, quality/rank bounds | UNVERIFIABLE | 58-PERCENT-OVERALL-CONTRADICTED | `e213c2782caadc4aabba66839f75ebd2b2efa41f` |
| 19 | Stage 1 makes no model calls | VERIFIED | Prior verification scope unchanged | `9bf99a4463340cf3f66f18509cb23e7d17a2c569` |
| 20 | BENIGN skip, EXPLOIT lock and UNCERTAIN escalation | VERIFIED | Prior verification scope unchanged | `ad8ab927b8496e506ccb6ecd8942dd6449f76e88` |
| 21 | 40% benign prefilter and latency reduction | UNVERIFIABLE | RATE-UNMEASURED | `885020a306d56b5fc7f7272e3f93cbde8a939d2c` |
| 22 | Multi-agent function localization | UNVERIFIABLE | HISTORICAL-AGGREGATE-RECOVERED | `d7519904f923998b91b2cea72b3e12fdd5f54144` |
| 23 | Equation 4 confidence scoring | VERIFIED | Prior verification scope unchanged | `2ed07865650d10a464341cbf7b1d2cd0f782dcf2` |
| 24 | Evidence cards and two HITL checkpoints, five guidance types | VERIFIED | Prior verification scope unchanged | `ec65b942cdc215144be9047ef3e8bcf0e1224736` |
| 25 | RPC EMA, LRU, TTL, breakers and batching | UNVERIFIABLE | CAPABILITY-DECLARATIONS-NOT-LIVE-PROOF | `6e3e2acce61e5fd2f4a717eaeb9b6b94399d34da` |
| 26 | Foundry replay extracts SLOAD and SSTORE | VERIFIED | Prior verification scope unchanged | `5a5c4b8d7d17101881b4a897986c51d6100160f2` |
| 27 | 23% WAF challenge bypass | UNVERIFIABLE | RATE-UNSUPPORTED | `adc3b2816f2c2ccf1e486281b778042ac712cbc7` |
| 28 | Table VI category averages | UNVERIFIABLE | NO-PRODUCTION-SCORE-VECTORS | `9c780471292ce93a1da782d51b5192565045a719` |
| 29 | Simulated guidance on 20 transactions, 68→81% | UNVERIFIABLE | GUIDANCE-RESULT-UNSUPPORTED | `22d316813c057e565dc355d1d3a119a469348ab4` |
| 30 | Reproduction scripts | UNVERIFIABLE | PARTIAL-REPRODUCTION-NOT-PAPER-REPLICATION | `7c10f725e61372939bf1dbd53cf06572de817ff3` |
| 31 | Repository layout/runtime compatibility | VERIFIED | Prior verification scope unchanged | `414e1a3fa3ebbe07f51de6678978138f751344b7` |

## Validation

- Every reopened decision has its own commit, a full-suite pre-commit gate and a full-suite post-commit gate. Exact commits and SHA-256-bound compressed JUnit files are in `verification.json`.
- 367 passed, 1 skipped at each completed gate. The single skip is the explicitly opt-in live historical replay; the recorded historical replay and local compiled execution checks pass.
- All 201 original tests pass, their source digests unchanged. Strict closure verifies every evidence digest and all 31 terminal decisions; it does not mean all paper claims are true.
- Uploaded paper hash unchanged. No model weights, thresholds, current benchmark rows or paper text modified in this review.
- New paid API/RPC requests:0; new paid spend:$0. Cumulative conservative booked spend:$0.809168/$10; ledger unchanged.
- Canonical remote fetched; no merge, checkout of upstream, push or PR. Kluster local waiver continues; full AGENTS.md review must resume before any push/PR.

## Principal corrections

- A 246-row historical CSV DOES exist: 246 unique parsed records, 248 physical data lines including two blanks, 15 malformed hashes, 8 chains. The claimed authenticity and 10-chain study remain unsupported.
- Original 115 GT files (April 3) and 48 October reconstructions are separately cached. Original files cover 114 unique transaction hashes; duplicate SorStaking affects independence of localization targets.
- .8593 [.8223,.8950] and .7586 [.7071,.8040] reproduce as distinct historical feature-harness runs. They are not TableV SSTORE or live LLM results. The newer stored -TIG row does not reproduce: observed .6531 versus recorded .6565.
- The older .8593 run has a degenerate benign control population: 1000 rows, one distinct feature vector. See strict_control_audit.json; reproduction is not validation of study design.
- Localization6.09% is a recovered aggregate (7/115 targets), with no raw rankings tracked in any of53 reachable canonical commits. It cannot verify68->81% guidance.
- Overall35% is modeled arithmetic;58.3% applies only to Tier2. Real measured savings, TableV metrics, TableVI component means and guidance effect remain unavailable.
