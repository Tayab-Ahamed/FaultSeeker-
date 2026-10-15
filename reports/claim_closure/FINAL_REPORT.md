# FaultSeeker++: all 31 paper claims reviewed

Date: 2026-10-15 (client session). Branch: `paper-claims-verified`.

**13 VERIFIED; 18 UNVERIFIABLE. No pending or unreviewed claims.**

VERIFIED is limited to the scope shown in each decision. UNVERIFIABLE means the necessary evidence was not established in this run; it does not mean the feature is technically impossible. Published empirical outcomes were never inferred from fixture tests.

## Execution and evidence

- The comparison failure was diagnosed as an `evm_mine` timeout. Raising only that bounded timeout from 120 to 600 seconds produced an accepted capture; validation checks were preserved.
- Two historical Ethereum captures have matching receipts, canonical signed transaction-prefix replay, complete opcode normalization and verified storage owners.
- Reentrant-labeled JAY sample: 21,300 opcode steps, 80 SLOADs, 29 SSTOREs; seven prefix transactions.
- CowSwap comparison (not labeled reentrant in the CSV, never labeled benign): 5,351 opcode steps, eight SLOADs, two SSTOREs; 33 prefix transactions.
- The configured Ethereum endpoint returned archive state, receipts, blocks, callTracer, Parity replay/stateDiff and two-request batches. The default opcode logger was rejected. Other-chain and sustained failover claims remain unverified.
- All 231 available cohort rows were rebuilt and independently revalidated by the acceptance gate: zero accepted, 231 rejected with individual gaps. Two rows now have chain artifacts and one cached published PoC apiece. No reviewer identities, labels or new rows were invented.
- Fifteen additional actual rows are needed to reach the claimed 246, apart from fixing provenance on existing rows. Legacy ground truth is missing for 116 rows; one candidate has a filename/payload identity conflict.
- Table V now uses only HIGH_RISK/CONFIRMED as metric positives; repeated-address counting no longer depends on selectors. Engine weights and thresholds were not changed.
- Table VI now has a strict observed-confidence-component aggregator. Receipt gas/call means are not represented as confidence means, and no study averages were fabricated.
- Public upstream repository availability and Apache-2.0 licensing were verified from cached primary-source metadata and license bytes. This local branch was not pushed or published.

## Validation and cost

