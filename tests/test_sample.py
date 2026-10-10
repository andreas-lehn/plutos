import unittest
from marketdata import Sample
from pathlib import Path


class TestSample(unittest.TestCase):
    """ Test of class sample """

    def setUp(self):
        self.test_dir = Path(__file__).resolve().parent

    def test_from_csv(self):
        samples = []
        Sample.stream_csv(self.test_dir/'test_samples.csv', lambda sample: samples.append(sample))
        self.assertEqual(len(samples), 10)
        self.assertEqual(samples[0].open, 122622)
        self.assertEqual(samples[1].high, 122667)
        self.assertEqual(samples[2].low, 122659)
        self.assertEqual(samples[3].close, 122666)
        self.assertEqual(samples[4].close, 122662)
        self.assertEqual(samples[5].low, 122654)
        self.assertEqual(samples[6].histo, [19, 10, 8, 6, 4, 26, 10])
        self.assertEqual(samples[7].high, 122667)
        self.assertEqual(samples[8].open, 122662)
        self.assertEqual(samples[9], None)

if __name__ == '__main__':
    unittest.main()
