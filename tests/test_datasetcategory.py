#
# test of data set category
#

import pytest
from click.testing import CliRunner
from plutos.datasetcategory import category, START_OF_PLUTOS_EPOCHE, category_index
from datetime import datetime

def test_category_index():
    assert category_index(START_OF_PLUTOS_EPOCHE) == 0
    assert category_index(datetime(2026, 9, 1)) == 1
    assert category_index(datetime(2026, 9, 2)) == 2
    assert category_index(datetime(2026, 9, 3)) == 3
    assert category_index(datetime(2026, 9, 4)) == 4
    assert category_index(datetime(2026, 9, 7)) == 5
    assert category_index(datetime(2026, 9, 8)) == 0
    assert category_index(datetime(2026, 9, 9)) == 1
    assert category_index(datetime(2026, 9,10)) == 2
    assert category_index(datetime(2026, 9,11)) == 3
    assert category_index(datetime(2026, 9,14)) == 4
    assert category_index(datetime(2026, 9,15)) == 5

def test_category():
    runner = CliRunner()
    
    result = runner.invoke(category, ['2026-08-31'])
    assert result.exit_code == 0
    assert result.output.strip() == 'training'

    result = runner.invoke(category, ['2026-09-02'])
    assert result.exit_code == 0
    assert result.output.strip() == 'eval'

    result = runner.invoke(category, ['2026-09-07'])
    assert result.exit_code == 0
    assert result.output.strip() == 'test'
    