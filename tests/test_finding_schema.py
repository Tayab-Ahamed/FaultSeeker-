import copy
import math
import pytest
from faultseeker.function_analysis.finding_schema import normalize_findings,validate_finding_order

MEMO={'withdraw::0xAbC':[{'depth':[0,1]},{'depth':[0,2,3]}], 'Deposit(uint256)::0xdef':[{'depth':[0]}], 'empty::0x123':[]}

def test_normalizes_legacy_and_dict_against_observed_identity():
 result=normalize_findings({'withdraw_0xABC':['observed write',0], 'Deposit(uint256)_0xDEF':{'evidence':'observed call','confidence_score':.7}},MEMO)
 assert result=={'withdraw_0xabc':{'evidence':'observed write','confidence_score':0.,'depth':3},'Deposit(uint256)_0xdef':{'evidence':'observed call','confidence_score':.7,'depth':1}}

def test_empty_findings_valid():assert normalize_findings({},MEMO)=={}

@pytest.mark.parametrize('key',['withdraw_0x999','Withdraw_0xabc','madeup_0xabc','empty_0x123','withdraw::0xabc','withdraw'])
def test_unobserved_or_malformed_identity_rejected(key):
 with pytest.raises(ValueError):normalize_findings({key:['evidence',.8]},MEMO)

@pytest.mark.parametrize('score',[True,False,float('nan'),float('inf'),-float('inf'),-0.1,1.1,100,'0.8',None])
def test_invalid_confidence_rejected(score):
 with pytest.raises(ValueError):normalize_findings({'withdraw_0xabc':['evidence',score]},MEMO)

@pytest.mark.parametrize('value',[[' ',.8],['evidence'],['evidence',.8,'extra'],{'evidence':[],'confidence_score':.8},{'evidence':'ok'},None])
def test_invalid_record_rejected(value):
 with pytest.raises(ValueError):normalize_findings({'withdraw_0xabc':value},MEMO)

def test_duplicate_canonical_identity_rejected():
 with pytest.raises(ValueError):normalize_findings({'withdraw_0xabc':['one',.5],'withdraw_0xABC':['two',.7]},MEMO)

def test_whole_response_rejected_without_mutating_inputs():
 response={'withdraw_0xabc':['valid',.8],'missing_0xabc':['invalid',.7]};before=copy.deepcopy((response,MEMO))
 with pytest.raises(ValueError):normalize_findings(response,MEMO)
 assert (response,MEMO)==before

def test_function_with_underscore_and_tuple_legacy():
 result=normalize_findings({'withdraw_funds_0xABC':('proof',1)}, {'withdraw_funds::0xabc':[{'depth':[0,1]}]})
 assert result['withdraw_funds_0xabc']['depth']==2

@pytest.mark.parametrize('response',[[],None,'{}',42])
def test_response_must_be_mapping(response):
 with pytest.raises(ValueError):normalize_findings(response,MEMO)

def test_order_requires_exact_permutation():
 assert validate_finding_order(['b','a'],{'a':{},'b':{}})==['b','a']
 assert validate_finding_order([],{})==[]

@pytest.mark.parametrize('order',[[],['a'],['a','a'],['a','c'],['A','b'],('a','b'),[1,'b'],None])
def test_invalid_order_rejected(order):
 with pytest.raises(ValueError):validate_finding_order(order,{'a':{},'b':{}})


def test_huge_out_of_range_integer_is_value_error():
 with pytest.raises(ValueError):normalize_findings({'withdraw_0xabc':['evidence',10**400]},MEMO)

@pytest.mark.parametrize('offered',[None,42])
def test_invalid_offered_container_is_value_error(offered):
 with pytest.raises(ValueError):validate_finding_order([],offered)
