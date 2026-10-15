# Final reopened-claim evidence report

**Outcome: 13 VERIFIED within their recorded scopes; 18 remain UNVERIFIABLE. No new paper claim was verified.** All 18 were reopened, investigated and individually committed after a full-suite gate. This completes this evidence pass, not verification of every paper assertion.

## Evidence that moved

- Searched every original exact transaction hash: **231/231**, with saved queries/results. Search snippets were treated as leads, not corroborating artifacts.
- Cached **734 unique public-source URL request records**, including failures, with source/body hashes; downloaded code was never executed. Four original rows (61 Orion, 73 Euler, 81 Inverse Finance, 99 Zunami) have reviewed accounts from two separate primary security publishers. Most rows still lack two acceptable sources.
- Queried the original 132 Ethereum identities: **108 matching transaction/receipt pairs, 24 pairs of null results** from the configured dRPC endpoint. Null results are single-provider observations, not proof that no transaction exists anywhere. The other 99 original rows were source-searched but not sent to an Ethereum endpoint.
- Located **15 additional documented incident-associated Ethereum transaction references**, all with real matching transaction/receipt identities. Their exploit roles, independent labels and membership in the original paper study are unproven. They were not renamed as the original missing 15.
- The new bundle has **246 candidate identities and 0 accepted rows**. All 246 lack independent annotation; 242 lack a reviewed dual-source pair; 244 lack a trace/full verification record. One pre-existing ground-truth identity conflict remains exposed. Per-row gaps are retained.
- No exact legitimate Compound cToken case-study hash was identified. Public searches and paper text do not uniquely identify it; unrelated Compound transactions were not substituted.

[Every row and its rejection reasons](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/cohort/row_decisions.json) · [Source manifest and hashes](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/source_manifest.json) · [Reviewed source pairs](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/reviewed_source_pairs.json) · [15 new reference candidates and source hits](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/new_candidate_source_hits.json)

## Provider observations

| Route / credential variable | Named model check | Observed outcome | Scope |
|---|---|---|---|
| Nara / NARAROUTER_API_KEY | Claude Haiku alias | HTTP402 | No conforming completion |
| Nara / NARAROUTER_API_KEY | Qwen alias | HTTP429 | No conforming completion |
| Nara / BYNARA_API_KEY | Claude Haiku alias | HTTP402, diagnostic retry HTTP429 | Provider message: insufficient credits |
| Nara / BYNARA_API_KEY | Qwen alias | HTTP429, diagnostic retry HTTP429 | Provider message: insufficient credits |
| Nara / BYNARA_API_KEY | agnes-2.5-flash free control | HTTP200; nonce, JSON and usage checks passed | VERIFIED-VIA-NARAROUTER for this free route only |
| NVIDIA | Documented qwen/qwen2.5-coder-32b-instruct endpoint | HTTP410; no Qwen in the 80-model returned catalog | No Qwen conformance proven |
| Atria | Authenticated model catalog | Atria-Dawn only | Does not substitute for Claude/Qwen |
| Native Anthropic / DashScope | Native adapters | UNTESTED | Gateway rejection does not prove native adapter failure |
| Local Ollama | localhost:11434 | Unreachable; no installed model observed | Pending local service/model |

The screenshot and captured free-plan catalog show that free allowance applies to eligible model groups. A remaining free allowance does not establish entitlement to Claude or Qwen aliases. PAYG was not enabled, no balance was purchased, and no API key is included in evidence. The successful free control checks chat transport, not localization quality or production-pipeline gateway integration. All live per-attempt outcomes and documentation/catalog snapshots are in [providers](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/providers/inventory.json).

## Empirical outcomes and paper deltas

| Claim / outcome | Real measurement in this pass | Delta from paper |
|---|---|---|
| 13: TableV precision/recall/F1 | Not measured; detector preflight BLOCKED-BY-DATA | Undefined |
| 14: +17/+29 point gains | No accepted paired detector outcomes | Undefined |
| 18: 58% savings / 100-case quality study | Routing preflight BLOCKED-BY-DATA | Undefined |
| 21: 40% prefilter / latency | Prefilter preflight BLOCKED-BY-DATA | Undefined |
| 22: localization quality | Not dispatched; source-linked function truth absent | Undefined |
| 27: 23% WAF recovery | Preflight missing registered cases/browser transport | Undefined |
| 28: TableVI confidence averages | Authentic production component vectors absent | Undefined |
| 29: guidance 68→81% | Guidance preflight BLOCKED-BY-DATA | Undefined |

