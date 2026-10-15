def test_gateway_alias_does_not_prove_native_adapter_or_model_quality():
    from scripts.probe_nara_conformance import assess_response
    body = {'model': 'claude-haiku-5.5', 'choices': [{'message': {'content': '{"nonce":"abc","sum":12}'},
        'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 24, 'completion_tokens': 12}}
    result = assess_response(body, 'claude-haiku-5.5', 'abc')
    assert result['status'] == 'VERIFIED-VIA-NARAROUTER'
    assert result['native_adapter_tested'] is False
    assert result['localization_quality_tested'] is False
    body['choices'][0]['message']['content'] = '{"nonce":"wrong","sum":12}'
    assert assess_response(body, 'claude-haiku-5.5', 'abc')['status'] == 'CONFORMANCE-FAILED'
