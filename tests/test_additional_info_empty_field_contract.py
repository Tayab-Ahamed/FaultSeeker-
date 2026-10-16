"""Software regressions for optional fields; never model-completion evidence."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.modules.setdefault('readline', None)

import pytest

from faultseeker.function_analysis.additional_info_schema import (
    AdditionalInfoSchemaError, normalize_additional_info,
)
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
from faultseeker.prompts.function_analysis.worker_prompts import WorkerPrompts


def saved_request():
    root = Path(__file__).resolve().parents[1]
    path = root / 'reports/cohort_rebuild_v2/gateway_runs/20261016T105155-5f843897/calls/call-007.json'
    record = json.loads(path.read_text(encoding='utf-8'))
    return json.loads(record['response']['choices'][0]['message']['content'])


def analyzer_for(request):
    analyzer = FunctionAnalyzer.__new__(FunctionAnalyzer)
    analyzer.function_prompts = WorkerPrompts()
    analyzer.function_call_info_summary = {}
    queries, lookups = [], []
    def query(prompt):
        queries.append(prompt)
        return deepcopy(request)
    analyzer.generation_agent = SimpleNamespace(query=query)
    def calls(reference):
        lookups.append(('function_call', deepcopy(reference)))
        return [deepcopy(reference)]
    analyzer._retrieve_function_calls = calls
    analyzer._retrieve_children_calls = lambda *args: lookups.append(('children_calls', args))
    analyzer._retrieve_source_code = lambda *args: lookups.append(('source_code', args))
    analyzer.fundflow_analysis = {'balance_change': {}}
    return analyzer, queries, lookups


def test_production_prompt_explicitly_defines_absent_optional_field_encoding():
    prompt = WorkerPrompts().retrieve_additional_info
    assert 'unavailable or unneeded' in prompt
    assert 'omit the field or use []' in prompt
    assert 'Never use "" or null' in prompt


def test_exact_recorded_empty_string_rejects_atomically_before_any_lookup():
    request = saved_request()
    original = deepcopy(request)
    assert request['source_code'] == '' and len(request['function_call']) == 5
    analyzer, queries, lookups = analyzer_for(request)
    with pytest.raises(AdditionalInfoSchemaError, match='source_code: function reference list required'):
        analyzer._retrieve_additional_info('Software replay of the recorded request')
    assert len(queries) == 1 and lookups == []
    assert request == original


@pytest.mark.parametrize('encoding', ['omitted', 'empty-list'])
def test_synthetic_supported_empty_field_variants_retain_all_supplied_owners(encoding):
    request = saved_request()
    if encoding == 'omitted':
        del request['source_code']
    else:
        request['source_code'] = []
    original = deepcopy(request)
    expected = request['function_call']
    assert normalize_additional_info(request)['function_call'] == expected
    analyzer, queries, lookups = analyzer_for(request)
    result = analyzer._retrieve_additional_info('Software-only supported empty-field variant')
    assert result['function_call'] == expected
    assert lookups == [('function_call', reference) for reference in expected]
    assert len(queries) == 1 and request == original


@pytest.mark.parametrize('value', ['', None])
def test_synthetic_invalid_optional_field_encodings_still_reject_without_repair(value):
    request = saved_request()
    request['source_code'] = value
    analyzer, queries, lookups = analyzer_for(request)
    with pytest.raises(AdditionalInfoSchemaError):
        analyzer._retrieve_additional_info('Software-only invalid empty-field variant')
    assert len(queries) == 1 and lookups == []