No original preregistered study manifest was found. The real detector/category/routing/prefilter/guidance entry points were invoked and refused rejected data before empirical inference/RPC dispatch. These gate results are not completed studies. A category/receipt instrument is not TableVI confidence-component measurement. Undefined metrics are not recorded as zero; no model, weight, threshold, label or cohort membership was adjusted to hit a target. [Commands, exit codes and full preflight logs](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/experiments/dispatch_log.json).

## All 31 claim statuses

VERIFIED retains each existing decision's stated scope. In particular, source availability is not publication of this branch; two Ethereum replay samples do not prove all-chain behavior; Docker input checks are not a Docker build.

| ID | Claim | Status | Latest claim decision/evidence commit |
|---|---|---|---|
| 1 | [Open source release](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/01.json) | VERIFIED | `164e65e` |
| 2 | [201 original tests pass](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/02.json) | VERIFIED | `af5eabe` |
| 3 | [Authentic 246-row cohort](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/03.json) | UNVERIFIABLE | `275d24f` |
| 4 | [Real transactions, two independent sources, annotations](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/04.json) | UNVERIFIABLE | `86d77db` |
| 5 | [Ten chains and Ethereum 47.6%](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/05.json) | UNVERIFIABLE | `c1d51f8` |
| 6 | [More than 80 vulnerability labels](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/06.json) | UNVERIFIABLE | `0402006` |
| 7 | [Class proportions 6.5/33.3/32.5/27.6%](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/07.json) | UNVERIFIABLE | `a8d4a4d` |
| 8 | [18 reentrant incidents among 246](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/08.json) | UNVERIFIABLE | `51cc168` |
| 9 | [Storage-aware detector, guards and delegatecall](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/09.json) | VERIFIED | `0f4f630` |
| 10 | [Five storage signal weights](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/10.json) | VERIFIED | `97d1811` |
| 11 | [Five confidence tiers](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/11.json) | VERIFIED | `ecb86cc` |
| 12 | [Three structural signals, .75 penalty, .80 cap](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/12.json) | VERIFIED | `8814f6b` |
| 13 | [Detector precision/recall/F1 and baselines](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/13.json) | UNVERIFIABLE | `4d5c185` |
| 14 | [17/29 percentage-point gains](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/14.json) | UNVERIFIABLE | `101c88a` |
| 15 | [Compound case study](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/15.json) | UNVERIFIABLE | `731c404` |
| 16 | [Query routing with theta gate](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/16.json) | VERIFIED | `b1a9e6e` |
| 17 | [Six provider families](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/17.json) | UNVERIFIABLE | `72495ba` |
| 18 | [58% cost savings, 100 transactions, quality/rank bounds](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/18.json) | UNVERIFIABLE | `3e4fd3b` |
| 19 | [Stage 1 makes no model calls](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/19.json) | VERIFIED | `9bf99a4` |
| 20 | [BENIGN skip, EXPLOIT lock and UNCERTAIN escalation](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/20.json) | VERIFIED | `ad8ab92` |
| 21 | [40% benign prefilter and latency reduction](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/21.json) | UNVERIFIABLE | `b0f6c40` |
| 22 | [Multi-agent function localization](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/22.json) | UNVERIFIABLE | `896c9d3` |
| 23 | [Equation 4 confidence scoring](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/23.json) | VERIFIED | `2ed0786` |
| 24 | [Evidence cards and two HITL checkpoints, five guidance types](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/24.json) | VERIFIED | `ec65b94` |
| 25 | [RPC EMA, LRU, TTL, breakers and batching](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/25.json) | UNVERIFIABLE | `401f5a6` |
| 26 | [Foundry replay extracts SLOAD and SSTORE](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/26.json) | VERIFIED | `5a5c4b8` |
| 27 | [23% WAF challenge bypass](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/27.json) | UNVERIFIABLE | `1e62f37` |
| 28 | [Table VI category averages](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/28.json) | UNVERIFIABLE | `92c756b` |
| 29 | [Simulated guidance on 20 transactions, 68→81%](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/29.json) | UNVERIFIABLE | `905d2f6` |
| 30 | [Reproduction scripts](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/30.json) | UNVERIFIABLE | `1b3f215` |
| 31 | [Repository layout/runtime compatibility](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/claim_closure/claims/31.json) | VERIFIED | `414e1a3` |

