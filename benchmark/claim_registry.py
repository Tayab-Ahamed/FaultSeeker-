"""All paper claims, their acceptance tests, and remaining external evidence.

Passing a fixture test proves the local mechanism only. It never verifies a
published empirical result. Reports keep those two scopes separate.
"""

def _test(file, name):
    return f'tests/{file}.py::{name}'


_evidence = _test('test_evidence_manifest', 'test_complete_artifact_manifest_accepts_then_detects_tampering')
_metrics = _test('test_paper_experiments', 'test_metrics_use_integer_outcomes_and_explicit_zero_denominators')
_paired = _test('test_paper_experiments', 'test_paired_runner_calls_actual_analysis_with_identical_identity_and_guidance')
_storage = _test('test_storage_normalization', 'test_raw_sload_then_sstore_preserves_slot_value_and_program_counters')
_profile = _test('test_paper_detector', 'test_paper_score_uses_activated_signals_from_opcode_adapter')
_flow = _test('test_local_control_flow', 'test_pipeline_bypasses_stage_two_before_model_setup_for_proven_benign')


CLAIMS = []
_definitions = [
 (1, 'Open source release', 'PENDING-PUBLICATION', [], 'Public fork/release URL; local Apache license alone does not prove publication.'),
 (2, '201 original tests pass', 'LOCAL', [_test('test_reproduction_entrypoints','test_legacy_runner_delegates_arguments_and_propagates_pytest_failure')], 'Full suite with original baseline tests retained; runner unit test alone is insufficient.'),
 (3, 'Authentic 246-row cohort', 'DATA', [_evidence, _test('test_claim_registry','test_cohort_builder_refuses_to_pad_or_emit_partial_dataset')], '246 unique accepted acquisition manifests; no padded rows.'),
 (4, 'Real transactions, two independent sources, annotations', 'DATA', [_evidence], 'Canonical transaction/receipt/traces, two source artifacts, independent adjudication per row.'),
 (5, 'Ten chains and Ethereum 47.6%', 'DATA', [_test('test_paper_experiments','test_all_ten_paper_chains_have_transaction_entrypoints')], 'Authenticated frozen ten-chain cohort; compute true chain counts and proportions.'),
 (6, 'More than 80 vulnerability labels', 'DATA', [_evidence], 'Adjudicated taxonomy and true unique labels on the frozen cohort.'),
 (7, 'Class proportions 6.5/33.3/32.5/27.6%', 'DATA', [_metrics], 'Predeclared non-overlapping class mapping and authentic row labels.'),
 (8, '18 reentrant incidents among 246', 'DATA', [_metrics], 'Independently adjudicated reentrancy labels for all accepted rows.'),
 (9, 'Storage-aware detector, guards and delegatecall', 'LOCAL', [_profile, _test('test_paper_detector','test_production_stage_one_activates_paper_profile'), _test('test_storage_normalization','test_delegatecall_uses_proxy_storage_and_marks_reverted_child_writes')], 'Compiled execution still separately required under claim 26.'),
 (10, 'Five storage signal weights', 'LOCAL', [_profile,_test('test_paper_weights','test_each_paper_weight_contributes_to_the_executed_score')], 'Weights must fire on observed opcode events.'),
 (11, 'Five confidence tiers', 'LOCAL', [_test('test_paper_tiers','test_every_tier_boundary_and_its_lower_neighbor'),_test('test_paper_detector','test_production_stage_one_activates_paper_profile')], 'Threshold boundaries and production paper profile.'),
 (12, 'Three structural signals, .75 penalty, .80 cap', 'LOCAL', [_test('test_paper_fallback','test_three_structural_signals_fire_without_storage_and_are_penalized_and_capped')], 'Fallback when storage capture unavailable, no extra terms.'),
 (13, 'Detector precision/recall/F1 and baselines', 'DATA', [_metrics], 'Actual predictions on one frozen adjudicated cohort; integer confusion counts.'),
 (14, '17/29 percentage-point gains', 'DATA', [_paired], 'Paired executed baseline detector outcomes; report measured differences.'),
 (15, 'Compound case study', 'DATA', [_evidence], 'Exact transaction, raw traces, independent source/GT and executed localization result.'),
 (16, 'Query routing with theta gate', 'LOCAL', [_test('test_query_routing','test_tier_two_low_confidence_falls_back_and_records_both_attempts')], 'Local quality/confidence gate must dispatch escalation.'),
 (17, 'Six provider families', 'EXTERNAL', [_test('test_query_routing','test_anthropic_adapter_uses_native_messages_schema_and_usage'),_test('test_query_routing','test_all_six_provider_families_construct_the_correct_adapter')], 'Live provider conformance and installed Ollama model.', ['OPENAI_API_KEY','XAI_API_KEY','DASHSCOPE_API_KEY','GOOGLE_API_KEY','ANTHROPIC_API_KEY','OLLAMA_HOST']),
 (18, '58% cost savings, 100 transactions, quality/rank bounds', 'DATA', [_paired,_test('test_spend_guard','test_reservation_survives_restart_and_blocks_cumulative_overspend')], '100 paired production runs, observed provider usage, pricing snapshot and 5:3:2 workload.'),
 (19, 'Stage 1 makes no model calls', 'LOCAL', [_test('test_stage_one_local','test_stage_one_constructor_does_not_build_model_agents'), _test('test_stage_one_local','test_fund_flow_analysis_is_deterministic_and_keyless')], 'Constructor and executed Stage1 must remain keyless.'),
 (20, 'BENIGN skip, EXPLOIT lock and UNCERTAIN escalation', 'LOCAL', [_flow,_test('test_local_control_flow','test_clean_signals_need_explicit_complete_coverage_to_be_benign')], 'Coverage required; positive verdict cannot be overwritten.'),
 (21, '40% benign prefilter and latency reduction', 'DATA', [_paired,_flow], 'Paired production runs on independently verified benign transactions and measured latency.'),
 (22, 'Multi-agent function localization', 'EXTERNAL', [_test('test_function_agent_flow','test_real_function_analysis_executes_every_role_including_child_filter'),_test('test_source_analysis_safety','test_production_function_analyzer_cannot_leak_findings_between_transactions')], 'Live model quality and verified contract source retrieval; local role dispatch is proven with model-boundary fixtures.', ['OLLAMA_HOST','OPENAI_API_KEY','ETHERSCAN_API_KEY']),
 (23, 'Equation 4 confidence scoring', 'LOCAL', [_test('test_calibration_schema','test_paper_formula_remains_a_relative_score'),_test('test_calibration_schema','test_legacy_proxy_model_cannot_calibrate_production_factors')], 'Heuristic score identified separately from calibrated probability.'),
 (24, 'Evidence cards and two HITL checkpoints, five guidance types', 'LOCAL', [_test('test_analyst_guidance','test_first_checkpoint_applies_all_guidance_to_downstream_state'), _test('test_local_control_flow','test_pipeline_stage_two_rejection_updates_final_findings')], 'All feedback must affect downstream state, with rejection audit trail.'),
 (25, 'RPC EMA, LRU, TTL, breakers and batching', 'EXTERNAL', [_test('test_rpc_mechanisms','test_rpc_latency_ema_really_uses_point_two'),_test('test_rpc_mechanisms','test_cache_enforces_lru_and_ttl'),_test('test_rpc_mechanisms','test_circuit_breaker_opens_and_requires_three_clean_recovery_probes'),_test('test_rpc_mechanisms','test_batch_preserves_request_order_and_falls_back_after_batch_failure')], 'Live dRPC/archive debug tracer capability on requested chains.', ['DRPC_API_KEY','DRPC_RPC_URL']),
 (26, 'Foundry replay extracts SLOAD and SSTORE', 'TOOLS', [_storage,_test('test_storage_normalization','test_local_fixture_runner_orchestrates_deploy_transact_and_both_tracers'),_test('test_compiled_evm_integration','test_compiled_contracts_emit_real_storage_opcodes'),_test('test_compiled_evm_integration','test_compiled_mutex_preserves_actual_lock_transitions'),_test('test_compiled_evm_integration','test_compiled_delegatecall_writes_proxy_storage'),_test('test_compiled_evm_integration','test_paper_tiers_on_compiled_contracts')], 'Compile and execute all Solidity fixtures and preserve raw trace captures; local EVM proof does not verify historical replay or cohort outcomes.', ['SOLC_BINARY','ANVIL_BINARY','CAST_BINARY','FOUNDRY_BIN']),
 (27, '23% WAF challenge bypass', 'DATA', [_test('test_acquisition_paths','test_challenge_recovery_records_every_attempt_and_real_denominator'),_test('test_acquisition_paths','test_production_collector_runs_recovery_and_retains_attempt_evidence')], 'Authorized recorded challenged requests, outcomes/attempts and versioned strategy; no percentage inferred from retry success.', ['CURL_IMPERSONATE_BINARY','WAF_CASES_JSON']),
 (28, 'Table VI category averages', 'DATA', [_test('test_paper_experiments','test_category_means_do_not_hide_missing_observations')], 'Real receipt gas, call count, address count and depth per adjudicated category.'),
 (29, 'Simulated guidance on 20 transactions, 68→81%', 'DATA', [_paired], '20 paired runs with preregistered simulation policy, complete integer outcomes; not a human study.'),
 (30, 'Reproduction scripts', 'LOCAL', [_test('test_claim_registry','test_registry_accounts_for_all_31_claims_without_promoting_fixture_proof')], 'One offline entry point, genuine test results and blocked evidence report.'),
 (31, 'Repository layout/runtime compatibility', 'LOCAL', [_test('test_runtime_layout','test_docker_copy_sources_all_exist')], 'Local Python runtime and Docker input layout checked; actual Docker execution remains an external-tool check.'),
]
for definition in _definitions:
    identifier, title, scope, tests, required, *env = definition
    CLAIMS.append({'id': identifier, 'claim': title, 'scope': scope, 'tests': tests,
                   'required_evidence': required, 'required_env': env[0] if env else []})


