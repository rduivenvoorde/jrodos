import pytest

from ..style_utils import RangeCreator
import PyQt5

def test_create_decimal_range_len():
    assert 1 == len(RangeCreator.create_range_set(-1, 1))
    assert 2 == len(RangeCreator.create_range_set(-1, 1, True))
    assert 2 == len(RangeCreator.create_range_set(-1, 1, False, True))
    assert 3 == len(RangeCreator.create_range_set(-1, 1, True, True))
    assert 5 == len(RangeCreator.create_range_set(-5, 5))


def test_create_decimal_range_inf():
    assert float('-inf') == RangeCreator.create_range_set(-1, 1, True)[0][0]
    assert float('inf') == RangeCreator.create_range_set(-1, 1, True, True)[-1][1]


def test_full_cream_color_ramp():
    ramp = RangeCreator.full_cream_color_ramp()
    assert 10 == len(ramp)
    ramp = RangeCreator.full_cream_color_ramp(11)
    assert 11 == len(ramp)


def test_create_rule_set():
    s = RangeCreator.create_rule_set(-5, 4, False, True)
    for r in s:
        assert len(r) == 3
        assert isinstance(r[2], PyQt5.QtGui.QColor)