## Reopened claims: evidence and one next required input artifact

The input column identifies one next artifact to supply, sometimes a manifest/bundle with several required fields. It is not a claim that there is exactly one remaining credential or dependency. Detailed unmet prerequisites and original decisions are preserved in the registry and previous_decisions/.

| ID | Evidence-based result of reopening | Next required input artifact |
|---|---|---|
| 3 | The 246-entry file now contains the original 231 plus 15 new canonical Ethereum transaction-reference candidates, not the original missing paper members. Full acceptance remains zero. Of 132 original Ethereum identities, 108 matched and 24 returned both RPC results null. New candidate receipts do not establish exploit roles or labels. | Author cohort manifest with corrected canonical identities and complete provenance/adjudication attachments |
| 4 | All 231 exact identities were searched. There are 734 cached public-source request records and four content-reviewed pairs of original security-publisher accounts. The remaining 242 candidate rows lack an accepted pair and all 246 lack independent annotation. Mirrors and distinct domains alone were not accepted. | Complete dual-source and independent-annotation evidence manifest for the intended study cohort |
| 5 | No accepted ten-chain paper population exists. Adding 15 Ethereum reference candidates cannot establish the published chain mix or 47.6 percent share. Original Ethereum null identities further invalidate naive counting. | Frozen accepted ten-chain cohort membership manifest |
| 6 | Incident sources supply candidate mechanism descriptions, but no qualified independently adjudicated SWC/DASP taxonomy is supplied. Public descriptions and legacy strings remain separate from accepted labels. | Independently adjudicated SWC/DASP taxonomy manifest |
| 7 | Existing class labels have not been altered, and new candidates were not assigned classes. No accepted 246-case trace-complexity population or frozen class assignment protocol verifies the published proportions. | Frozen trace-complexity class assignment manifest for the authentic cohort |
| 8 | Reentrancy is independently corroborated for some incidents such as Orion, but no accepted cohort-wide binary annotation manifest establishes exactly 18 reentrant rows among the paper 246. | Independently adjudicated reentrancy membership manifest |
| 13 | The real detector runner was invoked against the rebuilt candidate evidence and returned BLOCKED-BY-DATA before prediction. Precision, recall, F1 and deltas are undefined, not zero, on zero accepted records. | Preregistered Table V evaluation manifest with accepted labels and pooling definitions |
| 14 | The paired detector experiment entry point refused the unaccepted cohort. No paired outcomes exist from which to compute the published 17/29 point gains or their deltas. | Accepted paired detector-study manifest |
| 15 | Targeted public searches and the paper/repository narrative did not establish a unique legitimate Compound cToken transaction. No arbitrary Compound interaction or inflation exploit was substituted, and no unidentified transaction was claimed as replayed. | Exact author-identified Compound cToken case-study transaction hash |
| 17 | Actual routed attempts did not verify the claimed Claude or Qwen families: two Nara credential variables gave 402/429, diagnostic messages said insufficient credits, and a documented NVIDIA Qwen endpoint gave 410. Atria exposes only Atria-Dawn. The eligible Agnes free control passed but is not either claimed family. Native Anthropic/DashScope adapters remain untested; Ollama remains unreachable. | Executable six-family access configuration, including eligible Claude/Qwen access and a reachable installed Ollama model |
| 18 | Routing experiment preflight returned BLOCKED-BY-DATA. A successful tiny free-model control and conservative spend allocations are not a 100-case paired cost/quality study. No savings percentage or empirical delta is reported. | Preregistered 100-case 50/30/20 paired routing workload and pricing manifest |
| 21 | The existing source CSV is exploit-oriented and no independently benign evaluation cohort is accepted. The real prefilter runner returned BLOCKED-BY-DATA before any rate/latency measurement. | Independent benign-cohort paired prefilter study manifest |
| 22 | New incident and receipt evidence does not establish source-linked function-ranking ground truth. Gateway smoke responses test chat transport only; no localization-quality experiment was dispatched or inferred. | Verified source-linked function localization evaluation manifest |
| 25 | 302 further metered Ethereum identity/receipt requests were recorded, including null identities. They add evidence for the specific Ethereum read methods but do not establish other-chain archive/opcode support or sustained independent-provider failover. | Multi-chain endpoint and preregistered live failover test manifest |
| 27 | Public-source HTTP 403/challenge failures were cached, but these are not a preregistered explorer recovery denominator. The WAF runner reports missing challenge cases and CURL_IMPERSONATE_BINARY; no 23 percent rate is inferred. | Authorized preregistered explorer-challenge case and browser-transport bundle |
| 28 | No authentic production PMS/CES/TCS/LCS vectors exist for an accepted study cohort. Receipt data and free-model conformance are not Table VI observations; means and deltas remain undefined. | Observed production confidence-vector dataset for the accepted cohort |
| 29 | The guidance experiment runner returned BLOCKED-BY-DATA. No original or preregistered 20-case selection, independent function ranks, guidance policy or denominator establishes 68 to 81 percent. | Preregistered 20-case guidance evaluation manifest with ranking ground truth and aggregation |
| 30 | Real experiment entry points and all local tests run, but source acquisition does not supply the authentic labels and observations required to reproduce the published tables/figures. No empirical output is generated from rejected records. A gzip/plain-JSON mismatch in the experiment reader was repaired and tested against the actual 21,300-step historical JAY capture; this proves artifact IO, not empirical metrics. | Author reproducibility bundle with authentic inputs, study protocols and raw outcomes |

