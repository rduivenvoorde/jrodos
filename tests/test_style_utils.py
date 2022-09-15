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
    # LAST QColor should be red == '#ff0000'
    assert ramp[len(ramp)-1].name() == '#ff0000'
    # FIRST one should be '#000aff'
    assert ramp[0].name() == '#000aff'
    ramp = RangeCreator.full_cream_color_ramp(11)
    assert 11 == len(ramp)
    # LAST QColor should be red == '#ff0000'
    assert ramp[len(ramp)-1].name() == '#ff0000'
    # FIRST one should be '#000aff'
    assert ramp[0].name() == '#000aff'
    ramp = RangeCreator.full_cream_color_ramp(count=10, start_hue=0, end_hue=0.66, hex_notation=True)
    assert 10 == len(ramp)
    # LAST QColor should be red == '#ff0000'
    assert ramp[len(ramp)-1] == '#ff0000'
    # FIRST one should be '#000aff'
    assert ramp[0] == '#000aff'
    ramp = RangeCreator.full_cream_color_ramp(count=10, start_hue=0, end_hue=0.66, hex_notation=True, reverse=True)
    assert 10 == len(ramp)
    assert ramp[len(ramp) - 1] == '#000aff'
    assert ramp[0] == '#ff0000'
    ramp = RangeCreator.full_cream_color_ramp(count=11, start_hue=0, end_hue=0.66, hex_notation=True)
    assert 11 == len(ramp)
    # LAST QColor should be red == '#ff0000'
    assert ramp[len(ramp)-1] == '#ff0000'
    # FIRST one should be '#000aff'
    assert ramp[0] == '#000aff'

def test_create_log_rule_set():
    s = RangeCreator.create_log_rule_set(-5, 4, False, True)
    for r in s:
        assert len(r) == 3
        assert isinstance(r[2], PyQt5.QtGui.QColor)

def test_create_rule_set():
    r = RangeCreator.create_rule_set(0, 10)
    assert len(r) == 10
    # LAST QColor should be red == '#ff0000'
    assert r[9][2].name() == '#ff0000'
    r = RangeCreator.create_rule_set(0, 10, class_count=5, min_inf=False, max_inf=False)
    assert len(r) == 5
    r = RangeCreator.create_rule_set(0, 10, class_count=5, min_inf=False, max_inf=True)
    assert len(r) == 6  # IMPORTANT: because max_inf == True, one class is added
    r = RangeCreator.create_rule_set(0, 23.83, class_count=10, min_inf=False, max_inf=False)
    assert len(r) == 10
    r = RangeCreator.create_rule_set(0, 4.5, class_count=10, min_inf=False, max_inf=False)
    assert len(r) == 10
    # LAST QColor should be red == '#ff0000'
    assert r[len(r)-1][2].name() == '#ff0000'
    # FIRST one should be '#000aff'
    assert r[0][2].name() == '#000aff'
    r = RangeCreator.create_rule_set(0, 4.5, class_count=10, min_inf=False, max_inf=False, reverse=True)
    assert len(r) == 10
    assert r[len(r)-1][2].name() == '#000aff'
    assert r[0][2].name() == '#ff0000'


def test_cloud_rule_set():
    r = RangeCreator.create_cloud_ruleset(3)
    #print(r)
    assert r[0][0] == '0 - 0.5 uur'
    assert r[0][1] == 'Value >= 0 AND Value < 0.5'
    assert r[7][0] == '3.5 - 4.0 uur'
    assert r[7][1] == 'Value >= 3.5 AND Value < 4.0'