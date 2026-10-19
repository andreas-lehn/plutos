#
# Hephaistos is the AI Trader of Plutos
#

import csv
from pathlib import Path
from model import Bar, Chart

class DataCollector:
    """ delivers a data set for each bar """

    FIELDNAMES = ['time', 'avg_1', 'avg_9', 'low', 'high', 'range', 'range_9', 'close', 'delta', 'volume', 'ema9', 'ema48', 'ema9_9', 'ema48_48']

    LOOK_AHEAD = 3

    def __init__(self, file: Path, bar_size: int = 36):
        self.bar_size = bar_size
        self.time = 0
        self.data_sets = []
 
    @classmethod
    def from_file(file: Path, bar_size: int = 36):
        collector = DataCollector(bar_size)
        return collector.collect_from_file(file)

    def collect_from_file(self, file: Path):
        return self.data_sets

    def data_set(bar: Bar, chart: Chart):
        data = {}
        data['low']     = bar.average - bar.low
        data['high']    = bar.high - bar.average
        data['close']   = bar.close - bar.average
        data['delta']   = bar.delta
        data['ema_9']   = bar.average - bar.ema_9
        data['ema_48']  = bar.average - bar.ema_48
        data['range']   = bar.range
        data['range_9'] = chart.average_range(9)

        bar_1 = chart.look_back(1)
        data['avg_1']    = bar.average - bar_1.average
        data['ema_9_1']  = bar.ema_9 - bar_1.ema_9
        data['ema_48_1'] = bar.ema_48 - bar_1.ema_48

        bar_3 = chart.look_back(3)
        data['avg_3']    = bar.average - bar_3.average
        data['ema_9_3']  = bar.ema_9 - bar_3.ema_9
        data['ema_48_3'] = bar.ema_48 - bar_3.ema_48 

        return data
    
    def on_bar(self, bar: Bar, chart: Chart):
        data = DataCollector.data_set(bar, chart)
        data['time'] = self.time
        self.time += 1
        self.data_sets.appen(data)

        # set target value
        offset = DataCollector.LOOK_AHEAD + 1
        if len(self.data_sets) > offset:
            self.data_sets[-offset]['target'] = bar.average - chart[-offset]

    def data_path(file: Path):
        return file.stem + '.csv'

def train_cmd(prog_name: str, args): #pragma: no cover
    """ tain the model """
    print('I am training')

def data_cmd(prog_name: str, args):  #pragma: no cover
    """ generate training data from historical data """
    print('I generate training data')
    for file in args.files:
        path = Path(file)
        with open(DataCollector.data_path(path), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=DataCollector.FIELDNAMES)
            writer.writeheader()
            writer.writerows(DataCollector.from_file(path))


def test_cmd(prog_name: str, args): # pragma: no cover
    """ test a modell """
    print ('I am testing')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Hephaistos training utility")
    parser.set_defaults(command=lambda prog_anme, args: parser.print_usage())
    parser.add_argument('-b', '--bar-size', type=int, default=36, help="size of a bar")
    subparsers = parser.add_subparsers()

    train = subparsers.add_parser('train', description='train a model with historical data')
    train.add_argument('files', nargs='+', type=str, help='files with training data (.csv')
    train.add_argument('-m', '--model', default='hephaistos.json', help='model file')
    train.set_defaults(command=train_cmd)

    data = subparsers.add_parser('data', description='generate training data out of Databento native files')
    data.add_argument('files', nargs='+', type=str, help='files with historical data in Databento native file (.dbn)')
    data.add_argument('-d', '--dir', type=str, default=None, help="directory where to put the output files")
    data.set_defaults(command=data_cmd)

    test = subparsers.add_parser('test', description='test a modell on historical data')
    test.add_argument('file', type=str, help='file with historical data in Databento native file (.dbn)')
    test.add_argument('-m', '--model', default='hephaistos.json', help='model file')
    test.set_defaults(command=test_cmd)
    args = parser.parse_args()
    args.command(parser.prog, args)
