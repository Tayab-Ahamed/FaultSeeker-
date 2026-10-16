"""Software regressions for candidate extraction; never benchmark evidence."""
import gzip
import io
import json
from pathlib import Path
import zipfile
import pytest

from benchmark import import_defihacklabs_github as github
from benchmark.import_public_incidents import normalize_incident
from benchmark.research_protocol import read_bound


def imported(monkeypatch, text):
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as zf:
        zf.writestr('DeFiHackLabs-main/src/test/2023-02/incident.sol',text)
    monkeypatch.setattr(github,'download_zip',lambda url:archive.getvalue())
    return github.import_github_candidates()[0]


def sushi_source():
    root=Path(__file__).resolve().parents[1]
    cases=json.loads((root/'reports/cohort_rebuild_v2/consensus_cases.json').read_text())
    case=next(c for c in cases if c['id']=='57b8f74c990575c9')
    return gzip.decompress(read_bound(case['poc_artifact'],root)).decode('utf-8')


def test_real_sushi_calldata_prefixes_are_not_github_transaction_candidates(monkeypatch):
    hashes={r['candidate_tx_hash'] for r in imported(monkeypatch,sushi_source())}
    assert '0x04b166e7b4ab5105a8e9c85f08f6346de1c66368687215b0e0b58d6e5002bc32' in hashes
    assert '0x01514910771af9ca656af840dff83e8264ecf986ca010000017fa9385be102ac' not in hashes
    assert '0x01514910771af9ca656af840dff83e8264ecf986ca01000001f9a001d5b2c7c5' not in hashes


def test_real_sushi_calldata_prefixes_are_not_public_incident_candidates():
    hashes=set(normalize_incident({'poc_code':sushi_source()})['transaction_hashes'].split('|'))
    assert '0x04b166e7b4ab5105a8e9c85f08f6346de1c66368687215b0e0b58d6e5002bc32' in hashes
    assert '0x01514910771af9ca656af840dff83e8264ecf986ca010000017fa9385be102ac' not in hashes
    assert '0x01514910771af9ca656af840dff83e8264ecf986ca01000001f9a001d5b2c7c5' not in hashes


def test_each_transaction_uses_its_own_chain_and_unlinked_hash_stays_unresolved(monkeypatch):
    ethereum='0x'+'11'*32
    bsc='0x'+'22'*32
    unresolved='0x'+'33'*32
    text=f'// https://etherscan.io/tx/{ethereum}\n// https://bscscan.com/tx/{bsc}\n// tx {unresolved}'
    rows=imported(monkeypatch,text)
    assert {(r['candidate_tx_hash'],r['candidate_chain']) for r in rows}=={
        (ethereum,'eth'),(bsc,'bsc'),(unresolved,'unknown')}
    assert next(r for r in rows if r['candidate_tx_hash']==unresolved)['supported_chain'] is False


def test_same_hash_referenced_on_two_chains_retains_both_pending_candidates(monkeypatch):
    tx='0x'+'44'*32
    rows=imported(monkeypatch,f'https://etherscan.io/tx/{tx}\nhttps://bscscan.com/tx/{tx}')
    assert {(r['candidate_tx_hash'],r['candidate_chain']) for r in rows}=={(tx,'eth'),(tx,'bsc')}
    assert all(r['merge_status']=='staged_not_merged' for r in rows)


def test_exact_explorer_host_does_not_shadow_optimism_or_trust_suffix(monkeypatch):
    tx='0x'+'55'*32
    assert imported(monkeypatch,f'https://optimistic.etherscan.io/tx/{tx}')[0]['candidate_chain']=='optimism'
    assert imported(monkeypatch,f'https://etherscan.io.attacker.test/tx/{tx}')[0]['candidate_chain']=='unknown'


def test_phalcon_per_transaction_chain_reference(monkeypatch):
    tx='0x'+'66'*32
    assert imported(monkeypatch,f'https://phalcon.blocksec.com/tx/bsc/{tx}')[0]['candidate_chain']=='bsc'


@pytest.mark.parametrize('separator',['\n','\t','\r','\u2028'])
def test_decoded_nested_incident_separators_preserve_legitimate_hash(separator):
    tx='0x'+'ab'*32
    row={'metadata':[{'reference':separator+tx}]}
    assert normalize_incident(row)['transaction_hashes']==tx
