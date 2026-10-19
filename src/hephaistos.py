#
# Hephaistos is the AI Trader of Plutos
#

import csv
from pathlib import Path
from model import Bar, Chart, MarketModel
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt


class DataCollector:
    """ delivers a data set for each bar """

    FIELDNAMES = [
        'time', 
        'low', 'high', 'close', 'delta', 'range', 'volume', 'ema_9', 'ema_48',
        'avg_1', 'ema_9_1', 'ema_48_1',
        'avg_3','ema_9_3', 'ema_48_3',
        'target',
    ]

    LOOK_AHEAD = 3

    def __init__(self):
        self.time = 0
        self.data = []
 
    @classmethod
    def from_file(file: Path, bar_size: int = 36):
        collector = DataCollector(bar_size)
        return collector.collect_from_file(file)

    def data_set(bar: Bar, chart: Chart):
        data = {}
        data['low']     = bar.average - bar.low
        data['high']    = bar.average - bar.high
        data['close']   = bar.average - bar.close
        data['delta']   = bar.delta
        data['range']   = bar.range
        data['volume']  = bar.volume
        data['ema_9']   = bar.average - bar.ema_9
        data['ema_48']  = bar.average - bar.ema_48
        
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
        data['target'] = None
        self.data.append(data)
        self.time += 1

        # set target value in past data sets
        offset = DataCollector.LOOK_AHEAD + 1
        if len(self.data) >= offset:
            self.data[-offset]['target'] = bar.average - chart[-offset].average

    def data_path(file: Path):
        name = file.stem
        parts = name.split('_')
        if len(parts) != 3 and parts[2] != 'trades':
            raise ValueError(f"data_path(): file name ‘{name}' is violating naming convention '<SYM>_<DATE>_trades.dbn'")
        return Path(f'{parts[0]}_{parts[1]}_hephaistos.csv')

def load_files(files) -> pd.DataFrame:
    frames = []
    for file in files:
        df = pd.read_csv(file)
        df = df.iloc[48:-3]
        frames.append(df)
    return pd.concat(frames, axis=0)

def split_target(df: pd.DataFrame, target_col: str = 'target'):
    feature_cols = [col for col in df.columns if col != target_col]
    X = df[feature_cols]
    y = df[target_col]
    return X, y

def train_cmd(prog_name: str, args): #pragma: no cover
    """ tain the model """
    print(f'{prog_name}: I am training...')

    df = load_files(args.files)
    X, y = split_target(df)

    model = xgb.XGBRegressor(
        n_estimators = 100,
        learning_rate = 0.05,
        max_depth = 6,
        random_state = 42,
        n_jobs = -1,
    )
    model.fit(X, y)
    model.save_model(args.model)
    print(f'{prog_name}: model written to {args.model}')


def data_cmd(prog_name: str, args):  #pragma: no cover
    """ generate training data from historical data """
    print(f'{prog_name}: I generate training data...')
    for file in args.files:
        path = Path(file)

        collector = DataCollector()
        main_chart = Chart(bar_size=args.bar_size)
        main_chart.register_callback(collector.on_bar)
        model = MarketModel()
        model.charts.append(main_chart)
        model.simulate_file(path)

        with open(DataCollector.data_path(path), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=DataCollector.FIELDNAMES)
            writer.writeheader()
            writer.writerows(collector.data)


def test_cmd(prog_name: str, args): # pragma: no cover
    """ test a modell """
    print (f'{prog_name}: I am testing...')

    df = load_files(args.files)
    X, y = split_target(df)

    model = xgb.XGBRegressor()
    model.load_model(args.model)
    y_pred = model.predict (X)

    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)
    print(f'{prog_name}: test results:')
    print(f'    mean abs error (MAE): {mae:.4f}')
    print(f'  quadratic error (RMSE): {rmse:.4f}')
    print(f'                R2 score: {r2:.4f}')
    print()

    importance_gain = model.get_booster().get_score(importance_type='gain')
    for key, value in importance_gain.items():
        print(f'   {key:>10}: {value:12.4f}')


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
    test.add_argument('files', nargs='+', type=str, help='file with historical data in Databento native file (.dbn)')
    test.add_argument('-m', '--model', default='hephaistos.json', help='model file')
    test.set_defaults(command=test_cmd)
    args = parser.parse_args()
    args.command(parser.prog, args)
