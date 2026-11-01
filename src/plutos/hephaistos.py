#
# Hephaistos is the AI Trader of Plutos
#

import csv
import click
from pathlib import Path
from .model import Candle, Chart, MarketModel
import pandas as pd
import numpy as np
import xgboost as xgb

MAX_LOSS = 100
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
            stop_loss = 100
            max_contracts = MAX_LOSS // stop_loss
            return -max_contracts, stop_loss
        elif direction > 0:
            stop_loss = 100
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
        MAX_LOOK_BACK = 9
        for i in range(1, MAX_LOOK_BACK + 1):
            pd = data
            if len(past_data) > 0:            
                pd = past_data[-min(i, len(past_data))]
            for field in FIELD_NAMES:
                field_n = field + '_' + str(i)
                data[field_n] = data[field] - pd[field]
        return data

    LOOK_AHEAD = 3

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
            self.data[-offset]['target'] = candle.close - chart[-offset+1].open

    def data_path(file: Path) -> Path:
        """ generates the path for training data file from a source file (.dbn) """
        name = file.stem
        parts = name.split('_')
        if len(parts) != 3 or parts[2] != 'trades':
            raise ValueError(
                f"data_path(): file name ‘{name}' is violating naming convention '<SYMBOL>_<DATE>_trades.dbn'"
            )
        return Path(f'{parts[0]}_{parts[1]}_hephaistos.csv')

def drop_special_phases(df: pd.DataFrame, candle_size: int = 36):
    # der beginn und das ende einer CME session
    # sowie der beginn der nasdaq session sind spezielle momente,
    # die das training verfälschen.
    # deshalb werden die zeiten hier herausgefiltert.
    # 
    # CME session start:    17:00 h
    # Nasdaq session start:  8:30 h Chicago Time (9:30 h New York time)
    # CME session end:      16:00 h
    # 
    # Filter offset:
    #   00:00 - 00:20   Startphase der CME session
    #   15:20 - 16:00   Startphase der Nasdaq
    #   22:40 - 23:00   Endphase der CME session
    #
    # Das entsprichet den folgenden offsets in anzahl candles:

    CME_START    =            20  * 60 // candle_size + 1
    NASDAQ_START = (15 * 60 + 20) * 60 // candle_size
    NASDAQ_END   = (15 * 60 + 50) * 60 // candle_size + 1
    CME_END      = (22 * 60 + 40) * 60 // candle_size

    drop_rows = np.r_[0:CME_START, NASDAQ_START:NASDAQ_END, CME_END:len(df)]
    df.drop(df.index[drop_rows], inplace=True)


def load_files(files) -> pd.DataFrame: # pragma: no cover
    frames = []
    for file in files:
        df = pd.read_csv(file)
        drop_special_phases(df)
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

@click.command('fit')
@click.option(
    '-t', '--training-dir',
    type=click.Path(file_okay=False, dir_okay=True, exists=True, path_type=Path),
    default='training',
    help="directory with training files (*_hephaistos.csv), default='training'",
)
@click.option(
    '-e', '--eval-dir',
    type=click.Path(file_okay=False, dir_okay=True, exists=True, path_type=Path),
    default='eval',
    help="directory with evaluation files (*_hephaistos.csv), default='eval'",
)
@click.option('-m', '--model-file', type=str, default='hephaistos-model.json', help="model file, default='hephaistos-model.json'")
def fit_cmd(training_dir: tuple[Path], eval_dir: tuple[Path], model_file: str): #pragma: no cover
    """ fit the model to training data """
    print('Fitting a model to training data...')

    training_files = tuple(f for f in training_dir.glob("*_hephaistos.csv") if f.is_file())
    df_training = load_files(training_files)
    short, long = find_quantile(df_training)
    X_train, y_train = split_target(df_training, short, long)

    eval_files = tuple(f for f in eval_dir.glob("*_hephaistos.csv") if f.is_file())
    df_eval = load_files(eval_files)
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
    model.save_model(model_file)
    print(f"model written to '{model_file}'")


