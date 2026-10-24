#
# Hephaistos is the AI Trader of Plutos
#

import csv
from pathlib import Path
from model import Candle, Chart, MarketModel
import pandas as pd
import numpy as np
import xgboost as xgb

MAX_LOSS = 50
START_OFFSET = 48 # don't begin trading bevor this offset in seconds since start of the session

class Hephaistos:

    FIELDNAMES = ['contracts', 'stop_loss', 'prediction']

    def __init__(self, model_path: Path, threshold: int):
        self.model = xgb.XGBRegressor()
        self.model.load_model(model_path)
        self.threshold = threshold
 
    def contract_size(direction: int, candle: Candle) -> (int, int):
        """ calculates contract size and stop loss of a contract """
        if direction < 0:
            stop_loss = candle.high - candle.average
            max_contracts = MAX_LOSS // stop_loss
            return -max_contracts, stop_loss
        elif direction > 0:
            stop_loss = candle.average - candle.low
            max_contracts = MAX_LOSS // stop_loss
            return max_contracts, -stop_loss
        else:
            return 0, 0 # pragma: no cover

    def on_candle(self, candle: Candle, chart: Chart):
        contracts, stop_loss, prediction = 0, 0, 0

        if len(chart) > 48:
            data = DataCollector.data_set(candle, chart)
            data['time'] = len(chart) - 1
            df = pd.DataFrame([data])
            df = df[DataCollector.FIELDNAMES[:-1]]
            prediction = self.model.predict(df)[0]

            if abs(prediction) > self.threshold:
                contracts, stop_loss = Hephaistos.contract_size(prediction, candle)
    
        candle.contracts = contracts
        candle.stop_loss = stop_loss
        candle.prediction = prediction

    def simulate(file, model_path: Path, candle_size: int = 36, num_candles: int = None, threshold: int = 20): # pragma: no cover
        main_chart = Chart(candle_size)
        model = MarketModel()
        model.charts.append(main_chart)
        trader = Hephaistos(model_path, threshold)
        main_chart.register_callback(trader.on_candle)
        model.simulate_file(file, num_candles * candle_size if num_candles else 24*60*60*10**9)
        return main_chart


class DataCollector:
    """ delivers a data set for each candle """

    FIELDNAMES = [
        'time', 
        'low', 'high', 'close', 'delta', 'range', 'volume', 'ema_fast', 'ema_slow',
        'avg_1', 'ema_fast_1', 'ema_slow_1',
        'avg_3','ema_fast_3', 'ema_slow_3',
        'target',
    ]

    LOOK_AHEAD = 3

    def __init__(self):
        self.time = 0
        self.data = []
 
    def data_set(candle: Candle, chart: Chart):
        data = {}
        data['low']    = candle.average - candle.low
        data['high']   = candle.average - candle.high
        data['close']  = candle.average - candle.close
        data['delta']  = candle.delta
        data['range']  = candle.range
        data['volume'] = candle.volume
        data['ema_fast'] = candle.average - candle.ema_fast
        data['ema_slow'] = candle.average - candle.ema_slow
        
        candle_1 = chart.look_back(1)
        data['avg_1']      = candle.average - candle_1.average
        data['ema_fast_1'] = candle.ema_fast - candle_1.ema_fast
        data['ema_slow_1'] = candle.ema_slow - candle_1.ema_slow

        candle_3 = chart.look_back(3)
        data['avg_3']      = candle.average - candle_3.average
        data['ema_fast_3'] = candle.ema_fast - candle_3.ema_fast
        data['ema_slow_3'] = candle.ema_slow - candle_3.ema_slow

        return data
    
    def on_candle(self, candle: Candle, chart: Chart):
        data = DataCollector.data_set(candle, chart)
        data['time'] = self.time
        data['target'] = None
        self.data.append(data)
        self.time += 1

        # set target value in past data sets
        offset = DataCollector.LOOK_AHEAD + 1
        if len(self.data) >= offset:
            self.data[-offset]['target'] = candle.average - chart[-offset].average

    def data_path(file: Path) -> Path:
        """ generates the path for training data file from a source file (.dbn) """
        name = file.stem
        parts = name.split('_')
        if len(parts) != 3 or parts[2] != 'trades':
            raise ValueError(
                f"data_path(): file name ‘{name}' is violating naming convention '<SYMBOL>_<DATE>_trades.dbn'"
            )
        return Path(f'{parts[0]}_{parts[1]}_hephaistos.csv')

