"""Resume-safe, per-claim evidence commits, gated by a real offline full suite."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmark.claim_registry import CLAIMS,claim_report
from benchmark.claim_closure import apply_closure

BASE='reports/claim_closure/'
LOCAL=BASE+'local_acceptance.json'
COHORT=BASE+'cohort/row_decisions.json'
PAPER=BASE+'paper_requirements.json'
MATH=BASE+'numeric_constraints.json'
ENV=BASE+'environment.json'

VERIFIED={1,2,9,10,11,12,16,19,20,23,24,26,31}
REASONS={
1:'A public upstream repository and its Apache-2.0 license were fetched and cached. This is availability proof, not publication of this local branch.',
2:'All 201 baseline cases passed and every original test source matches its frozen digest.',
3:'The rebuilt corpus has 231 candidates, zero accepted provenance chains, and 15 additional rows are absent. Qualified independent annotation attestations are missing for every candidate.',
4:'Two independent cached corroborating research sources and two independent annotation records are not available per row. Only one published PoC source was recovered for each of two replayed rows.',
5:'The unadjudicated CSV has eight chains and 132/231 Ethereum rows; no accepted 246-row ten-chain corpus establishes the stated 47.6 percent share.',
6:'Distinct legacy vulnerability strings are observable, but their taxonomy assignment and independent label adjudication are not attested. String counts alone do not verify more than 80 confirmed vulnerability types.',
7:'The original class labels and trace-size observations are unadjudicated and do not establish the published proportions over 246 accepted rows. No labels were changed to meet percentages.',
8:'Legacy reentrancy-string matches are not independent ground truth; the required accepted 246-row corpus and its stated 18 positives are unavailable.',
9:'Production paper-mode storage signals, mutex filtering, reverted-frame handling and delegatecall storage ownership pass behavioral and compiled execution tests.',
10:'Each specified storage weight contributes through executed detector evidence; weights were not tuned during this review.',
11:'All five tier boundaries and lower neighbors pass, including production paper-profile activation.',
12:'The three structural terms, 0.75 penalty and 0.80 cap fire in the real fallback path under tests.',
13:'No adjudicated positive/negative evaluation cohort or raw Table V outcomes exist. The metric runner now uses the paper HIGH_RISK/CONFIRMED positive rule, but no paper precision/recall/F1 is inferred from two unadjudicated samples. Pooled integer-count constraints also require clarification.',
14:'The 17/29 percentage-point differences require paired detector predictions on the same frozen adjudicated cohort. Those outcomes are absent; the corrected repeated-address baseline is implemented and tested.',
15:'The paper names legitimate Compound cToken recursion but gives no exact transaction. Compoundv2 inflation-attack CSV rows are not a substitute benign case study.',
16:'Tier-2 confidence/evidence gating demonstrably dispatches escalation and records both attempts at the provider boundary.',
17:'Six-family live conformance cannot be established: Anthropic and DashScope credentials are absent and no local Ollama endpoint/model was reachable. Other key presence is not authentication proof.',
18:'No preregistered authenticated 100-transaction 5:3:2 paired workload, observed usage, quality/rank outcomes or verified pricing snapshot is available. The paper cost inputs imply 35 percent overall, not the Tier-2-only 58 percent figure.',
19:'Executed deterministic Stage 1 constructors and fund-flow analysis make no model calls and remain keyless.',
20:'Complete-coverage BENIGN bypass occurs before Stage 2 model setup; EXPLOIT locking and UNCERTAIN escalation pass production-flow tests.',
21:'There is no independently verified benign study pool or preregistered paired prefilter latency experiment. The BENIGN skip mechanism alone cannot establish a 40 percent population rate.',
22:'All local analysis roles execute under boundary tests, but no authenticated function-localization evaluation exists. Verified contract-source access, source-linked ground truth and live model-quality observations are absent.',
23:'The executed four-component weighted formula is a relative heuristic score; incompatible calibration schemas are rejected rather than presented as validated probabilities.',
24:'All five first-checkpoint guidance actions affect downstream state and second-checkpoint rejection removes findings with an audit record and contract/function identity checks.',
25:'Observed Ethereum method and batch responses are recorded. The configured endpoint does not establish other-chain archive/trace support or sustained multi-provider recovery. Native opcode logging is rejected, while the tested Ethereum Anvil workaround works.',
26:'Two historical Ethereum transactions have hash-checked signed block-prefix replay, matching receipts, full opcode captures and verified storage ownership; all compiled fixtures also pass. This does not certify other chains or incident labels.',
27:'No recorded authorized challenged-request sample, real challenge denominator or live recovery outcomes establish 23 percent. The challenge transport/case configuration is absent; fixture tests are not a measured bypass rate.',
28:'Table VI needs observed PMS/CES/TCS/LCS and overall scores by adjudicated category over the authentic study. No such production vectors exist. The new component aggregator is tested; receipt gas/call averages are explicitly not Table VI.',
29:'No original 20-case selection, guidance policy, source-linked ranking ground truth or paired outcomes establish 68 to 81 percent. Ordinary binary top-1 accuracy over 20 items has five-point steps; another aggregation requires an explicit protocol.',
30:'The offline acceptance/closure entry point executes, but exact reproduction of the published Table V, Fig.6 and Table VI cannot be demonstrated without the original authenticated studies and inputs. Infrastructure tests do not verify those unavailable outputs.',
31:'The current Python 3.11.9 suite executes and Docker COPY inputs/layout exist. This scope does not assert an image build or untested interpreter versions; the Docker daemon was unavailable.'}

UNMET={
3:['246 accepted row manifests','Two qualified independent label attestations per row','15 missing candidate rows'],
4:['Two independent cached research reports per row','Independent annotator identities and consensus records'],
5:['Authenticated ten-chain 246-row population','Measured chain shares on that population'],
6:['Adjudicated SWC/DASP-aligned vulnerability taxonomy'],
7:['Frozen class-mapping protocol','Authentic trace-size/class labels for all 246 rows'],
8:['Independent reentrancy labels and exact positive/negative membership'],
13:['Frozen adjudicated evaluation set','Raw integer confusion outcomes','Declared pooling/averaging protocol'],
14:['Paired predictions for all three detector variants on identical adjudicated records'],
15:['Exact legitimate Compound cToken transaction and source corroboration'],
17:['Anthropic live access','DashScope live access','Installed reachable Ollama model','Six-family live conformance observations'],
18:['Preregistered 100-case workload','Sourced dated prices','Paired observed query usage and quality/rank outcomes'],
21:['Authenticated benign population','Paired production latency and bypass observations'],
22:['Verified source-linked function ground truth','Live model/localization quality evaluation'],
25:['Remaining-chain trace/archive endpoints and observations','Live multi-provider outage/recovery evidence'],
27:['Authorized challenge cases and strategy configuration','Observed challenged-request denominator and recovery outcomes'],
28:['Observed production confidence vectors for authenticated study records','Predeclared function/transaction aggregation'],
29:['Original or preregistered 20-case guidance study','Ground-truth function rankings','Explicit accuracy aggregation protocol'],
30:['Authentic inputs and observed outputs for the three published tables/figures']}


def git(*args):
    value=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True)
    if value.returncode:
        raise RuntimeError('Git operation failed: '+args[0])
    return value.stdout.strip()


def check_branch():
    if git('branch','--show-current')!='paper-claims-verified':
        raise RuntimeError('Refusing to work outside paper-claims-verified')
    if git('diff','--cached','--name-only'):
        raise RuntimeError('Index contains unrelated staged work')


def full_suite(label):
    output=ROOT/'build/closure_acceptance';output.mkdir(parents=True,exist_ok=True)
    xml=output/(label+'.xml')
    environment=os.environ.copy()
    for name,key in [('solc','SOLC_BINARY'),('anvil','ANVIL_BINARY'),('cast','CAST_BINARY')]:
        environment[key]=str(ROOT/'build/tools'/(name+'.exe'))
    environment['FAULTSEEKER_RUN_HISTORICAL_REPLAY']='0'
    command="""import sys,socket
