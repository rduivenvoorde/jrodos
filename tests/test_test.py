import pytest

def test_test_ok():
    assert True is True

def test_test_nok():
    with pytest.raises(AssertionError) as e:
        assert True is False
    assert e.typename == 'AssertionError'

