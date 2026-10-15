import pytest

def test_proxy_storage_owner_cannot_replace_implementation_target():
    from scripts.score_train_localization import function_rank
    rows=[{'rank':1,'code_address':'0xproxy','selector':'0x12345678'}, {'rank':2,'code_address':'0ximplementation','selector':'0x12345678'}]
    assert function_rank(rows,{('0ximplementation','0x12345678')})==2
    assert function_rank(rows,{('0xmissing','0x12345678')}) is None

def test_unordered_or_duplicate_predictions_are_rejected():
    from scripts.score_train_localization import function_rank
    with pytest.raises(ValueError):
        function_rank([{'rank':2,'code_address':'0xa','selector':'0x12345678'}],{('0xa','0x12345678')})
    with pytest.raises(ValueError):
        function_rank([{'rank':1,'code_address':'0xa','selector':'0x12345678'},{'rank':2,'code_address':'0xa','selector':'0x12345678'}],{('0xa','0x12345678')})
