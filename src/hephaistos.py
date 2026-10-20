#
# Hephaistos is the AI Trader of Plutos
#

import csv
from pathlib import Path
from model import Bar, Chart, MarketModel
import pandas as pd
import numpy as np
import xgboost as xgb


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
 
    #@classmethod
    #def from_file(file: Path, bar_size: int = 36):
    #    collector = DataCollector(bar_size)
    #    return collector.collect_from_file(file)

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

    def data_path(file: Path) -> Path:
        """ generates the path for training data file from a source file (.dbn) """
        name = file.stem
        parts = name.split('_')
        if len(parts) != 3 and parts[2] != 'trades':
            raise ValueError(
                f"data_path(): file name ‘{name}' is violating naming convention '<SYMBOL>_<DATE>_trades.dbn'"
            )
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

def fit_cmd(prog_name: str, args): #pragma: no cover
    """ fit the model to training data """
    print(f'{prog_name}: I fit a model to training data...')

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


def prepare_cmd(prog_name: str, args):  #pragma: no cover
    """ prepare training data from historical data """
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

def evaluate_prediction(y_pred, y):
    bin_edges = [-np.inf, -50, -40, -30, -20, -10, 10, 20, 30, 40, 50, np.inf]
    labels = ['-50', '-40', '-30', '-20', '-10', '  0', '+10', '+20', '+30', '+40', '+50']
    zones = pd.cut(y_pred, bins=bin_edges, labels=labels, include_lowest=True)
    evaluation = []
    for pred, target in zip(y_pred, y):
        if abs(pred) < 10:
            if abs(pred) <= abs(target):
                evaluation.append('correct')
            else:
                evaluation.append('wrong')
        elif pred * target < 0:
            evaluation.append('wrong')
        else:
            evaluation.append('correct')

    analyse_df = pd.DataFrame({'zone': zones, 'eval': evaluation})
    crosstab = pd.crosstab(analyse_df['zone'], analyse_df['eval'])
    for col in ['correct', 'wrong']:
        if  col not in crosstab.columns:
            crosstab[col] = 0
    
    crosstab['total'] = crosstab.sum(axis=1)
    percent_tab = crosstab.copy()
    for col in ['correct', 'wrong']:
        percent_tab[col] = (crosstab[col] / crosstab['total']).fillna(0) * 100

    return pd.DataFrame({
        'total': crosstab['total'],
        'correct (%)': percent_tab['correct'],
        'wrong (%)': percent_tab['wrong'],
    })


def predict_cmd(prog_name: str, args): # pragma: no cover
    """ predict based on a given model """
    print (f"{prog_name}: I predict based on model '{args.model}'' ...")

    df = load_files(args.files)
    X, y = split_target(df)

    model = xgb.XGBRegressor()
    model.load_model(args.model)
    y_pred = model.predict (X)

    result_df = evaluate_prediction(y_pred, y)
    print()
    print(result_df.to_string())


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Hephaistos training utility")
    parser.set_defaults(command=lambda prog_anme, args: parser.print_usage())
    parser.add_argument('-b', '--bar-size', type=int, default=36, help="size of a bar")
    subparsers = parser.add_subparsers()

    train = subparsers.add_parser('fit', description='fit a model from historical data')
    train.add_argument('files', nargs='+', type=str, help='files with training data (.csv')
    train.add_argument('-m', '--model', default='hephaistos.json', help='model file')
    train.set_defaults(command=fit_cmd)

    data = subparsers.add_parser('prepare', description='generate training data out of Databento native files')
    data.add_argument('files', nargs='+', type=str, help='files with historical data in Databento native file (.dbn)')
    data.add_argument('-d', '--dir', type=str, default=None, help="directory where to put the output files")
    data.set_defaults(command=prepare_cmd)

    test = subparsers.add_parser('predict', description='predict historical test data and evaluate results')
    test.add_argument('files', nargs='+', type=str, help='file with taining data (.csv)')
    test.add_argument('-m', '--model', default='hephaistos.json', help='model file')
    test.set_defaults(command=predict_cmd)
    args = parser.parse_args()
    args.command(parser.prog, args)

