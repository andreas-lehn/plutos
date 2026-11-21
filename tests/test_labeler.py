#
# test_labeler.py
#

import pytest

from plutos.hephaistos.labeler import is_trend_start, is_long_chance, is_short_chance, tripple_barrier

def test_is_trend():
    assert is_trend_start([10, 11, 12, 13, 14]) == 0
    assert is_trend_start([12, 11, 12, 13, 14]) > 0
    assert is_trend_start([11, 11, 12, 13, 14]) > 0
    assert is_trend_start([12, 11, 11, 13, 14]) == 0
    assert is_trend_start([12, 11, 12, 11, 14]) == 0
    assert is_trend_start([12, 11, 12, 13, 13]) == 0
    assert is_trend_start([12, 13, 12, 11, 10]) < 0

def test_tripple_barrier():
    assert tripple_barrier(10, 20, [10, 15, 20]) == 0
    assert tripple_barrier(10, 20, [10, 15, 20, 9, 21]) == -1
    assert tripple_barrier(10, 20, [10, 15, 20, 21, 9]) == 1

def test_is_long_chance():
    assert is_long_chance(10, 4, 10, [10, 6, 19, 15]) == False
    assert is_long_chance(10, 4, 10, [10, 5, 21]) == False
    assert is_long_chance(10, 4, 10, [6, 10, 15, 21, 20, 19])

def test_is_short_chance():
    assert is_short_chance(20, 4, 10, [20, 24, 10, 15]) == False
    assert is_short_chance(20, 4, 10, [20, 25, 10, 9, 10]) == False
    assert is_short_chance(20, 4, 10, [20, 24, 10, 9, 10])
