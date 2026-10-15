"""Real narrowing-loop safety; only model/source analysis boundaries are replaced."""
from types import SimpleNamespace
import pytest
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer


def make_analyzer(response, created=False, candidate_count=6):
    analyzer = FunctionAnalyzer.__new__(FunctionAnalyzer)
    owner = '0x' + '11' * 20
    keys = [('f' + str(i)) if created else ('f' + str(i) + '_' + owner) for i in range(candidate_count)]
    candidates = {key: {'count': 1, 'calls': [], 'address': [owner]} for key in keys}
    analyzer.functions_to_be_inspected = {} if created else candidates
    analyzer.address_calls_with_created_contract_in_params = candidates if created else {}
    analyzer.repeated_patterns = []
    analyzer.fundflow_analysis = {'balance_change': {}}
    analyzer.function_prompts = SimpleNamespace(
        narrow_down_functions='{function_call_to_be_inspected}',
        narrow_down_functions_with_created_contracts='{function_call_to_be_inspected}')
    queries = []
    def query(prompt):
        queries.append(prompt)
        return response(keys) if callable(response) else response
    analyzer.agent = SimpleNamespace(query=query)
    analyzer.children_call_memo = {}
    analyzer.children_call_memo_single = {}
    analyzer.analysis_errors = []
    analyzer.trace = []
    analyzer.txn_seq = {'created_address': []}
    analyzer.potentially_vulnerable_functions = {}
    analyzer.understanding_result = ''
    observed = []
    analyzer._retrieve_related_info = lambda *args: None
    analyzer._function_analysis_init = lambda: observed.append(analyzer.function_call_info_summary['function'])
    return analyzer, keys, queries, observed


@pytest.mark.parametrize('response', [None, 1, 'x', {}, [], ['unknown'], [0],
    lambda keys: {'selected_functions': [keys[0]]},
    lambda keys: [keys[0], keys[0]]])
@pytest.mark.parametrize('created', [False, True])
def test_invalid_narrowing_never_silently_completes_or_discards_candidates(response, created):
    analyzer, keys, queries, observed = make_analyzer(response, created)
    # Invalid selector output must be a typed analysis failure, never an empty
    # success or a KeyError/TypeError after candidates have already been dropped.
    with pytest.raises(ValueError, match='selection|Selection|narrow|Narrow'):
        analyzer._review_function_calls()
    assert observed == []
    candidates = analyzer.address_calls_with_created_contract_in_params if created else analyzer.functions_to_be_inspected
    assert list(candidates) == keys


@pytest.mark.parametrize('created', [False, True])
def test_valid_exact_key_subset_runs_real_selected_function_branch(created):
    analyzer, keys, queries, observed = make_analyzer(lambda keys: [keys[1], keys[3]], created)
    analyzer._review_function_calls()
    expected = [keys[1], keys[3]] if created else ['f1', 'f3']
    assert observed == expected
    assert len(queries) == 1
    assert analyzer.analysis_errors == []


@pytest.mark.parametrize('created', [False, True])
def test_no_progress_is_bounded_and_preserves_all_candidates(created):
    analyzer, keys, queries, observed = make_analyzer(lambda keys: list(keys), created)
    analyzer._review_function_calls()
    assert len(queries) == 3
    assert observed == (keys if created else ['f' + str(i) for i in range(6)])
    assert analyzer.analysis_errors == []

@pytest.mark.parametrize('created', [False, True])
def test_second_narrowing_prompt_only_offers_current_subset(created):
    import json
    analyzer, keys, queries, observed = make_analyzer(None, created, candidate_count=8)
    selected = keys[:6]
    def query(prompt):
        queries.append(prompt)
        offered = json.loads(prompt)
        if len(queries) == 1:
            assert list(offered) == keys
            return selected
        assert list(offered) == selected
        assert keys[6] not in offered and keys[7] not in offered
        return selected[1:3]
    analyzer.agent = SimpleNamespace(query=query)
    analyzer._review_function_calls()
    assert len(queries) == 2
    assert observed == (selected[1:3] if created else ['f1', 'f2'])


@pytest.mark.parametrize('created', [False, True])
def test_second_narrowing_cannot_reintroduce_an_already_removed_key(created):
    import json
    analyzer, keys, queries, observed = make_analyzer(None, created, candidate_count=8)
    selected = keys[:6]
    def query(prompt):
        queries.append(prompt)
        if len(queries) == 1:
            return selected
        assert list(json.loads(prompt)) == selected
        return [selected[0], keys[7]]
    analyzer.agent = SimpleNamespace(query=query)
    with pytest.raises(ValueError, match='selection|Selection|narrow|Narrow'):
        analyzer._review_function_calls()
    assert len(queries) == 2
    assert observed == []
    candidates = analyzer.address_calls_with_created_contract_in_params if created else analyzer.functions_to_be_inspected
    assert list(candidates) == keys
