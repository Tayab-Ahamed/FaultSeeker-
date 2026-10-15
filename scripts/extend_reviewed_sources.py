"""Materialize explicitly reviewed source pairs, not detector predictions.

Source quotes are checked against cached original artifacts before annotation.
The curated decisions here are public-source consensus authored by Codex.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.research_protocol import bind, source_text, write_json
from scripts.rebuild_authentic_cohort import BASE, cached_meta


def extend():
    cases = json.loads((BASE/'consensus_cases.json').read_text())
    reviews = json.loads((BASE/'manual_consensus_reviews.json').read_text())
    rows = json.loads((BASE/'candidate_pool.json').read_text())
    metas = cached_meta()

    def source(publisher, url, quote, local=None):
        artifact = bind(BASE/'web'/local if local else ROOT/metas[url]['file'], ROOT)
        text = source_text((ROOT/artifact['path']).read_bytes())
        if quote.casefold() not in text.casefold():
            raise ValueError('Explicitly reviewed quote absent from original cache: '+publisher)
        return {'publisher':publisher,'url':url,'artifact':artifact,'text':text}, quote

    def add(case_id, name, label, hashes, observations, reason, reentrant=False):
        if any(c['id']==case_id for c in cases):
            return
        known = {r['txn_hash'] for r in rows}
        if not set(hashes)<=known:
            raise ValueError('Unknown transaction identity; add and verify genuine lead first')
        sources = [s for s,q in observations]
        cases.append({'id':case_id,'candidate_hashes':hashes,'sources':sources,
            'poc_artifact':sources[0]['artifact'],
            'identity_evidence_kind':'Original publisher incident analysis, not a PoC',
            'poc_context':'Transaction role explicitly reviewed in the original incident analysis'})
        reviews.append({'case_id':case_id,'incident_name':name,'reviewed_by':'Codex',
            'decision':'APPROVE_SOURCE_CONSENSUS','consensus':True,'vulnerability_class':label,
            'chain':{'Grim Finance':'fantom','Hundred Finance Gnosis':'gnosis'}.get(name,'eth'),
            'reentrancy_label':reentrant,'attack_transaction_hashes':hashes,'reasoning':reason,
            'independence_basis':'Different security research organizations publishing original mechanism analyses. Shared victim and public transaction data do not constitute dependence; no cited observation is a republication of the other.',
            'observations':[{'publisher':s['publisher'],'url':s['url'],'quote':q} for s,q in observations]})

    add('reviewed-grim-2021','Grim Finance','Reentrancy',
        ['0x19315e5b150d0a83e797203bb9c957ec1fa8a6f404f4f761d970cb29a74a5dd6'],[
        source('SlowMist','https://slowmist.medium.com/analysis-of-the-grim-finance-hack-bc440108b069',
            'It failed to check the validity of the token passed in by the user and did not have a reentrancy guard.', 'slowmist_0.txt'),
        source('Halborn','https://www.halborn.com/blog/post/explained-the-grim-finance-hack-december-2021',
            'A function vulnerable to reentrancy does not properly update its internal state before sending a transfer to an external contract.')],
        'SlowMist explicitly identifies this Fantom exploit execution and the depositFor callback flaw. Halborn independently explains the same nested reward-accounting reentry in the December 2021 Grim incident; its analysis cites the protocol, not SlowMist. The second article is incident corroboration, not a second assertion of the exact hash.',True)
    add('reviewed-revest-2022','Revest Finance','Reentrancy',
        ['0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428'],[
        source('SlowMist','https://slowmist.medium.com/revest-finance-incident-analysis-6fcd9b6be207',
            'Therefore, the attacker used a reentrancy attack to modify the information of the NFT that had been minted.', 'slowmist_1.txt'),
        source('BlockSec','https://blocksec.com/blog/revest-finance-vulnerabilities-more-than-re-entrancy',
            "the attacker re-enters the Revest contract's depositAdditionalToFNFT function via the FNFTHandler 's call-back mechanism inherited from the ERC-1155 token standard")],
        'SlowMist names this among the four actual exploit transactions. BlockSec independently reconstructs the executed ERC1155 callback attack. Its additional hypothetical zero-day PoC is explicitly separate and is not treated as a historical transaction or another admitted row.',True)
    add('reviewed-hundred-gnosis-2022','Hundred Finance Gnosis','Reentrancy',
        ['0x534b84f657883ddc1b66a314e8b392feb35024afdec61dfe8e7c510cfac1a098'],[
        source('SlowMist','https://slowmist.medium.com/another-day-another-reentrancy-attack-5cde10bbb2b4',
            'The borrowFresh function within the Hundred Finance contract checks the funds after theyâ€™ve been transferred.', 'slowmist_hundred_indexed.txt'),
        source('Knownsec','https://medium.com/@Knownsec_Blockchain_Lab/knownsec-blockchain-lab-hundred-and-agave-flash-loan-attack-analysis-ba45ee6c06f9',
            'This callback would have directly led to the creation of the reentry vulnerability', 'knownsec_hundred_indexed.txt')],
        'Both original reports explicitly name this Gnosis exploit hash and analyze ERC677 callbacks before borrow accounting. Knownsec and SlowMist are separate security organizations. This is the March 2022 incident, not the distinct April 2023 Optimism donation exploit.',True)
    add('reviewed-beanstalk-execution-2022','Beanstalk','Flash-loan governance capture',
        ['0xcd314668aaa9bbfebaf1a0bd2b6553d01dd58899c508d4729fa7311dc5d33ad7'],[
        source('CertiK','https://www.certik.com/blog/revisiting-beanstalk-farms-exploit',
            'The exploiter deposited all gained assets from the flash loan into a Beanstalk Diamond contract and voted for the malicious BIP18 proposal.'),
        source('Halborn','https://www.halborn.com/blog/post/explained-the-beanstalk-hack-april-2022',
            'the attacker was able to use a flashloan to perform a large deposit to the Diamond contract.')],
        'CertiK explicitly distinguishes proposal setup transaction 68cdec from execution cd314; only execution is admitted here. Halborn independently analyzes flash-loan-funded governance capture. Financing alone is not the annotation: instantaneous voting power and emergency execution are the failed governance invariant.')

    write_json(BASE/'consensus_cases.json', cases)
    write_json(BASE/'manual_consensus_reviews.json', reviews)
    print('Explicit manual consensus decisions',len(reviews))


if __name__=='__main__':
    extend()
