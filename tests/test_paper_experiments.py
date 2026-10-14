import pytest
from benchmark.paper_experiments import confusion_metrics, compare_runs, run_paired, summarize_categories


def test_all_ten_paper_chains_have_transaction_entrypoints():
    from faultseeker.core.pipeline import FaultSeekerPipeline
    domains = {'eth':'etherscan.io', 'bsc':'bscscan.com', 'polygon':'polygonscan.com',
               'arbitrum':'arbiscan.io', 'optimism':'optimistic.etherscan.io',
               'avalanche':'snowtrace.io', 'base':'basescan.org', 'fantom':'ftmscan.com',
               'gnosis':'gnosisscan.io', 'zksync':'explorer.zksync.io'}
    for chain, domain in domains.items():
        assert FaultSeekerPipeline._parse_txn_link(f'https://{domain}/tx/0x'+ 'a'*64)[1] == chain


def test_metrics_use_integer_outcomes_and_explicit_zero_denominators():
    result = confusion_metrics([True, True, False, False], [True, False, True, False])
    assert result['tp'] == result['fp'] == result['fn'] == result['tn'] == 1
    assert result['precision'] == result['recall'] == result['f1'] == .5
    assert confusion_metrics([False], [False])['precision'] is None
    with pytest.raises(ValueError):
        confusion_metrics([True], [])


def test_paired_runner_calls_actual_analysis_with_identical_identity_and_guidance():
    calls = []
    def analyze(record, variant, guidance):
        calls.append((record['txn_hash'], variant, guidance))
        return {'predicted_exploit': bool(guidance), 'ranked_functions': [],
                'query_records': [], 'duration_seconds': 1.0}
    records = [{'txn_hash': '0x' + 'a'*64, 'chain': 'eth', 'label': True}]
    runs = run_paired(records, analyze, ['baseline', 'guided'], {'guided': {'focus': 'withdraw()'}})
    assert len(calls) == 2
    assert calls[0][0] == calls[1][0]
    compared = compare_runs(runs['baseline'], runs['guided'])
    assert compared['accuracy_difference_pp'] == 100
    assert compared['cost_savings_fraction'] is None


def test_comparison_rejects_unpaired_ids_and_missing_cost_usage():
    first = [{'identity': 'eth:a', 'label': True, 'predicted_exploit': True,
              'ranked_functions': [], 'query_records': [], 'duration_seconds': 1.}]
    second = [dict(first[0], identity='eth:b')]
    with pytest.raises(ValueError, match='paired'):
        compare_runs(first, second)
    with pytest.raises(ValueError, match='cost'):
        compare_runs(first, [dict(first[0], query_records=[{'tier': 3}])])


def test_function_identity_includes_address_and_full_signature():
    base = {'identity': 'eth:a', 'label': True, 'predicted_exploit': True,
            'query_records': [], 'duration_seconds': 1.}
    a = [dict(base, ranked_functions=[{'address': '0xabc', 'function': 'withdraw(uint256)'}])]
    b = [dict(base, ranked_functions=[{'address': '0xdef', 'function': 'withdraw(uint256)'}])]
    assert compare_runs(a, b)['top1_agreement_fraction'] == 0


def test_category_means_do_not_hide_missing_observations():
    rows = [{'category': 'access', 'function_calls': 3, 'addresses': 2, 'max_depth': 1, 'gas_used': 5},
            {'category': 'access', 'function_calls': 7, 'addresses': 4, 'max_depth': 3, 'gas_used': 9}]
    assert summarize_categories(rows)['access']['function_calls'] == 5
    with pytest.raises(ValueError, match='gas_used'):
        summarize_categories([{'category': 'access'}])


def test_published_precision_recall_cannot_be_forced_on_18_positive_incidents():
    from benchmark.paper_experiments import feasible_confusion_counts
    assert feasible_confusion_counts(246,18,.89,.83) == []
    assert feasible_confusion_counts(4,2,.5,.5) == [{'tp':1,'fp':1,'fn':1,'tn':1}]


def test_cohort_statistics_count_real_labels_without_padding():
    from benchmark.paper_experiments import cohort_statistics
    records = [{'chain':'eth','vuln_type':'reentrancy','vulnerability_class':'contract','reentrancy_label':True},
               {'chain':'bsc','vuln_type':'oracle','vulnerability_class':'economic','reentrancy_label':False}]
    result = cohort_statistics(records)
    assert result['n'] == 2
    assert result['percentages']['chain']['eth'] == 50
    assert result['reentrant_incidents'] == 1


def test_localization_quality_uses_ground_truth_functions_not_exploit_labels():
    from benchmark.paper_experiments import localization_metrics
    expected = {'address':'0xabc','function':'withdraw(uint256)'}
    wrong = {'address':'0xdef','function':'withdraw(uint256)'}
    metrics = localization_metrics([
        {'predicted_exploit':True,'expected_functions':[expected],'ranked_functions':[wrong]},
        {'predicted_exploit':True,'expected_functions':[expected],'ranked_functions':[expected]}])
    assert metrics['top1_accuracy'] == .5
    assert metrics['micro_f1'] == .5
    assert metrics['tp'] == metrics['fp'] == metrics['fn'] == 1
