"""Pure whole-request validation before any additional-info I/O."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from faultseeker.function_analysis.additional_info_schema import normalize_additional_info,AdditionalInfoSchemaError

A='0x'+'AB'*20
B='0x'+'12'*20

@pytest.mark.parametrize('reference',[
    {'address':A,'function':'withdraw(uint256)'},
    {'address':A,'function_name':'withdraw(uint256)'},
    [A,'withdraw(uint256)'],(A,'withdraw(uint256)'),
    'withdraw(uint256)::'+A,A+'::withdraw(uint256)'])
@pytest.mark.parametrize('field',['function_call','children_calls','source_code'])
def test_supported_reference_shapes_have_one_canonical_representation(reference,field):
    request={field:[reference]};original=deepcopy(request)
    assert normalize_additional_info(request)=={field:[{'address':A.lower(),'function':'withdraw(uint256)'}]}
    assert request==original


def test_legacy_single_source_dictionary_and_empty_requests_are_supported():
    assert normalize_additional_info({})=={}
    assert normalize_additional_info({'source_code':{'address':A,'function_name':'owner'}})=={'source_code':[{'address':A.lower(),'function':'owner'}]}
    assert normalize_additional_info({'children_calls':[],'balance_change':[A,B]})=={'children_calls':[],'balance_change':[A.lower(),B]}


@pytest.mark.parametrize('payload',[None,[], '[]', {'unknown':[]},{'source_code':None},
    {'source_code':'owner::'+A},{'source_code':[['owner',A]]},
    {'source_code':[{'address':'moduleLookup','function':'owner'}]},
    {'source_code':['owner::moduleLookup']},{'children_calls':['callInternalModule::moduleLookup']},
    {'function_call':[{'address':'0x1234','function':'foo'}]},
    {'function_call':[{'address':A,'function':'','extra':1}]},
    {'function_call':[{'address':A,'function':'foo','function_name':'bar'}]},
    {'function_call':[{'address':A,'function':'foo','explanation':'extra'}]},
    {'function_call':[A+'::'+B]},{'function_call':[A+'::foo::bar']},
    {'function_call':[[A,'foo','extra']]},{'function_call':[[A,True]]},
    {'balance_change':A},{'balance_change':{}},{'balance_change':['moduleLookup']},
    {'balance_change':[None]},{'balance_change':['0x123']},
    {'function_call':[{'address':A,'function':'foo'}],'balance_change':'malformed-later-field'}])
def test_any_malformed_field_rejects_whole_request(payload):
    with pytest.raises(AdditionalInfoSchemaError):normalize_additional_info(payload)


def test_real_historical_response_five_rejects_unresolved_module_reference():
    root=Path(__file__).resolve().parents[1]
    path=root/'reports/cohort_rebuild_v2/gateway_runs/20261015T180644-7cc259e6/calls/call-005.json'
    record=json.loads(path.read_text())
    raw=record['response']['choices'][0]['message']['content']
    request=json.loads(raw.split('```json')[1].split('```')[0])
    assert 'callInternalModule::moduleLookup' in request['children_calls']
    with pytest.raises(AdditionalInfoSchemaError,match='address'):
        normalize_additional_info(request)