def claim_report(test_outcomes, dataset_audit):
    rows = []
    for claim in CLAIMS:
        def passed(node):
            matches = [outcome for key,outcome in test_outcomes.items() if key == node or key.startswith(node+'[')]
            return bool(matches) and all(outcome == 'passed' for outcome in matches)
        proof = bool(claim['tests']) and all(passed(node) for node in claim['tests'])
        scope = claim['scope']
        status = ('IMPLEMENTED-LOCAL' if proof else 'LOCAL-ACCEPTANCE-PENDING') if scope == 'LOCAL' else {
            'DATA': 'BLOCKED-BY-DATA', 'EXTERNAL': 'PENDING-CREDENTIALS',
            'TOOLS': 'PENDING-CREDENTIALS', 'PENDING-PUBLICATION': 'PENDING-PUBLICATION'}[scope]
        if scope == 'TOOLS' and proof:
            status = 'VERIFIED-COMPILED-EVM'
        historical_node = 'tests/test_historical_fork_replay.py::test_recorded_historical_capture_validates_storage_and_receipt'
        historical = claim['id'] == 26 and proof and passed(historical_node)
        if historical:
            status = 'VERIFIED-HISTORICAL-ETHEREUM-SAMPLE'
        local_proof = 'OUTSIDE-LOCAL-SCOPE' if scope=='PENDING-PUBLICATION' else 'PASSED' if proof else 'FAILED-OR-MISSING'
        row = dict(claim, status=status, local_proof=local_proof)
        if historical:
            row.update(evidence_pointers=[
                'reports/historical_replay/README.md',
                'reports/historical_replay/historical_replay_summary.json',
                'reports/historical_replay/0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6.json.gz'],
                historical_verification_scope='One Ethereum transaction; comparison replay timed out. No cohort, all-chain or incident-label verification.',
                historical_acceptance_test=historical_node)
        rows.append(row)
    return {'claims': rows, 'dataset_audit': dataset_audit,
            'scope': 'local acceptance only; empirical and live claims require separate evidence',
            'paid_api_spend_this_run_usd': 0.0}