## Validation, commits and budget

- Final strict closure run: **361 passed, 1 skipped**, exit0; **all 201 original cases passed and their source hashes are unchanged**. Skip: explicitly opt-in live historical replay. Real compiled Anvil fixtures and both recorded historical-capture validation tests ran. All 31 decision/evidence-hash checks passed. Strict closure completion permits documented UNVERIFIABLE decisions; it does not satisfy --require-paper-verification.
- Each of the 18 reopened decision commits ran its own green full suite (360 passed, 1 skipped). The subsequent claim30 IO regression brought the final suite to 361 passed. The real JAY artifact reader now preserves **21,300 opcodes, 80 SLOAD and 29 SSTORE**, without accepting the row or inventing a metric. Reader fix: `1b3f215`.
- RPC requests: **302 new logical methods**, **1,528 cumulative**. RPC estimate: **$0.001812 new; $0.009168 cumulative**, not invoice-confirmed.
- Gateway chat attempts: **8**, consisting of seven rejected named-family attempts and one successful eligible free control. Each attempt conservatively consumes a **$0.10 ledger allocation**, including rejected/free calls. **$0.80 allocated** is not a claim of actual billed charges.
- Shared cumulative ledger: **$0.809168 in estimates/allocations**, **0 outstanding reservations**, below the $10 cap. No empirical paper-quality inference calls were made. Provider metadata/doc GETs: 7; source collection: 734 unique URL request records plus 3 initial index downloads, with failure-before-dispatch possible. No billing statement was queried.
- Paper PDF hash matches the original; no paper text, detector weights or tier thresholds were changed. Kluster was waived for local development only. No push or PR was made; full repository Kluster rules apply before either.

[Machine summary with all decision commits](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/final_summary.json) · [Accounting and its limitations](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/accounting.json) · [Strict machine claim report](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/local_verification/claim_report.json) · [Reproduction commands and acquisition guide](C:/Users/91701/Downloads/FaultSeeker--main/FaultSeeker--main/reports/provenance_hunt/README.md)

**Next practical step:** recover or create the independent cohort annotations and verified identity/source chains, then freeze the study manifests before spending inference budget. Working free API access alone does not resolve the evidence gate.
