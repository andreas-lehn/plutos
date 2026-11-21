#
# Test Hephaistos
#

import pandas as pd
from plutos.hephaistos.core import FeatureGenerator
from pathlib import Path
import pytest


def test_data_path():
    dir =  Path('another/path')
    correct = Path('my_path/SYM_1968-05-08_trades.dbn')
    assert FeatureGenerator.data_path(correct, dir) == dir/Path('training/SYM_1968-05-08_features.csv')

    incorrect = Path('my_path/SYM_2005-04-10.dbn')
    with pytest.raises(ValueError):
        FeatureGenerator.data_path(incorrect, dir)
