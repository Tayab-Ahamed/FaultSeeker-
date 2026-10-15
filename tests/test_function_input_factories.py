"""Production function analysis can use real verified I/O adapters without global patches."""
import sys
sys.modules['readline']=None

def test_input_factories_cover_all_roles_and_verified_source(tmp_path):
    from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
    from benchmark.verified_source_inputs import VerifiedSourceDownloader
    from benchmark.research_protocol import bind
    from scripts.run_train_production import ROOT
    from faultseeker.utils.agent import UniversalAgent
    roles=[]
    def agent_factory(task,role):
        roles.append(role)
        return UniversalAgent(task,'gpt-4o-mini',api_key='unused-in-offline-construction')
    source=VerifiedSourceDownloader.factory(root=ROOT,evidence_binding=bind(ROOT/'reports/cohort_rebuild_v2/localization_sources/evidence.json',ROOT),train_identity='eth:0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428')
    analyzer=FunctionAnalyzer(agent_factory=agent_factory,contract_downloader_factory=source)
    assert set(roles)=={'reasoning_agent','generation_agent','processing_agent','organization_agent','children_call_filtering','ranking_agent'}
    address='0x2320a28f52334d62622cc2eafa15de55f9987ed9'
    analyzer.contract_info=analyzer.contract_downloader_factory('eth',[address]).run()
    actual=analyzer._retrieve_source_code(address,'0x5dcb7ab2')
    assert actual
    assert any('depositAdditionalToFNFT' in item['source_code'] for item in actual)