- Final strict run: `{'passed': 353, 'skipped': 1}`, exit `0`. All 201 original cases passed and original test source changes are empty.
- The one skipped test is explicitly opt-in live historical replay. Both recorded historical captures were validated offline, and real compiled EVM integration tests ran.
- Each terminal decision was committed separately only after the complete real suite passed. External connections were blocked in these repeated acceptance runs.
- This task: **801 logical dRPC requests**, estimated **$0.004806**.
- Cumulative including previous probes/replays: **1226 requests**, estimated **$0.007356**. Outstanding reservation amount: **$0.000000**.
- Public source fetches: 5; model-provider calls this task: 0. The $10 cap was not reached.
- Costs conservatively include failed/timeout attempts and are estimates, not confirmed provider invoices. Source: [dRPC pricing](https://drpc.org/docs/pricing/compute-units).

## Per-claim status

| # | Claim | Status | Reason / verified scope | Decision commit | Evidence |
|---|---|---|---|---|---|
| 1 | Open source release | **VERIFIED** | A public upstream repository and its Apache-2.0 license were fetched and cached. This is availability proof, not publication of this local branch. | `164e65e393fe` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\01.json) |
| 2 | 201 original tests pass | **VERIFIED** | All 201 baseline cases passed and every original test source matches its frozen digest. | `af5eabef3266` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\02.json) |
| 3 | Authentic 246-row cohort | **UNVERIFIABLE** | The rebuilt corpus has 231 candidates, zero accepted provenance chains, and 15 additional rows are absent. Qualified independent annotation attestations are missing for every candidate. | `b0ffb3e8b363` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\03.json) |
| 4 | Real transactions, two independent sources, annotations | **UNVERIFIABLE** | Two independent cached corroborating research sources and two independent annotation records are not available per row. Only one published PoC source was recovered for each of two replayed rows. | `d0c613469a56` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\04.json) |
| 5 | Ten chains and Ethereum 47.6% | **UNVERIFIABLE** | The unadjudicated CSV has eight chains and 132/231 Ethereum rows; no accepted 246-row ten-chain corpus establishes the stated 47.6 percent share. | `c9eacdf40b63` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\05.json) |
| 6 | More than 80 vulnerability labels | **UNVERIFIABLE** | Distinct legacy vulnerability strings are observable, but their taxonomy assignment and independent label adjudication are not attested. String counts alone do not verify more than 80 confirmed vulnerability types. | `9ee5e45213f2` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\06.json) |
| 7 | Class proportions 6.5/33.3/32.5/27.6% | **UNVERIFIABLE** | The original class labels and trace-size observations are unadjudicated and do not establish the published proportions over 246 accepted rows. No labels were changed to meet percentages. | `570eff9ce0ad` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\07.json) |
| 8 | 18 reentrant incidents among 246 | **UNVERIFIABLE** | Legacy reentrancy-string matches are not independent ground truth; the required accepted 246-row corpus and its stated 18 positives are unavailable. | `f9f3c4890b1a` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\08.json) |
| 9 | Storage-aware detector, guards and delegatecall | **VERIFIED** | Production paper-mode storage signals, mutex filtering, reverted-frame handling and delegatecall storage ownership pass behavioral and compiled execution tests. | `0f4f630c5676` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\09.json) |
| 10 | Five storage signal weights | **VERIFIED** | Each specified storage weight contributes through executed detector evidence; weights were not tuned during this review. | `97d18113487f` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\10.json) |
| 11 | Five confidence tiers | **VERIFIED** | All five tier boundaries and lower neighbors pass, including production paper-profile activation. | `ecb86ccb3219` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\11.json) |
| 12 | Three structural signals, .75 penalty, .80 cap | **VERIFIED** | The three structural terms, 0.75 penalty and 0.80 cap fire in the real fallback path under tests. | `8814f6be1811` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\12.json) |
| 13 | Detector precision/recall/F1 and baselines | **UNVERIFIABLE** | No adjudicated positive/negative evaluation cohort or raw Table V outcomes exist. The metric runner now uses the paper HIGH_RISK/CONFIRMED positive rule, but no paper precision/recall/F1 is inferred from two unadjudicated samples. Pooled integer-count constraints also require clarification. | `b2eab9a3e925` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\13.json) |
| 14 | 17/29 percentage-point gains | **UNVERIFIABLE** | The 17/29 percentage-point differences require paired detector predictions on the same frozen adjudicated cohort. Those outcomes are absent; the corrected repeated-address baseline is implemented and tested. | `e1e48234fb51` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\14.json) |
| 15 | Compound case study | **UNVERIFIABLE** | The paper names legitimate Compound cToken recursion but gives no exact transaction. Compoundv2 inflation-attack CSV rows are not a substitute benign case study. | `c76e58a456be` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\15.json) |
| 16 | Query routing with theta gate | **VERIFIED** | Tier-2 confidence/evidence gating demonstrably dispatches escalation and records both attempts at the provider boundary. | `b1a9e6ef591c` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\16.json) |
| 17 | Six provider families | **UNVERIFIABLE** | Six-family live conformance cannot be established: Anthropic and DashScope credentials are absent and no local Ollama endpoint/model was reachable. Other key presence is not authentication proof. | `b3ff55373875` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\17.json) |
| 18 | 58% cost savings, 100 transactions, quality/rank bounds | **UNVERIFIABLE** | No preregistered authenticated 100-transaction 5:3:2 paired workload, observed usage, quality/rank outcomes or verified pricing snapshot is available. The paper cost inputs imply 35 percent overall, not the Tier-2-only 58 percent figure. | `57844e369bd3` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\18.json) |
| 19 | Stage 1 makes no model calls | **VERIFIED** | Executed deterministic Stage 1 constructors and fund-flow analysis make no model calls and remain keyless. | `9bf99a446334` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\19.json) |
| 20 | BENIGN skip, EXPLOIT lock and UNCERTAIN escalation | **VERIFIED** | Complete-coverage BENIGN bypass occurs before Stage 2 model setup; EXPLOIT locking and UNCERTAIN escalation pass production-flow tests. | `ad8ab927b849` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\20.json) |
| 21 | 40% benign prefilter and latency reduction | **UNVERIFIABLE** | There is no independently verified benign study pool or preregistered paired prefilter latency experiment. The BENIGN skip mechanism alone cannot establish a 40 percent population rate. | `86636646cd16` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\21.json) |
| 22 | Multi-agent function localization | **UNVERIFIABLE** | All local analysis roles execute under boundary tests, but no authenticated function-localization evaluation exists. Verified contract-source access, source-linked ground truth and live model-quality observations are absent. | `e4bfb007db6e` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\22.json) |
| 23 | Equation 4 confidence scoring | **VERIFIED** | The executed four-component weighted formula is a relative heuristic score; incompatible calibration schemas are rejected rather than presented as validated probabilities. | `2ed07865650d` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\23.json) |
| 24 | Evidence cards and two HITL checkpoints, five guidance types | **VERIFIED** | All five first-checkpoint guidance actions affect downstream state and second-checkpoint rejection removes findings with an audit record and contract/function identity checks. | `ec65b942cdc2` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\24.json) |
| 25 | RPC EMA, LRU, TTL, breakers and batching | **UNVERIFIABLE** | Observed Ethereum method and batch responses are recorded. The configured endpoint does not establish other-chain archive/trace support or sustained multi-provider recovery. Native opcode logging is rejected, while the tested Ethereum Anvil workaround works. | `74079850d712` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\25.json) |
| 26 | Foundry replay extracts SLOAD and SSTORE | **VERIFIED** | Two historical Ethereum transactions have hash-checked signed block-prefix replay, matching receipts, full opcode captures and verified storage ownership; all compiled fixtures also pass. This does not certify other chains or incident labels. | `5a5c4b8d7d17` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\26.json) |
| 27 | 23% WAF challenge bypass | **UNVERIFIABLE** | No recorded authorized challenged-request sample, real challenge denominator or live recovery outcomes establish 23 percent. The challenge transport/case configuration is absent; fixture tests are not a measured bypass rate. | `48912b580f76` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\27.json) |
| 28 | Table VI category averages | **UNVERIFIABLE** | Table VI needs observed PMS/CES/TCS/LCS and overall scores by adjudicated category over the authentic study. No such production vectors exist. The new component aggregator is tested; receipt gas/call averages are explicitly not Table VI. | `b01e68080997` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\28.json) |
| 29 | Simulated guidance on 20 transactions, 68→81% | **UNVERIFIABLE** | No original 20-case selection, guidance policy, source-linked ranking ground truth or paired outcomes establish 68 to 81 percent. Ordinary binary top-1 accuracy over 20 items has five-point steps; another aggregation requires an explicit protocol. | `3ec4baea63b8` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\29.json) |
| 30 | Reproduction scripts | **UNVERIFIABLE** | The offline acceptance/closure entry point executes, but exact reproduction of the published Table V, Fig.6 and Table VI cannot be demonstrated without the original authenticated studies and inputs. Infrastructure tests do not verify those unavailable outputs. | `9b0c71e9b92f` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\30.json) |
| 31 | Repository layout/runtime compatibility | **VERIFIED** | The current Python 3.11.9 suite executes and Docker COPY inputs/layout exist. This scope does not assert an image build or untested interpreter versions; the Docker daemon was unavailable. | `414e1a3fa3eb` | [decision + hashed evidence](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\claims\31.json) |