def load_files(files) -> pd.DataFrame: # pragma: no cover
    frames = []
    for file in files:
        df = pd.read_csv(file)
        df = df.iloc[48:-3]
        frames.append(df)
    return pd.concat(frames, axis=0)

def split_target(df: pd.DataFrame, target_col: str = 'target'): # pragma: no cover
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
        main_chart = Chart(candle_size=args.candle_size)
        main_chart.register_callback(collector.on_candle)
        model = MarketModel()
        model.charts.append(main_chart)
        model.simulate_file(path)

        with open(DataCollector.data_path(path), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=DataCollector.FIELDNAMES)
            writer.writeheader()
            writer.writerows(collector.data)

EVLUATION_BINS = [-np.inf, -50, -40, -30, -20, -10, 10, 20, 30, 40, 50, np.inf]
EVALUATION_LABELS = ['-50', '-40', '-30', '-20', '-10', '  0', '+10', '+20', '+30', '+40', '+50']

def evaluate_prediction(y_pred, y):
    zones = pd.cut(y_pred, bins=EVLUATION_BINS, labels=EVALUATION_LABELS, include_lowest=True)
    evaluation = []
    for pred, target in zip(y_pred, y):
        if abs(pred) < 10:
            if abs(pred) <= abs(target):
                evaluation.append('correct')
            else:
                evaluation.append('wrong')
        elif pred * target <= 0:
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
    y_pred = model.predict(X)

    result_df = evaluate_prediction(y_pred, y)
    print()
    print(result_df.to_string())


def sim_cmd(prog_name: str, args): # pragma; no cover
    """ simulate a Databento trades file with Hephaistos """
    print (f"{prog_name}: I simulate file '{args.file}'")
    
    chart = Hephaistos.simulate(args.file, args.model, args.candle_size, args.num_candles, args.threshold)
    chart.to_file(args.out_file, fieldnames=Candle.OHLC_FIELDNAMES + Hephaistos.FIELDNAMES)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Hephaistos training utility")
    parser.set_defaults(command=lambda prog_anme, args: parser.print_usage())
    parser.add_argument('-b', '--candle-size', type=int, default=36, help="size of a candle")
    subparsers = parser.add_subparsers()

    train = subparsers.add_parser('fit', description='fit a model from historical data')
    train.add_argument('files', nargs='+', type=str, help='files with training data (.csv')
    train.add_argument('-m', '--model', type=str, default='hephaistos.json', help='model file')
    train.set_defaults(command=fit_cmd)

    data = subparsers.add_parser('prepare', description='generate training data out of Databento native files')
    data.add_argument('files', nargs='+', type=str, help='files with historical data in Databento native file (.dbn)')
    data.add_argument('-d', '--dir', type=str, default=None, help="directory where to put the output files")
    data.set_defaults(command=prepare_cmd)

    test = subparsers.add_parser('predict', description='predict historical test data and evaluate results')
    test.add_argument('files', nargs='+', type=str, help='file with taining data (.csv)')
    test.add_argument('-m', '--model', type=str, default='hephaistos.json', help='model file')
    test.set_defaults(command=predict_cmd)

    sim = subparsers.add_parser('sim', description="simulate a Databento trades file")
    sim.add_argument('file', type=str, help="file (.dbn) to simulate")
    sim.add_argument('-m', '--model', type=str, default='hephaistos.json', help='model file')
    sim.add_argument('-t', '--threshold', type=int, default=20, help='threshold to start a trade')
    sim.add_argument('-n', '--num-candles', type=int, help='number of candles to simulate')
    sim.add_argument('-o', '--out-file', type=str, required=True, help="name of output file")

    sim.set_defaults(command=sim_cmd)

    args = parser.parse_args()
    args.command(parser.prog, args)

