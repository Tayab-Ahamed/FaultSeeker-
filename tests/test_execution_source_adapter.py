"""Bound real execution source spans reach actual model evidence prompts."""
import sys
sys.modules['readline']=None
from pathlib import Path
from types import SimpleNamespace
from benchmark.verified_source_inputs import VerifiedSourceDownloader
from benchmark.research_protocol import bind
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
ROOT=Path(__file__).resolve().parents[1]
IDENTITY='eth:0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d'

def factory():
 return VerifiedSourceDownloader.factory(root=ROOT,evidence_binding=bind(ROOT/'reports/cohort_rebuild_v2/localization_sources/evidence.json',ROOT),train_identity=IDENTITY,include_execution_spans=True)

def test_real_bound_delegate_storage_spans_reach_processing_prompt():
 create=factory()
 # These are verified code addresses from the allowed TRAIN source cache.
 owner='0xbb0d4bb654a21054af95456a3b29c63e8d1f4c0a'
 source=create('eth',[owner]);mapping=source.run()[owner]
 candidates=[(selector,records) for selector,records in mapping.items() if any(r.get('executed_source_spans') for r in records)]
 assert candidates
 selector,records=candidates[0]
 spans=[s for r in records for s in r.get('executed_source_spans',[])]
 assert all(s['code_address']==owner for s in spans)
 assert any(s['storage_address']!=owner for s in spans)
 prompts=[]
 def make_agent(task,role):
  def query(prompt,format='json'):
   if role=='generation_agent':return {'source_code':[{'address':owner,'function':selector}]}
   if role=='processing_agent':prompts.append(prompt);return 'Observed execution spans only.'
   raise AssertionError('Unexpected role')
  return SimpleNamespace(query=query)
 a=FunctionAnalyzer(agent_factory=make_agent,contract_downloader_factory=create)
 a.analysis_result=SimpleNamespace(chain='eth');a.contract_info={owner:mapping}
 a.current_task={'task_description':'Inspect the observed implementation','additional_information':'source'}
 a.function_call_info_summary={}
 a._perform_task()
 assert len(prompts)==1
 assert 'executed_source_spans' in prompts[0] and 'start_line' in prompts[0]
 assert owner in prompts[0] and 'not_function_slice' in prompts[0]
 assert source.execution_evidence['capture']['sha256'] in prompts[0]
 assert a.processing_result=='Observed execution spans only.'

def test_identical_content_at_distinct_source_paths_keeps_execution_locations():
 owner='0x'+'11'*20;selector='0x12345678'
 a=FunctionAnalyzer(agent_factory=lambda *args:SimpleNamespace())
 a.contract_info={owner:{selector:[{'path':path,'content':'same content','execution_scope':'not_function_slice','executed_source_spans':[{'source':{'path':path,'start_line':1}}]} for path in ['first.sol','second.sol']]}}
 rows=a._retrieve_source_code(owner,selector)
 assert [row['path'] for row in rows]==['first.sol','second.sol']
 assert all(row['executed_source_spans'][0]['source']['path']==row['path'] for row in rows)
