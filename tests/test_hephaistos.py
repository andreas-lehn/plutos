#
# Test Hephaistos
#

import pandas as pd
from hephaistos import evaluate_prediction, EVALUATION_LABELS, DataCollector
from pathlib import Path
import pytest

def test_evaluate_prediction():
    y      = pd.Series([  5,  -5,   5,  -5,   5,  -5,   0,  -5,   5,  -5, -4, 5,  5, -5,  5,  0,  5, -5,  5, -5,  5, -5])
    y_pred = pd.Series([-60, -60, -45, -45, -35, -35, -25, -25, -15, -15, -5, 4, 15, 15, 25, 25, 35, 35, 45, 45, 55, 55])

    result = evaluate_prediction(y_pred, y)

    for label in EVALUATION_LABELS:
        row = result.loc[label]
        assert row['total'] == 2
        assert row['correct (%)'] == 50
        assert row['wrong (%)'] == 50

def test_data_path():
    correct = Path('my_path/SYM_1968-05-08_trades.dbn')
    assert DataCollector.data_path(correct) == Path('SYM_1968-05-08_hephaistos.csv')

    incorrect_1 = Path('my_path/SYM_2005-04-10_candles.dbn')
    with pytest.raises(ValueError):
        DataCollector.data_path(incorrect_1)

    incorrect_2 = Path('another/path/SYM_2008-03-14.dbn')
    with pytest.raises(ValueError):
        DataCollector.data_path(incorrect_2)
