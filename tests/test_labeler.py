#
# test_labeler.py
#

import pytest

from plutos.labeler import is_trend

def test_is_trend():
    assert is_trend([10, 11, 12, 13, 14]) == 0
    assert is_trend([12, 11, 12, 13, 14]) > 0
    assert is_trend([11, 11, 12, 13, 14]) > 0
    assert is_trend([12, 11, 11, 13, 14]) == 0
    assert is_trend([12, 11, 12, 11, 14]) == 0
    assert is_trend([12, 11, 12, 13, 13]) == 0
    assert is_trend([12, 13, 12, 11, 10]) < 0
