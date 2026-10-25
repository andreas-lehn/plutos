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

    FIELDNAMES = ['contracts', 'stop_loss', 'p_short', 'p_long']

    def __init__(self, model_path: Path, threshold: int):
        self.model = xgb.XGBClassifier()
        self.model.load_model(model_path)
        self.threshold = threshold / 100
        self.data = []
 
    def contract_size(direction: int, candle: Candle) -> (int, int):
        """ calculates contract size and stop loss of a contract """
        if direction < 0:
            stop_loss = 50
            max_contracts = MAX_LOSS // stop_loss
            return -max_contracts, stop_loss
        elif direction > 0:
            stop_loss = 50
            max_contracts = MAX_LOSS // stop_loss
            return max_contracts, stop_loss
        else:
            return 0, 0 # pragma: no cover

    def on_candle(self, candle: Candle, chart: Chart):
        contracts, stop_loss, p_long, p_short = 0, 0, 0.0, 0.0

        if len(chart) > START_OFFSET:
            data = DataCollector.data_set(candle, chart)
            DataCollector.fill_past_data(data, self.data)
            data['time'] = len(chart) - 1
            self.data.append(data)
            
            df = pd.DataFrame([data])
            p_short, _, p_long = self.model.predict_proba(df)[0]

            if p_long > self.threshold:
                contracts, stop_loss = Hephaistos.contract_size(1, candle)
            elif p_short > self.threshold:
                contracts, stop_loss = Hephaistos.contract_size(-1, candle)
    
        candle.contracts = contracts
        candle.stop_loss = stop_loss
        candle.p_short = p_short
        candle.p_long = p_long


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

    LOOK_AHEAD = 3

    def __init__(self):
        self.time = 0
        self.data = []
 
    def data_set(candle: Candle, chart: Chart):
        data = dict()

        average_0 = chart[0].average
        data['open'] = candle.open - average_0
        data['low'] = candle.low - average_0
        data['average'] = candle.average - average_0
        data['high'] = candle.high - average_0
        data['close'] = candle.close - average_0
        data['ema_fast'] = candle.ema_fast - average_0
        data['ema_slow'] = candle.ema_slow - average_0

        average = candle.average
        data['delta_open']  = candle.open - average 
        data['delta_low']   = candle.low - average
        data['delta_high']  = candle.high - average
        data['delta_close'] = candle.close - average
        data['delta_ema_fast'] = candle.ema_fast - average
        data['delta_ema_slow'] = candle.ema_slow - average
        data['delta_ema'] = candle.ema_slow - candle.ema_fast

        data['wick_top'] = candle.high - max(candle.open, candle.close)
        data['wick_low'] = min(candle.open, candle.close) - candle.low
        data['delta']    = candle.delta
        data['range']    = candle.range
        data['atr']      = chart.average_range(9)
        data['volume']   = candle.volume
        return data

    def fill_past_data(data, past_data: list):
        FIELD_NAMES = [key for key in data.keys()]
        MAX_LOOK_BACK = 5
        for i in range(1, MAX_LOOK_BACK + 1):
            pd = data
            if len(past_data) > 0:            
                pd = past_data[-min(i, len(past_data))]
            for field in FIELD_NAMES:
                field_n = field + '_' + str(i)
                data[field_n] = data[field] - pd[field]
        return data
    
    def on_candle(self, candle: Candle, chart: Chart):
        data = DataCollector.data_set(candle, chart)
        DataCollector.fill_past_data(data, self.data)
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
        df = df.iloc[24:-5]
        frames.append(df)
    return pd.concat(frames, axis=0)

def split_target(df: pd.DataFrame, short: int = 24, long: int = 24, target_col: str = 'target'): # pragma: no cover
    feature_cols = [col for col in df.columns if col != target_col]
    X = df[feature_cols]

    conditions = [
        (df[target_col] < short),
        (df[target_col] >= short) & (df[target_col] <= long),
        (df[target_col] > long)
    ]
    y = np.select(conditions, [0, 1, 2])
    return X, y

def find_quantile(df: pd.DataFrame, target_col: str = 'target', quantile: float = 0.25):
    short = df[target_col].quantile(quantile)
    long  = df[target_col].quantile(1 - quantile)
    return short, long

def fit_cmd(prog_name: str, args): #pragma: no cover
    """ fit the model to training data """
    print(f'{prog_name}: I fit a model to training data...')

    df_training = load_files(args.training_files)
    short, long = find_quantile(df_training)
    X_train, y_train = split_target(df_training, short, long)

    df_eval = load_files(args.eval_files)
    X_eval, y_eval = split_target(df_eval, short, long)

    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=3,
        eval_metric='mlogloss',
        early_stopping_rounds=25,
        n_estimators = 1500,
        learning_rate = 0.03,
        max_depth = 4,
        random_state = 42,
    )
    model.fit(X_train, y_train, eval_set=[(X_eval, y_eval)], verbose=True)
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
            writer = csv.DictWriter(f, fieldnames=collector.data[0].keys())
            writer.writeheader()
            writer.writerows(collector.data)


def predict_cmd(prog_name: str, args): # pragma: no cover
    """ predict based on a given model """
    print (f"{prog_name}: I predict based on model '{args.model}'' ...")

    df = load_files(args.files)
    X, y = split_target(df)

    model = xgb.XGBClassifier()
    model.load_model(args.model)
    prob = model.predict_proba(X)
    prob_short = prob[:, 0]
    prob_long  = prob[:, 2]

    THRESHOLD = 0.65
    long_signals = prob_long > THRESHOLD
    total_long_signals = np.sum(long_signals)
    correct_long_signals = np.sum(long_signals & (y == 2))
    long_rate = correct_long_signals/total_long_signals

    short_signals = prob_short > THRESHOLD
    total_short_signals = np.sum(short_signals)
    correct_short_signals = np.sum(short_signals & (y == 0))
    short_rate = correct_short_signals/total_short_signals
    
    print( '              short    long')
    print(f'    p > {int(THRESHOLD*100):2d}%  {total_long_signals:6d}  {total_short_signals:6d}')
    print(f'    correct  {correct_long_signals:6d}  {correct_short_signals:6d}')
    print(f'    rate     {long_rate*100:6.2f}  {short_rate*100:6.2f}')


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
    train.add_argument('-t', '--training_files', nargs='+', type=str, help='files with training data (.csv')
    train.add_argument('-e', '--eval-files', nargs='+', type=str, help='files to evaluate fitting of training data')
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
    sim.add_argument('-t', '--threshold', type=int, default=65, help='threshold to start a trade')
    sim.add_argument('-n', '--num-candles', type=int, help='number of candles to simulate')
    sim.add_argument('-o', '--out-file', type=str, required=True, help="name of output file")

    sim.set_defaults(command=sim_cmd)

    args = parser.parse_args()
    args.command(parser.prog, args)