sys.modules['readline']=None
original=socket.socket.connect
def local_only(self,address):
    if isinstance(address,tuple) and address[0] not in ('127.0.0.1','::1','localhost'):
        raise OSError('Offline acceptance prohibits external connections')
    return original(self,address)
socket.socket.connect=local_only
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
"""
    with (output/(label+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-c',command,str(ROOT/'tests'),'-q','--tb=short',
            '--junitxml='+str(xml)],cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('Full suite failed; inspect build/closure_acceptance/'+label+'.log')
    lookup={str(p.relative_to(ROOT)).replace('\\','/').removesuffix('.py').replace('/','.'):
            str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'tests').glob('test_*.py')}
    outcomes={}
    for case in ET.parse(xml).iter('testcase'):
        module=case.attrib['classname']
        matched=next((key for key in lookup if module==key or module.startswith(key+'.')),None)
        if not matched:
            raise RuntimeError('Unmapped real pytest case')
        suffix=module[len(matched):].strip('.').replace('.','::')
        node=lookup[matched]+('::'+suffix if suffix else '')+'::'+case.attrib['name']
        outcomes[node]='failed' if case.find('failure') is not None or case.find('error') is not None else (
                       'skipped' if case.find('skipped') is not None else 'passed')
    baseline=json.loads((ROOT/'benchmark/baseline_tests.json').read_text())
    original=Counter(value for node,value in outcomes.items() if node.split('::')[0] in baseline['source_sha256'])
    if original!={'passed':201}:
        raise RuntimeError('Original 201-case evidence is incomplete')
    print(label+' full suite '+json.dumps(dict(Counter(outcomes.values()))),flush=True)
    return outcomes


def commit_files(number,files,message):
    check_branch()
    git('add','--',*files)
    if not git('diff','--cached','--name-only'):
        return
    git('diff','--cached','--check')
    full_suite('source-claim-'+str(number))
    git('commit','--quiet','-m',message)
    print('Committed '+git('rev-parse','--short','HEAD')+' '+message,flush=True)


def source_commits():
    groups=[
        (13,['benchmark/detector_experiments.py','tests/test_detector_experiments.py',
             'tests/test_compiled_evm_integration.py',BASE+'paper_requirements.json',BASE+'numeric_constraints.json'],
            'claim13: align metric positives and repeated-address baseline with paper'),
        (28,['benchmark/paper_experiments.py','tests/test_table_vi.py'],
            'claim28: aggregate observed confidence components without imputation'),
        (1,['.gitattributes','scripts/acquire_claim_sources.py',BASE+'sources'],
            'claim1: preserve public repository and published source provenance'),
        (30,['benchmark/claim_closure.py','benchmark/run_paper_verification.py','tests/test_claim_closure.py',
             'scripts/finalize_claim_closure.py',BASE+'local_acceptance.json',BASE+'local_snapshot',BASE+'environment.json'],
            'claim30: validate hashed terminal decisions and strict closure reporting')]
    for number,files,message in groups:
        commit_files(number,files,message)


def decision(claim):
    number=claim['id']
    status='VERIFIED' if number in VERIFIED else 'UNVERIFIABLE'
    evidence=[LOCAL]
    if claim['scope']=='DATA':
        evidence += [COHORT,PAPER]
    if number in [13,14,18,29]:
        evidence.append(MATH)
    if number in [17,18,21,22,25,27,29,31]:
        evidence.append(ENV)
    if number==1:
        evidence += [BASE+'sources/public_repository.json',BASE+'sources/public_repository_LICENSE.txt']
    if number==25:
        evidence += [BASE+'rpc_capabilities.json',BASE+'rpc_capability_conclusion.json']
    if number==26:
        evidence += [BASE+'comparison_result.json',BASE+'comparison_attempt_2/historical_replay_summary.json',
                     'reports/historical_replay/final_accounting.json']
    if number in [28,30]:
        evidence += [PAPER,COHORT]
    tests=list(claim['tests'])
    if number==1:
        tests=['tests/test_claim_closure.py::test_publication_snapshot_is_public_and_open_licensed']
    if number==2:
        tests.append('tests/test_reproduction_entrypoints.py::test_original_test_sources_match_the_frozen_baseline_manifest')
    if number in [9,26]:
        tests += ['tests/test_compiled_evm_integration.py::test_compiled_mutex_preserves_actual_lock_transitions',
                  'tests/test_compiled_evm_integration.py::test_compiled_delegatecall_writes_proxy_storage']
    if number==26:
        tests += ['tests/test_historical_fork_replay.py::test_recorded_historical_capture_validates_storage_and_receipt',
                  'tests/test_historical_fork_replay.py::test_recorded_comparison_capture_validates_storage_and_receipt']
    scope=('Code mechanism and its passing behavioral acceptance; not a population-performance claim'
           if claim['scope']=='LOCAL' else 'Current recorded evidence only')
    if number==1:scope='Public upstream source availability; local branch publication not asserted'
    if number==26:scope='Compiled EVM fixtures and two matching-receipt Ethereum historical opcode captures'
    if number==31:scope='Observed Python 3.11.9 execution and Docker COPY/layout checks; no Docker build assertion'
    return {'id':number,'claim':claim['claim'],'status':status,'reason':REASONS[number],
        'verification_scope':scope,'requirements_unmet':UNMET.get(number,[]),
        'human_decision':('; '.join(UNMET[number])+' must be supplied or independently established before reopening.'
                          if number in UNMET else None),
        'acceptance_tests':list(dict.fromkeys(tests)),
        'evidence':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()}
                    for p in dict.fromkeys(evidence)],'session_date':'2026-10-15'}


def close_decisions():
    directory=ROOT/(BASE+'claims');directory.mkdir(exist_ok=True)
    order=[26,25,3,4,5,6,7,8,13,14,15,18,21,27,28,29,17,22,1,2,9,10,11,12,16,19,20,23,24,30,31]
    definitions={row['id']:row for row in CLAIMS}
    for number in order:
        check_branch()
        item=decision(definitions[number])
        path=directory/f'{number:02d}.json'
        data=(json.dumps(item,indent=2)+'\n').encode()
        if path.exists():
            if path.read_bytes()!=data:
                raise RuntimeError('Existing decision differs; review instead of silently replacing')
            continue
        path.write_bytes(data)
        outcomes=full_suite('decision-claim-'+str(number))
        dataset=json.loads((ROOT/COHORT).read_text())
        report=claim_report(outcomes,dataset)
        snapshot=json.loads((ROOT/LOCAL).read_text())
        report['original_test_evidence']=snapshot['original_test_evidence']
        apply_closure(report,outcomes,directory,ROOT)
        progress={'closed_ids':sorted(int(p.stem) for p in directory.glob('*.json')),
                  'latest_claim':number,'latest_status':item['status'],
                  'latest_full_suite':dict(Counter(outcomes.values()))}
        progress_path=ROOT/(BASE+'progress.json')
        progress_path.write_bytes((json.dumps(progress,indent=2)+'\n').encode())
        git('add','--',str(path.relative_to(ROOT)),str(progress_path.relative_to(ROOT)))
        git('diff','--cached','--check')
        git('commit','--quiet','-m',f'claim{number}: close as {item["status"]} with scoped evidence')
        print(f'Closed {number}: {item["status"]} at '+git('rev-parse','--short','HEAD'),flush=True)


if __name__=='__main__':
    if sys.argv[1:]==['--source-commits']:
        source_commits()
    elif sys.argv[1:]==['--close-decisions']:
        close_decisions()
    else:
        raise SystemExit('Use --source-commits or --close-decisions; no implicit writes.')