@click.command('prepare')
@click.argument('files', nargs=-1, type=click.Path(exists=True, path_type=Path), help='files with historical data in Databento native file (.dbn)')
@click.option('-d', '--dir', type=click.Path(), help="directory where to put the output files")
@click.option('-s', '--candle-size', type=int, default=36, help="size of a candle (default=36s)")
def prepare_cmd(files: list[Path], dir: Path, candle_size: int):  #pragma: no cover
    """ prepare training data from historical data """
    click.echo(f'Generating training data...')
    for path in files:
        collector = DataCollector()
        main_chart = Chart(candle_size=candle_size)
        main_chart.register_callback(collector.on_candle)
        model = MarketModel()
        model.charts.append(main_chart)
        model.simulate_file(path)

        with open(DataCollector.data_path(path), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=collector.data[0].keys())
            writer.writeheader()
            writer.writerows(collector.data)


@click.command('predict')
@click.argument('files', nargs=-1, type=click.Path(exists=True, path_type=Path), help='files with test data (.csv)')
@click.option('-m', '--model-file', type=click.Path(exists=True, path_type=Path), default='hephaistos-model.json', help='model file')
def predict_cmd(files: tuple[Path,...], model_file: Path): # pragma: no cover
    """ predict based on a given model """
    click.echo(f"Predicting based on model '{model_file}'...")

    df = load_files(files)
    X, y = split_target(df)

    model = xgb.XGBClassifier()
    model.load_model(model_file)
    prob = model.predict_proba(X)

    QUANTILE = 0.95
    prob_short = prob[:, 0]
    prob_short_max = np.max(prob_short)
    prob_short_75 = np.quantile(prob_short, QUANTILE)
    
    prob_long = prob[:, 2]
    prob_long_max = np.max(prob_long)
    prob_long_75  = np.quantile(prob_long, QUANTILE)

    long_signals = prob_long > prob_long_75
    total_long_signals = np.sum(long_signals)
    correct_long_signals = np.sum(long_signals & (y == 2))
    long_rate = correct_long_signals/total_long_signals

    short_signals = prob_short > prob_short_75
    total_short_signals = np.sum(short_signals)
    correct_short_signals = np.sum(short_signals & (y == 0))
    short_rate = correct_short_signals/total_short_signals
    
    click.secho( '                short    long', bold=True)
    click.secho(f'    p max      {prob_short_max*100:6.2f}  {prob_long_max*100:6.2f}')
    click.secho(f'    p {QUANTILE}%    {prob_short_75*100:6.2f}  {prob_long_75*100:6.2f}')
    click.secho(f'    total      {total_long_signals:6d}  {total_short_signals:6d}')
    click.secho(f'    correct    {correct_long_signals:6d}  {correct_short_signals:6d}')
    click.secho(f'    rate       {long_rate*100:6.2f}  {short_rate*100:6.2f}')


@click.command('eval')
@click.argument('file', type=str, help="file to be evaluated (.dbn)")
@click.option('-s', '--candle-size', type=int, default=36, help="size of a candle in sec (default=36)")
@click.option('-m', '--model-file', type=str, default='hephaistos-model.json', help="model file (default='Hephaistos-model.json')")
@click.option('-t', '--threshold', type=int, default=65, help='threshold to start a trade (default=65%)')
@click.option('-n', '--num-candles', type=int, help='number of candles to simulate')
@click.option('-o', '--out-file', type=str, required=True, help="name of output file")
def eval_cmd(file: Path, candle_size:int, model_file: Path, threshold: int, num_candles: int, out_file: Path): # pragma; no cover
    """ evaluate a trades file with Hephaistos """
    click.echo(f"Evaluating file '{file}' based on '{model_file}'")
    
    chart = Hephaistos.simulate(file, model_file, candle_size, num_candles, threshold)
    chart.to_file(out_file, fieldnames=Candle.OHLC_FIELDNAMES + Hephaistos.FIELDNAMES)
    click.echo(f"candles written to '{out_file}'")
