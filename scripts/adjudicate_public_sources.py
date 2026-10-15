"""Record explicitly reviewed public-source consensus without fictitious reviewers.

The mappings below are dataset annotations grounded in quoted original analyses,
never detector returns. Runtime predictions are produced separately by execution.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmark.research_protocol import bind, write_json, read_bound, source_text, admit
from scripts.rebuild_authentic_cohort import BASE

CASES = {
'0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa': {
    'name':'Orion Protocol','vuln_type':'Reentrancy','reentrancy_label':True,
    'swc_registry_classification':'SWC-107','dasp_classification':'Reentrancy','uncategorized':False,
    'reason':'BlockSec identifies reentry in _doSwapTokens and resulting USDT balance miscalculation. PeckShield independently identifies reentry in ExchangeWithOrionPool. The two reports identify the same Ethereum exploit transaction; flash-loan use is financing, not the adjudicated root cause.',
    'excerpts':[
        'The root cause is due to a reentrancy issue exists in the PoolFunctionality._doSwapTokens function',
        'The @orion_protocol is hacked due to a reentrancy issue in its core contract: ExchangeWithOrionPool.']},
'0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d': {
    'name':'Euler Finance','vuln_type':'Missing collateral health check','reentrancy_label':False,
    'swc_registry_classification':'','dasp_classification':'','uncategorized':True,
    'reason':'BlockSec attributes the exploit to a missing liquidity check in donateToReserves. PeckShield explicitly says the donation must leave the donor over-collateralized. Their independent mechanism accounts agree on an accounting/solvency check failure, not reentrancy. No SWC/DASP code is forced onto this DeFi-specific invariant failure.',
    'excerpts':[
        'The root cause is due to the lack of liquidity check in the function donateToReserves()',
        'Specifically, the donateToReserves needs to ensure the donator is still over-collateralized.']},
'0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c': {
    'name':'Inverse Finance','vuln_type':'Oracle price manipulation','reentrancy_label':False,
    'swc_registry_classification':'','dasp_classification':'','uncategorized':True,
    'reason':'BlockSec identifies manipulation of the oracle used by Inverse. PeckShield explains that LP pricing misuses manipulable pool balances. Both independently diagnose an oracle-price dependency; the flash loan magnifies it. It is not labeled reentrancy or assigned an unrelated SWC category.',
    'excerpts':[
        'The root cause is that the price oracle utilized by Inverse Finance has been manipulated.',
        'The hack is made possible due to the price oracle manipulation, which misuses the balances of assets in the pool']},
'0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb': {
    'name':'Zunami Protocol','vuln_type':'Oracle price manipulation','reentrancy_label':False,
    'swc_registry_classification':'','dasp_classification':'','uncategorized':True,
    'reason':'CertiK explains inflation of UZD balances through manipulated asset pricing. PeckShield independently diagnoses donation-based miscalculation of price. Both link the transaction to the same Zunami incident. The consensus class is oracle price manipulation; no generic flash-loan label or unrelated SWC code is substituted.',
    'excerpts':[
        'The attacker was able to inflate their UZD balance 3x by taking advantage of the way in which UDZ is calculated.',
        'It is a price manipulation issue, which can be exploited by donation to incorrectly calculate the price']}
}


def core_consensus():
    rows = json.loads((BASE/'candidate_pool.json').read_text())
    by_id = {r['txn_hash']:r for r in rows}
    accepted = []
    for tx, case in CASES.items():
        row = by_id[tx]
        observations = []
        for source, excerpt in zip(row['sources'],case['excerpts']):
            text = source_text(read_bound(source['artifact'],ROOT))
            if excerpt.casefold() not in text.casefold():
                raise ValueError('Reviewed mechanism excerpt does not match cached primary source')
            observations.append({'publisher_id':source['publisher_id'],'source_url':source['url'],
                'source_artifact':source['artifact'],'vulnerability_class':case['vuln_type'],
                'mechanism_excerpt':excerpt})
        annotation = {'schema':1,'mode':'public-source-consensus-v1','adjudication_author':'Codex',
            'not_independent_human_review':True, 'authorization':'User explicitly authorized two independent security publishers agreeing on the vulnerability class, with Codex reasoning documented',
            'txn_hash':tx,'chain':row['chain'],'is_exploit':True,'vuln_type':case['vuln_type'],
            'adjudication_basis':case['reason'],'independent_observations':observations,
            'reentrancy_label':case['reentrancy_label'],'swc_registry_classification':case['swc_registry_classification'],
            'dasp_classification':case['dasp_classification'],'uncategorized':case['uncategorized']}
        target = BASE/'annotations'/(tx+'.json')
        write_json(target,annotation)
        row['annotation_record'] = bind(target,ROOT)
        rpc = BASE/'rpc'/row['chain']/(tx+'.json')
        if rpc.exists():
            row['rpc'] = bind(rpc,ROOT)
        decision = admit(row,ROOT)
        accepted.append({'txn_hash':tx,**decision})
        row['incident_id'] = 'reviewed:'+case['name']
    write_json(BASE/'candidate_pool.json',rows)
    write_json(BASE/'core_consensus_audit.json',accepted)
    print('Public-consensus adjudications',len(accepted),'accepted',sum(r['accepted'] for r in accepted),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core',action='store_true')
    if parser.parse_args().core:
        core_consensus()
