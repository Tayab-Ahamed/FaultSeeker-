"""Build publication-scope numerical map and evidence-bound decision proposals."""
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.collect_canonical_evidence import BASE, write


def build():
    findings = json.loads((BASE / 'findings.json').read_text())
    history = json.loads((BASE / 'cohort_history.json').read_text())
    numbers = []

    def number(key, paper, verdict, replacement, evidence, scope='Implementation paper'):
        numbers.append(dict(key=key, paper=paper, verdict=verdict, replacement=replacement,
                            evidence=evidence, publication_scope=scope))

    c = history['requested_231_snapshot']
    early = next(v for v in history['versions'].values() if v['rows'] == 246)
    number('cohort', '246 authentic exploits (2021-2026)', 'COUNT-EXISTS-AUTHENTICITY-UNVERIFIED',
           '246 unique records existed, with 15 malformed EVM hashes; frozen fca6b99 has 231, current main 183', 'cohort_history.json')
    number('sources', '6 incident sources; 2 independent corroborating sources per incident', 'UNSUPPORTED',
           'Source catalog and incident disclosure/detection links recovered; no complete per-row independence/adjudication chain', 'manifest.json; cohort_history.json')
    number('annotators', '2 qualified independent annotators; approximately 8% disagreement', 'UNSUPPORTED',
           '115 original files / 114 unique transaction hashes; 48 Oct 6 reconstructions separate; no annotator attestations or disagreement log', 'cohort_history.json')
    number('chain_count', '10 EVM chains; Table III 10+', 'CONTRADICTED-COHORT',
           '8 chains in every fixed CSV version; wider candidate pool is a different, unvalidated population', 'cohort_history.json')
    number('eth_share', 'Ethereum 47.6%, other chains 52.4%', 'CONTRADICTED-FROZEN-CSV',
           f"132/231 = {100*132/231:.4f}% Ethereum, {100*99/231:.4f}% others; not adjudicated population estimates", 'cohort_history.json')
    number('types', '80+ vulnerability types with SWC/DASP labels', 'LABEL-STRINGS-ONLY',
           '82 distinct vuln_type strings at fca6b99; 89 in early 246 and 69 in current 183. Semantic uniqueness and correctness unadjudicated', 'cohort_history.json')
    for klass, published in [('Simple', '6.5%'), ('Moderate', '33.3%'), ('Complex', '32.5%'), ('Exceptionally Complex', '27.6%')]:
        count = c['class_counts'][klass]
        number('complexity_' + klass, f'{klass}: {published}', 'CONTRADICTED-FROZEN-CSV',
               f'{count}/231 = {100*count/231:.4f}% legacy labels; authentic trace-based class adjudication unavailable', 'cohort_history.json')
    number('complexity_combined', 'Moderate + Complex 65.8%; bins <=5, 6-50, 51-500, >500 functions', 'PROPORTIONS-UNSUPPORTED',
           '153/231 = 66.2338% by stored class; bins are definitions, not proof that class assignments obey them', 'cohort_history.json')
    number('reentrancy_count', '18/246 = 7.3% reentrancy', 'CONTRADICTED-LABEL-COUNT',
           '17/231 = 7.3593% at fca6b99; 19/246 early, 17/213 Oct 6, 16/183 current; labels are not independently verified exploit outcomes', 'cohort_history.json')
    number('detector_f1', 'Table V SSTORE P=.89, R=.83, F1=.86', 'UNSUPPORTED',
           'Undefined: canonical recompute evaluated 0 transactions', 'findings.json; snapshots/*/reports/research_results/reentrancy_metrics.json')
    number('structural', 'Table V structural P=.72, R=.67, F1=.69', 'UNSUPPORTED',
           'No empirical precision, recall or F1; Oct 6 structural F1 null', 'findings.json')
    number('repeated', 'Table V repeated-address P=.54, R=.61, F1=.57', 'UNSUPPORTED',
           'No empirical precision, recall or F1; Oct 6 baseline F1 null', 'findings.json')
    number('gains', '17 / 29 percentage-point F1 gains', 'UNSUPPORTED',
           'Undefined without paired detector predictions on adjudicated data; proxy classification F1 is a different endpoint', 'findings.json')
    number('tableV_integer', '18 positives with rounded P=.89 and R=.83', 'INCOMPATIBLE-WITH-SINGLE-POOLED-MATRIX',
           'No integer pooled confusion matrix fits both rounded values; macro/trial averaging would require its missing definition', '../claim_closure/numeric_constraints.json')
    number('workload', '100 paired transactions, tier mix 5:3:2 (~50/30/20%)', 'ASSUMED-NOT-OBSERVED',
           'No authenticated paired workload/query log; these fractions are modeling inputs', 'findings.json')
    number('tier_cost', 'Tier 1 $0; Tier 2 hybrid $0.05 vs cloud $0.12; Tier 3 $0.12 both', 'MODEL-INPUTS',
           'Local API fee assumed zero; query costs assumed, not observed token usage or total ownership cost', 'findings.json')
    number('overall_saving', 'Approximately 58% overall inference saving', 'CONTRADICTED-ARITHMETIC',
           '35% modeled; measured savings unavailable', 'findings.json')
    number('tier2_saving', '58% origin', 'ARITHMETIC-ONLY',
           '(0.12-0.05)/0.12 = 58.3333% Tier-2-only; mixture hybrid $0.039 vs cloud $0.060/query, 35% overall', 'findings.json')
    number('price', 'GPT-4o-mini $0.15 input/$0.60 output per million tokens; ~4 characters/token', 'HISTORICAL-ASSUMPTIONS',
           'Versioned price estimates and character-token approximation are not dated invoices or actual token measurements', 'manifest.json; ../claim_closure/environment.json')
    number('rank_quality', 'Hybrid/cloud ranking differences <5% of transactions; Tier 3 quality maintained', 'UNSUPPORTED',
           'No paired ranked outputs/quality measurements', 'findings.json')
    number('prefilter', 'Approximately 40% clean traffic skips Stage 2; bypassing filter increases time ~40%', 'UNMEASURED',
           'BENIGN skip mechanism tested; neither population rate nor paired latency effect measured', 'findings.json; ../claim_closure/claims/20.json')
    number('waf', '23% of Cloudflare explorer challenges bypassed via JSON-RPC fallback', 'UNSUPPORTED',
           'RPC fallback capability is not a challenged-request success denominator; no authorized recorded cohort', '../claim_closure/claims/27.json')
    vectors = {
        'reentrancy': '.82/.71/.76/.73/.76', 'flash loan': '.78/.64/.82/.70/.74',
        'price manipulation': '.75/.60/.79/.68/.71', 'access control': '.70/.68/.65/.72/.69',
        'logic bug': '.55/.58/.60/.61/.58'}
    for category, vector in vectors.items():
        number('tableVI_' + category, f'Table VI {category} PMS/CES/TCS/LCS/overall: {vector}', 'UNSUPPORTED',
               'No observed per-function component vectors or declared aggregation; no substitute from gas/call-count features', '../claim_closure/claims/28.json')
    number('guidance', '20 randomly selected cases; top-1 68% to 81%', 'UNSUPPORTED',
           'No selected cases, policy or paired rankings in recovered history; n=20 binary accuracy has 5-percentage-point steps', 'history_search.json; guidance_history_search.txt')
    number('compound', 'Compound cToken legitimate recursion true negative', 'UNIDENTIFIED-CASE',
           'Narrative recovered in historical JSON but no transaction hash/trace/source mapping; Compound exploit annotations do not identify this benign control', 'history_search.json; manifest.json')
    number('tests', '201 passing tests', 'VERIFIED-LOCAL-SCOPE',
           '201 original cases still pass with original source hashes unchanged; current full suite separately reported', '../claim_closure/claims/02.json')
    settings = [
        ('architecture', '3 stages; 5 signal categories; 3 router tiers; zero Stage 1 LLM calls', 'Executed local mechanisms, not population-quality measurements', '09,16,19,20,23'),
        ('storage_weights', 'Table IV weights .55/.25/.20/.10/.10; depth span >=2, slot writes >=2', 'Paper profile executed by existing behavioral/compiled tests; canonical legacy JSON has write_before_and_after=.20 instead of paper .10', '09,10'),
        ('storage_tiers', '5 tiers >=.80/.55/.30/.10; structural 3 signals x.75 capped .80; mutex 1->2->1', 'Paper profile verified locally. Oct 6 canonical detector uses four different thresholds; its output is not the five-tier paper evaluation', '09,11,12'),
        ('control_threshold', 'EXPLOIT confidence >=.85, BENIGN bypass and UNCERTAIN escalation', 'Executed local control flow, not measured false-positive/negative rates', '20'),
        ('equation4', 'Weights .30/.25/.25/.20; normalized [0,1]', 'Executed relative heuristic score; paper itself says regression calibration is future work, despite calibrated label in figure', '23'),
        ('factor_constants', 'PMS 15 patterns +.20, repeat bonus .30; CES base .30 +.30 source +.20 confirmation; TCS .40 +up to .60; LCS default .50', 'Scoring definitions, not empirical calibration/quality evidence', '23'),
        ('confidence_levels', '5 interpretability levels, very high >=.90, very low <.30', 'Display thresholds, not calibrated probabilities', '23'),
        ('rpc_settings', 'EMA alpha=.2; LRU 512 entries, TTL 600s', 'Local mechanism tests; chain/archive availability and real failover evidence remain scoped', '25'),
        ('signal_tokens', '11 flash-loan borrow tokens; 10 callback tokens; 15 privileged selectors', 'Pattern-list sizes are implementation definitions, not 80+ validated vulnerability coverage', '09'),
        ('hitl', '2 HITL checkpoints, 5 guidance types', 'Feedback behavior exercised; 68->81% empirical effect remains unsupported', '24'),
        ('providers', '6 provider backends', 'Adapter construction tested; native/live family coverage incomplete, Ollama unreachable in previous run', '17'),
        ('runtime_versions', 'Ubuntu22.04, Python3.10+, Foundry0.2.x, web3 6.x', 'Declared historical environment, not proof all historical measurements ran there; current tests run in Windows/Python3.11 with local binaries', '31')]
    for key, paper, replacement, ids in settings:
        number(key, paper, 'MECHANISM-OR-DEFINITION-SCOPE', replacement, '../claim_closure/claims/' + ids)
    number('background', '$100B secured; $3.8B lost in 2022; 16.7 analyst-hours; literature 84/115 incidents, 40+ Slither patterns, 0% complex-case recall',
           'EXTERNAL-LITERATURE-NOT-REPOSITORY-EVIDENCE',
           'Not verified by implementation/Git history; check cited primary publications separately. No replacement inferred', 'Uploaded paper pp1-3')
    number('generations', 'Text says 4 generations; Table I contains Gen1 through Gen5, periods 2016-2026; Table II 12 systems', 'DOCUMENT-INTERNAL-COUNTS',
           'Table I has five generations; Table II has twelve rows. Publication dates/chronology require cited literature', 'Uploaded paper pp2-3')
    # These numbers belong to the recovered JISA audit, not the uploaded implementation paper.
    legacy = 'Recovered JISA audit / extended research results (different publication scope)'
    number('legacy_f1', 'F1 .969, FPR .003, +14.7pp, CI [.961,.975]', 'INVALID-EMPIRICAL-EVIDENCE',
           'Legacy harness reads labels; old .9687 proxy CSV even has CI low .9798 > point estimate. Recovered audit rejects paper CI; no genuine matching run', 'manifest.json; recovered PAPER_CLAIM_AUDIT.md', legacy)
    number('historical_f1', 'Older strict harness .859, CI [.822,.895]', 'REPRODUCED-FEATURE-HARNESS',
           '.8593, CI [.8223,.8950], TP174 FP0 TN1000 FN57; July 50853e4 heuristic formula, not live LLM/full pipeline and not calibrated OOF', 'reruns/50853*/status.json', legacy)
    number('cv_f1', 'Honest five-fold result .759', 'REPRODUCED-FEATURE-HARNESS',
           '.7586, CI [.7071,.8040], P.88 R.6667 FPR.021, TP154 FP21 TN979 FN77; frozen231 exploit +1000 benign-feature rows', 'reruns/8e02*/status.json', legacy)
    number('cv_tig', 'Stored -TIG F1 .6565', 'RERUN-DISAGREES',
           'Byte-pinned rerun .6531 (TP128 FN103), not .6565 (TP129 FN102); other seven scorer results match. No tuning to reproduce the discrepant row', 'reruns/8e02*/status.json; findings.json', legacy)
    number('cv_baselines', 'Static .4808, dynamic .3733, LLM-only .6120; ablations .7556/.6565/.6889/.7586', 'PROXY-CLASSIFIER-SCOPE',
           'Rerun static .4808, dynamic .3733, formula named LLM-only .6120; -FAEGL .7556, -TIG .6531, -calib .6889, -routing .7586. Routing ablation returns same scorer, not actual routing experiment', 'reruns/8e02*/status.json; snapshots/*/benchmark/run_honest_experiments.py', legacy)
    number('adversarial', 'Retention >=.94; .9412/.9647/1/1/.9529', 'UNSUPPORTED-EMPIRICAL-OUTCOME',
           'Old harness uses synthetic two-node trace and literal analyzer deltas; newer CSV retains illustrative .85 baseline scores without raw challenged production runs', 'manifest.json', legacy)
    number('localization', 'Localization top-1 6.09%', 'RECORDED-NOT-REPRODUCED',
           'Stored 7/115 targets =6.09%, top3 23/115=20%, top5 36/115=31.30%, top10 48/115=41.74%, MRR .173; 115 GT files cover114 unique transactions. Raw rankings unavailable in all53 reachable commits', 'findings.json; history_search.json', legacy)
    number('extended_counts', '1059 exploits +10000 benign =11059; 231 fully annotated; 124/121 tests in earlier audit', 'MIXED-POPULATIONS',
           '1059 includes828 candidate exploits, not all validated; extended CV uses1231 records=231+1000. 115 original GT files cover114 unique hashes; declarations are not independent labels', 'manifest.json; cohort_history.json', legacy)
    number('latencies', 'Stage1 2.3+/-0.4s; cloud 8.1+/-1.2s; hybrid 3.4+/-0.8s', 'REMOVED-UNMEASURED',
           'Oct 6 artifact latency=null; no production timing observations to substitute', 'findings.json', legacy)

    details = {
        3: ('COUNT-EXISTS-AUTHENTICITY-UNVERIFIED', 'Early 246 unique records existed (15 malformed hashes), then231/213/183. Original115 files cover114 unique tx; reconstructions48 are separate. No fully authenticated 246-row adjudicated cohort.', 'Frozen cohort with complete independent provenance and qualified annotation records'),
        4: ('PARTIAL-PROVENANCE-RECOVERED', 'Original April3 GT and source catalog/disclosure links are recovered, not manufactured in October. They do not contain two qualified annotator attestations or a complete independent evidence chain per row.', 'Per-row independent corroboration plus signed independent annotation/consensus ledger'),
        5: ('CONTRADICTED-FROZEN-CSV', 'Every fixedCSV version has8chains, not10; fca6b99 Ethereum132/231=57.1429%, not47.6%. Unvalidated candidate-pool coverage is a different denominator.', 'Accepted frozen study cohort and independently verified chain membership'),
        6: ('STRINGS-COUNTED-NOT-ADJUDICATED', 'fca6b99 has82 distinct vulnerability strings with SWC/DASP columns; original GT supports partial named targets but semantic taxonomy uniqueness/correctness is not adjudicated.', 'Adjudicated SWC/DASP label mapping and semantic deduplication for the frozen cohort'),
        7: ('CONTRADICTED-FROZEN-CSV', '231-row class counts Simple19/Moderate62/Complex91/Exceptional59 differ from paper proportions. The early246 also differs (20/71/93/62).', 'Trace-verified function-count bins for the authentic paper cohort'),
        8: ('CONTRADICTED-LABEL-COUNT', '17 reentrancy strings among231 and213,16amongcurrent183,19amongearly246. No18-row authenticated study. Label counts are now checkable, label truth is separate.', 'Independently adjudicated reentrancy positives in the frozen evaluation cohort'),
        13: ('PUBLISHED-METRICS-UNSUPPORTED', 'Historical .86/.69/.57 were literal result declarations; Oct6 recompute evaluates0 and emitsnull F1. Reproduced .7586/.8593 feature classification has a different target and cannot validate TableV.', 'Paired raw detector predictions/confusion counts on adjudicated positives and negatives with defined averaging'),
        14: ('PUBLISHED-GAINS-UNSUPPORTED', '17/29pp are arithmetic between unsupported TableV declarations. Feature-harness ablations are different mechanisms/endpoints; even -TIG recorded .6565 differs from rerun .6531.', 'Paired executed SSTORE/structural/repeated-address outcomes on the same adjudicated rows'),
        15: ('CASE-NARRATIVE-RECOVERED-HASH-MISSING', 'Historical reentrancy_metrics.json contains the cToken narrative with no hash. Compound-related exploit annotations cannot identify the legitimate recursive transaction.', 'Exact legitimate cToken case-study transaction plus source linkage'),
        17: ('LIVE-CONFORMANCE-STILL-INCOMPLETE', 'Canonical adapter/pricing declarations add no authenticated Claude/Qwen/Ollama response. Prior gateway failures remain recorded; native adapters untested, not inferred failed.', 'Eligible live family access including a reachable installed Ollama model'),
        18: ('58-PERCENT-OVERALL-CONTRADICTED', 'Canonical Oct6 removes58%; the published mixture computes35% modeled, with no observed100-case paired workload. No ranking-quality comparison or token billing log.', 'Frozen100-case paired workload with observed usage, pricing and quality outputs'),
        21: ('RATE-UNMEASURED', 'Canonical runtime artifact explicitly marks benign prefilter rate unmeasured. Executed skip mechanism does not establish40% of traffic or paired latency effect.', 'Verified benign workload and paired prefilter latency observations'),
        22: ('HISTORICAL-AGGREGATE-RECOVERED', 'Recovered top1 7/115=6.09% and114 per-tx provenance entries; original GT contains one duplicate transaction explaining target/tx difference. No tracked raw ranked outputs in any reachable canonical commit; cannot rerun localization.', 'Original per-transaction ranked predictions tied to traces/models and source-linked GT'),
        25: ('CAPABILITY-DECLARATIONS-NOT-LIVE-PROOF', 'Canonical data covers8chains; ten-chain provider declarations and protocol add no live archive/opcode/failover observations beyond prior Ethereum probes and replay.', 'Required-chain archive/debug observations and live provider recovery evidence'),
        27: ('RATE-UNSUPPORTED', 'Recovered protocol and audit do not supply challenged-request denominator or successes for23%. Ethereum RPC success is not an explorer WAF bypass experiment.', 'Authorized challenged explorer-request corpus with recovery logs and denominator'),
        28: ('NO-PRODUCTION-SCORE-VECTORS', 'No TableVI component observations; CV classifier derives proxy factors from four numeric trace features, not PMS/CES/TCS/LCS for actual candidate functions.', 'Raw production per-function four-factor scores with adjudicated categories and declared averaging'),
        29: ('GUIDANCE-RESULT-UNSUPPORTED', 'All53 reachable canonical text versions searched: no68%-to81% paired study; binary n20 increments5pp. 6.09% localization belongs to another study, not guidance.', 'Original20-case selection/policy and paired rankings with explicit aggregation definition'),
        30: ('PARTIAL-REPRODUCTION-NOT-PAPER-REPLICATION', 'Canonical protocol recovered; two historical proxy/feature harnesses actually reproduced offline without tuning. They do not reproduce TableV/VI/guidance or authenticate the paper cohort.', 'Authentic paper-study input/output artifacts and exact experiment protocol')}
    decisions = [dict(id=n, status='UNVERIFIABLE', paper_verdict=v, reason=r, missing_input=m)
                 for n, (v, r, m) in sorted(details.items())]
    payload = {'paper_sha256': '96878e703f5c0bc27324f7da63c775fab66d4fed3ef6a272d238244ff6e7b31b',
               'inventory_scope': 'All quantitative project assertions, formulas/settings and Tables IV-VI in uploaded eight-page implementation paper; repeated mentions consolidated. External literature grouped separately. Bibliographic indices, author contact digits, pagination and equation/figure numbers are identifiers, not measured claims. Extended JISA audit results explicitly separate.',
               'paper_text_changed': False, 'numbers': numbers, 'reopened_decisions': decisions}
    write(BASE / 'paper_vs_repo.json', payload)
    ledger = json.loads((ROOT / 'data/research/spend_ledger.json').read_text())
    write(BASE / 'accounting.json', {'cumulative_booked_usd': ledger['spent_usd'], 'cap_usd': 10,
        'new_model_requests': 0, 'new_rpc_requests': 0, 'new_paid_cost_usd': 0,
        'git_network_operations': 'one canonical fetch; Git transport is not a metered RPC/model call',
        'reservations_count': len(ledger['reservations']), 'ledger_sha256': hashlib.sha256((ROOT / 'data/research/spend_ledger.json').read_bytes()).hexdigest()})
    lines = ['# Canonical-history paper versus repository map', '', payload['inventory_scope'], '',
             'No paper edits. No empirical promotion from fixture results, source declarations, model inputs or proxy classifiers.', '',
             '**Correction to supplied premise:** the early CSV contains246 parsed unique records;248 physical data lines include two blanks. Fifteen hashes are malformed. Eight chains occur in all four CSV versions. This does not authenticate the claimed study.', '',
             '## Numerical map', '', '| Paper number/assertion | Verdict | Honest replacement and scope | Evidence |', '|---|---|---|---|']
    for row in numbers:
        lines.append('| ' + ' | '.join(str(row[k]).replace('|', '/') for k in ('paper', 'verdict', 'replacement', 'evidence')) + ' |')
    lines += ['', '## Reopened registry decisions', '', '| Claim | Status / paper verdict | Evidence decision | Single next input bundle |', '|---|---|---|---|']
    for row in decisions:
        lines.append(f"| {row['id']} | {row['status']} / {row['paper_verdict']} | {row['reason']} | {row['missing_input']} |")
    lines += ['', '## Result lineage and limits', '',
        '- `manifest.json` binds every cached upstream file to a full commit, Git blob identity and SHA-256; `cohort_history.json` records all four distinct fixed-CSV blobs across53 commits/two advertised branches. No assertion about unadvertised/private/unreachable history.',
        '- Original115 GT JSONs first added Apr3 are physically separate from48 Oct6 reconstructions. They contain114 unique hashes, all present in frozen231. This recovers genuine historical annotations, not complete paper-standard adjudication.',
        '- The115-target/114-transaction localization denominator includes duplicate SorStaking. The evaluator can count one transaction twice. Reported7/115 cannot be reinterpreted as seven distinct transaction hits without raw predictions.',
        '- Oct6 reentrancy artifact identifies213 input rows but names fca6b99 (whose committed CSV has231). Its SHA256 exactly matches CRLF rendering of the213-row later blob; no byte hash is silently normalized. The metrics remain null because no trace bundles were evaluated.',
        '- `reruns/50853*/` reproduces the older .8593 [.8223,.8950] feature heuristic. `reruns/8e02*/` reproduces .7586 [.7071,.8040] out-of-fold feature classification. Each run freezes exact source/input bytes and default parameters; all network calls prohibited. Neither invokes actual LLMs, static tools or SSTORE detector.',
        '- Seven of eight current recorded scorer rows reproduce exactly. -TIG differs (TP128/FN103 instead of129/102). Difference is reported, not repaired by threshold or weight changes. The old strict .859 table is historical, not an alternative headline for the newer CV run.',
        '- `SYNTHETIC_DO_NOT_CITE` correctly rejects label-reading legacy outputs. Its later statement that .969 is real is stale; trust executable method and frozen inputs over README/result labels. `DATASET_INTEGRITY.md` also still describes231 while HEAD contains183.',
        '- Main-result .759 and older .859 were computed by code on stored features; that is stronger than a literal number but weaker than authenticated end-to-end experimental evidence. Ground-truth quality remains a separate requirement.',
        '- TableVI weighted means also differ slightly from products of rounded displayed components; without unrounded observations/aggregation this is rounding ambiguity, not grounds to invent corrected empirical values.',
        '- Existing13 VERIFIED claims retain their previously documented implementation/sample scopes. The18 reopened publication claims remain UNVERIFIABLE, now with explicit contradiction/support verdicts and recovered evidence.',
        '', '## Accounting and review', '',
        f"New paid/model/RPC calls:0. New paid spend:$0. Cumulative conservative ledger:${ledger['spent_usd']:.6f} / $10; no change to ledger. Fetch and offline arithmetic incur no provider charges.",
        '', 'Kluster waived for local development only; before any PR or push, repository AGENTS.md rules apply in full and Kluster review is re-enabled. No push performed.',
        '', 'Per-decision commits and post-commit full-suite records are published in `verification.json` after decisions complete. Original201 test-source digests are checked at every gate.']
    (BASE / 'PAPER_VS_REPO.md').write_bytes(('\n'.join(lines) + '\n').encode())
    print('Mapped', len(numbers), 'numeric assertion groups; proposed', len(decisions), 'evidence decisions')


if __name__ == '__main__':
    build()
