"""All source lookup paths respect the configured source provenance boundary."""
import sys
sys.modules['readline']=None
from types import SimpleNamespace
from pathlib import Path
import pytest
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer

ROOT=Path(__file__).resolve().parents[1]

def analyzer(factory,monkeypatch):
 def forbidden(*args,**kwargs):raise AssertionError('Live source fallback prohibited')
 monkeypatch.setattr('faultseeker.function_analysis.function_analyzer.ContractDownloader',forbidden)
 a=FunctionAnalyzer(agent_factory=lambda *args:SimpleNamespace(),contract_downloader_factory=factory)
 a.analysis_result=SimpleNamespace(chain='eth');a.contract_info={}
 return a

def test_real_verified_source_factory_handles_uncached_historical_contract(monkeypatch):
 from benchmark.verified_source_inputs import VerifiedSourceDownloader
 from benchmark.research_protocol import bind
 factory=VerifiedSourceDownloader.factory(root=ROOT,evidence_binding=bind(ROOT/'reports/cohort_rebuild_v2/localization_sources/evidence.json',ROOT),train_identity='eth:0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428')
 a=analyzer(factory,monkeypatch)
 result=a._retrieve_source_code('0x2320A28F52334D62622CC2EAFA15DE55F9987ED9','0x5dcb7ab2')
 assert result and any('depositAdditionalToFNFT' in source['source_code'] for source in result)

def test_missing_source_is_cached_without_falling_back_to_live_transport(monkeypatch):
 calls=[]
 def factory(chain,addresses):
  calls.append((chain,addresses));return SimpleNamespace(run=lambda:{})
 a=analyzer(factory,monkeypatch)
 assert a._retrieve_source_code('0xABC','0x11111111')==[]
 assert a._retrieve_source_code('0xabc','0x22222222')==[]
 assert calls==[('eth',['0xabc'])]

def test_configured_source_error_is_propagated_not_replaced_with_live_fetch(monkeypatch):
 def factory(*args):raise ValueError('Bound source digest mismatch')
 a=analyzer(factory,monkeypatch)
 with pytest.raises(ValueError,match='digest mismatch'):a._retrieve_source_code('0xabc','0x11111111')
 assert '0xabc' not in a.contract_info
