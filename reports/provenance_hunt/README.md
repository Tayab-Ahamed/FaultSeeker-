# Reopened paper-claim evidence pass

This pass reopened all 18 UNVERIFIABLE claims. It does not declare the paper fully verified. The final decision table and commit IDs are in FINAL_REPORT.md.

## Acquired evidence

- Every one of the original 231 exact transaction identities was searched. Search outputs are lead records, not primary-source corroboration.
- 734 unique public source URLs have cached request records, including failures. Successful/error HTTP bodies are gzip-cached without executing downloaded code, with compressed-file and original-body SHA256 digests.
- Four original rows (61 Orion, 73 Euler, 81 Inverse Finance, 99 Zunami) have reviewed corroborating accounts from two distinct security research publishers. Four primary-source pairs do not satisfy the entire study's source requirement or its independent annotation requirement.
- 108 of the original 132 Ethereum identities have matching single-provider transaction and receipt responses; 24 returned both results null. Other chains were searched for sources but not queried through an Ethereum endpoint. A null response is provider evidence, not global proof of nonexistence.
- Fifteen additional exact-host Ethereum transaction references were selected from documented historical incident sections, searched, cached and checked against real matching transaction/receipt identities. They are candidates, not identified original missing paper rows or independently adjudicated exploit outcomes. The initial explorer-subdomain selection error is preserved in new_candidates_initial_selection.json; the corrected selector has a regression test.
- The self-contained cohort folder contains 246 candidate identities and **0 accepted records**. Missing fields are listed for every row. No annotations, vulnerability labels or function rankings were synthesized. The original CSV and paper were not changed.

## Provider checks

Two separately supplied Nara credential variables were tried on the same Claude and Qwen aliases. Initial responses were 402/429. One diagnostic retry each returned rate_limited with an insufficient-credit message. This does not mean the visible seven-million free allowance is exhausted: the captured free-plan list covers other aliases. An eligible agnes-2.5-flash control returned HTTP200, exact nonce/JSON content and token usage. That checks this free route only.

The configured NVIDIA catalog returned 80 models without Qwen; one officially documented Qwen endpoint returned HTTP410. Atria's authenticated catalog returned only Atria-Dawn. None of these observations verifies Claude or Qwen family conformance. Native Anthropic/DashScope adapters remain untested; local Ollama was unreachable. No model quality claim is established by a chat smoke check.

Authoritative route references: [Nara documentation](https://router.bynara.id/docs), [NVIDIA LLM API reference](https://docs.api.nvidia.com/nim/reference/llm-apis), [Atria documentation](https://api.atria-asi.ai/docs). Their returned source/catalog snapshots are in providers/.

## Experiments and interpretation

The actual detector, category, routing, prefilter and guidance entry points returned BLOCKED-BY-DATA (exit2) before dispatching any empirical model/RPC work. Localization and TableVI confidence-vector evaluation remain explicitly not dispatched. WAF preflight separately records its missing authorized challenge manifest and browser-TLS transport.

No real precision/recall/F1, paired gains, savings percentage, latency/bypass rate, guidance/localization accuracy, or category confidence means were measured. These values and their paper deltas are **undefined**, not zero. The categories entry point is receipt/category instrumentation and is not a substitute for TableVI's PMS/CES/TCS/LCS vectors. No original preregistration artifact was found; the blocked preflights are not preregistration or completed experiments.

## Reproduce without dispatching paid requests

Run from the nested repository root:

```powershell
python scripts/hunt_claim_provenance.py
python scripts/summarize_provenance_hunt.py
$env:SOLC_BINARY = "$PWD/build/tools/solc.exe"
$env:ANVIL_BINARY = "$PWD/build/tools/anvil.exe"
$env:CAST_BINARY = "$PWD/build/tools/cast.exe"
$env:FAULTSEEKER_RUN_HISTORICAL_REPLAY = '0'
python scripts/reproduce_paper.py --require-claim-closure --dataset reports/provenance_hunt/cohort/records.json --evidence-root reports/provenance_hunt/cohort
```

Live fetch/identity acquisition require explicit --fetch/--verify-ethereum switches. Gateway smoke requests require --execute-live and use the durable shared spend ledger. Existing gateway observations are reused instead of dispatched again. Do not delete the real ledger or prior evidence to rerun.

The next-input column in FINAL_REPORT.md names one next required artifact per claim; it is not a promise that every other prerequisite disappears. Detailed unmet requirements and previous decisions are preserved in the claim registry.

Kluster remains waived for local development only. Before any push or PR, the repository's full Kluster rules apply. No push or PR was performed.
