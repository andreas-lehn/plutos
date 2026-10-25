#
# Test Hephaistos
#

import pandas as pd
from hephaistos import DataCollector
from pathlib import Path
import pytest

def test_fill_past_data():
    d_0 = {'low': 100, 'average': 103, 'high': 105, 'delta_low': -3, 'delta_high': 2, 'range': 5, 'atr': 7.0, 'volume': 250}
    d_1 = {'low': 103, 'average': 107, 'high': 109, 'delta_low': -4, 'delta_high': 2, 'range': 6, 'atr': 6.1, 'volume': 240}
    d_2 = {'low': 102, 'average': 103, 'high': 108, 'delta_low': -1, 'delta_high': 5, 'range': 6, 'atr': 5.5, 'volume': 280}

    data = []
    DataCollector.fill_past_data(d_0, data)
    data.append(d_0)
    assert d_0['low_1'] == 0
    assert d_0['low_5'] == 0

    DataCollector.fill_past_data(d_1, data)
    data.append(d_1)
    assert d_1['low_1'] == 3
    assert d_1['low_2'] == 3

    DataCollector.fill_past_data(d_2, data)
    data.append(d_2)
    assert d_2['low_1'] == -1
    assert d_2['low_2'] == 2
    assert d_2['low_3'] == 2


def test_data_path():
    correct = Path('my_path/SYM_1968-05-08_trades.dbn')
    assert DataCollector.data_path(correct) == Path('SYM_1968-05-08_hephaistos.csv')

    incorrect_1 = Path('my_path/SYM_2005-04-10_candles.dbn')
    with pytest.raises(ValueError):
        DataCollector.data_path(incorrect_1)

    incorrect_2 = Path('another/path/SYM_2008-03-14.dbn')
    with pytest.raises(ValueError):
        DataCollector.data_path(incorrect_2)
