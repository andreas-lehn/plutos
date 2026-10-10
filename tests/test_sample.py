from pathlib import Path

import pytest

from marketdata import Sample


@pytest.fixture
def csv_path():    
    return Path(__file__).resolve().parent/'test_samples.csv'


def test_from_csv(csv_path):
    samples = []
    Sample.stream_csv(csv_path, lambda sample: samples.append(sample))
    assert len(samples) == 10
    assert samples[0].open == 122622
    assert samples[1].high == 122667
    assert samples[2].low == 122659
    assert samples[3].close == 122666
    assert samples[4].close == 122662
    assert samples[5].low == 122654
    assert samples[6].histo == [19, 10, 8, 6, 4, 26, 10]
    assert samples[7].high == 122667
    assert samples[8].open == 122662
    assert samples[9] == None

if __name__ == '__main__':
    unittest.main()
