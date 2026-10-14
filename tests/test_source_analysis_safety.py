import json
from faultseeker.data_collection.contract_downloader import ContractDownloader
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer


def test_single_line_function_source_is_not_dropped():
    analyzer = FunctionAnalyzer.__new__(FunctionAnalyzer)
    analyzer.contract_info = {'0xabc': {'withdraw': [{'start_line': 1, 'end_line': 1,
                          'path': 'Vault.sol', 'content': 'function withdraw() external { }'}]}}
    assert analyzer._retrieve_source_code('0xabc', 'withdraw')[0]['source_code'].startswith('function')


def test_downloaded_source_cannot_escape_output_directory(monkeypatch, tmp_path):
    monkeypatch.setattr('faultseeker.data_collection.contract_downloader.explorer_call',
        lambda *a: {'status': '1', 'result': [{'ContractName': '../../escaped',
                                             'SourceCode': 'contract Vault {}'}]})
    output = tmp_path/'work'
    ContractDownloader.get_source_code('eth', '0xabc', str(output))
    assert not (tmp_path/'escaped.sol').exists()
    assert list((output/'Implementation').glob('*.sol'))


def test_downloader_preserves_caller_directory_and_unrelated_implementation(monkeypatch, tmp_path):
    output, unrelated = tmp_path/'shared', tmp_path/'Implementation'
    output.mkdir(); unrelated.mkdir()
    (output/'keep.txt').write_text('caller-owned')
    (unrelated/'keep.sol').write_text('contract Keep {}')
    monkeypatch.chdir(tmp_path)
    def capture(chain, address, directory):
        path = __import__('pathlib').Path(directory)/'Fixture.sol'
        path.write_text('contract Fixture { function withdraw() external {} }')
    monkeypatch.setattr(ContractDownloader, 'get_source_code', staticmethod(capture))
    result = ContractDownloader('eth', ['0xabc'], str(output), str(tmp_path/'cache')).run()
    assert (output/'keep.txt').exists()
    assert (unrelated/'keep.sol').exists()
    assert result['0xabc']['withdraw']


def test_production_function_analyzer_cannot_leak_findings_between_transactions(monkeypatch):
    from faultseeker.forensics.result import ForensicsResult
    from faultseeker.function_analysis.function_ranker import RankingResult
    class BoundaryAgent:
        def __init__(self):
            self.memory = []
        def query(self, *args, **kwargs):
            return {}
        def reset_memory(self):
            self.memory.clear()
    monkeypatch.setattr('faultseeker.function_analysis.function_analyzer.build_agent',
                        lambda *args: BoundaryAgent())
    monkeypatch.setattr(ContractDownloader, 'run', lambda self: {})
    analyzer = FunctionAnalyzer(model='fixture-local')
    analyzer.potentially_vulnerable_functions = {'old_0xabc': {'depth': 1, 'evidence':['old transaction'], 'confidence_score':[.9]}}
    result = ForensicsResult(transaction_hash='0xnew', chain='eth')
    txn_seq = {'address_relation': {'directed':True,'multigraph':False,'graph':{},'nodes':[],'edges':[]},
               'address_calls':{},'created_address':[]}
    output = analyzer.run(result, txn_seq, {'transaction_hash':'0xnew'}, RankingResult())
    assert output['finalized_vulnerable_functions'] == []
    assert output['potentially_vulnerable_functions'] == {}