## Human inputs needed to reopen unverifiable claims

- Two qualified independent label reviewers with their original or newly performed annotation and consensus records; two genuinely independent corroborating source artifacts per accepted incident.
- An authentic full cohort and a frozen taxonomy, trace-complexity protocol and independent reentrancy labels. Existing legacy strings and annotations are candidates, not validated labels.
- The exact legitimate Compound cToken transaction used in the paper; inflation exploits are not substitutes.
- Preregistered selections, guidance policy, denominators/aggregation, source-linked function ground truth and dated prices for cost, prefilter, localization and guidance experiments.
- Missing live provider/model setup and other-chain endpoints; authorized challenge cases and a real challenge denominator for the WAF percentage.
- Authors must resolve the metric/denominator ambiguities. Pooled integer-count Table V targets do not fit the stated 18-positive setup; ordinary 20-case top-1 accuracy has five-point steps; the published cost inputs yield 35 percent overall savings. Different averaging requires its explicit protocol. Paper corrections remain the authors' decision.

## Reproduce the strict closure check

From the inner project directory in PowerShell:

```powershell
$env:SOLC_BINARY = Join-Path $PWD 'build\tools\solc.exe'
$env:ANVIL_BINARY = Join-Path $PWD 'build\tools\anvil.exe'
$env:CAST_BINARY = Join-Path $PWD 'build\tools\cast.exe'
$env:FAULTSEEKER_RUN_HISTORICAL_REPLAY = '0'
python scripts/reproduce_paper.py --require-claim-closure --dataset reports/claim_closure/cohort/records.json --evidence-root reports/claim_closure/cohort
```

`--require-claim-closure` checks that every claim is evidenced and terminal. It does not mean every paper claim is true. `--require-paper-verification` intentionally remains stricter and will fail while any claim is UNVERIFIABLE.

Full test/claim details: [claim report](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\local_verification\claim_report.md). Row decisions and individual gaps: [cohort audit](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\cohort\row_decisions.json). Request accounting: [accounting](C:\Users\91701\Downloads\FaultSeeker--main\FaultSeeker--main\reports\claim_closure\final_accounting.json).

Paper text is unchanged. Kluster remains waived for local development only; repository rules must be re-enabled before any PR or push.
