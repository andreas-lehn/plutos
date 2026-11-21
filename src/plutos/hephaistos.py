#
# Hephaistos is the AI Trader of Plutos
#

import os
import csv
import click
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve,  average_precision_score, confusion_matrix
from . import marketdata
from . import datasetcategory
from . import labeler
from .chart import Candle, Chart, MarketModel


START_OFFSET = 10 * 60 # don't begin trading bevor this offset in seconds since start of the session

class Hephaistos:

    FIELDNAMES = ['p_trade', 'p_short', 'p_long']

    def __init__(self, model_path: Path):
        self.model_long = xgb.XGBClassifier()
        self.model_short = xgb.XGBClassifier()
        self.model_no_trade = xgb.XGBClassifier()
        self.model_long.load_model(model_path + '_long.json')
        self.model_short.load_model(model_path + '_short.json')
        self.model_trade.load_model(model_path + '_trade.json')

 
    def on_candle(self, candle: Candle, chart: Chart):
        """ predict probalities for long, neutral, short """
        p_long, p_short, p_no_trade = 0.0, 0.0, 0.0

        if candle.index > START_OFFSET // candle.size:
            feature_set = FeatureGenerator.feature_set(candle, chart)
            df = pd.DataFrame([feature_set])
            p_short = self.model_short.predict_proba(df)[0][1]
            p_long  = self.model_long.predict_proba(df)[0][1]
            p_trade = self.model_trade.predict_proba(df)[0][1]

        candle.p_short = p_short
        candle.p_long  = p_long
        candle.p_trade = p_trade


    def simulate(file, model_path: Path, candle_size: int = 36, num_candles: int = None): # pragma: no cover
        main_chart = Chart(candle_size)
        model = MarketModel()
        model.charts.append(main_chart)
        trader = Hephaistos(model_path)
        main_chart.register_callback(trader.on_candle)
        model.simulate_file(file, num_candles * candle_size if num_candles else 24*60*60)
        return main_chart


class FeatureGenerator:
    """ delivers a feature set for each candle in a chart """

    def __init__(self, chart: Chart):
        self.chart = chart

    def feature_set(candle: Candle, chart: Chart):
        """ creates feature set of a candle """
        if candle.index <= START_OFFSET // candle.size:
            """ no feature set will be calculated before START_OFFSET in seconds """
            return None

        data = dict()
        average = candle.average
        ema_fast = candle.ema_fast
        ema_slow = candle.ema_slow
        ema_spread = candle.ema_spread
        volume = candle.volume
        #data['index'] = candle.index
        data['low'] = (candle.low - average) / average
        data['high'] = (candle.high - average) / average
        data['open'] = (candle.open - average) / average
        data['close'] = (candle.close - average) / average
        data['global_high'] = (candle.global_high - average) / average
        data['global_low'] = (candle.global_low - average) / average
        data['ema_fast'] = (ema_fast - average) / average
        data['ema_slow'] = (ema_slow - average) / average
        data['ema_spread'] = candle.ema_spread / candle.ema_slow
        data['range'] = candle.range / average
        data['body'] = candle.body / average
        data['delta'] = candle.delta / average
        data['atr']    = candle.atr / average

        candle_1 = chart[-2]
        average_1 = candle_1.average
        ema_fast_1 = candle_1.ema_fast
        ema_slow_1 = candle_1.ema_slow
        ema_spread_1 = candle_1.ema_spread
        volume_1 = candle_1.volume
        data['open_1']  = (candle.open - candle_1.open) / candle_1.open 
        data['low_1']   = (candle.low - candle_1.low) / candle_1.low
        data['average_1'] = (average - average_1) / average_1
        data['high_1']  = (candle.high - candle_1.high) / candle_1.high
        data['close_1'] = (candle.close - candle_1.close) / candle_1.close
        data['ema_fast_1'] = (ema_fast - ema_fast_1) / ema_fast_1
        data['ema_slow_1'] = (ema_slow - ema_slow_1) / ema_slow_1
        data['ema_spread_1'] = (ema_spread - ema_spread_1) / ema_slow_1
        data['volume_1'] = (volume - volume_1) / volume_1

        candle_2 = chart[-3]
        average_2 = candle_2.average
        ema_fast_2 = candle_2.ema_fast
        ema_slow_2 = candle_2.ema_slow
        ema_spread_2 =candle_2.ema_spread
        volume_2 = candle_2.volume
        data['low_2']   = (candle.low - candle_2.low) / candle_2.low
        data['average_2'] = (average - average_2) / average_2
        data['high_2']  = (candle.high - candle_2.high) / candle_2.high
        data['ema_fast_2'] = (ema_fast - ema_fast_2) / ema_fast_2
        data['ema_slow_2'] = (ema_slow - ema_slow_2) / ema_slow_2
        data['ema_spread_2'] = (ema_spread - ema_spread_2) / ema_slow_2
        data['volume_2'] = (candle.volume - volume_2) / volume_2

        data['average_accel'] = ((average - average_1) - (average_1 - average_2)) / average
        data['ema_fast_accel'] = ((ema_fast - ema_fast_1) - (ema_fast_1 - ema_fast_2)) / ema_fast
        data['ema_slow_accel'] = ((ema_slow - ema_slow_1) - (ema_slow_1 - ema_slow_2)) / ema_slow
        data['ema_spread_accel'] = ((ema_spread - ema_spread_1) - (ema_spread_1 - ema_spread_2)) / ema_slow
        data['volume_accel'] = ((volume - volume_1) - (volume_1 - volume_2)) / volume

        candle_3 = chart[-4]
        average_3 = candle_3.average
        ema_fast_3 = candle_3.ema_fast
        ema_slow_3 = candle_3.ema_slow
        ema_spread_3 = candle_3.ema_spread
        data['average_3'] = (average - average_3) / average_3
        data['ema_fast_3'] = (ema_fast - ema_fast_3) / ema_fast_3 
        data['ema_slow_3'] = (ema_slow - ema_slow_3) / ema_slow_3 
        data['ema_spread_3'] = (ema_spread - ema_spread_3) / ema_slow_3 

        candle_5 = chart[-6]
        average_5 = candle_5.average
        ema_fast_5 = candle_5.ema_fast
        ema_slow_5 = candle_5.ema_slow
        ema_spread_5 = candle_5.ema_spread
        data['average_5'] = (average - average_5) / average_5
        data['ema_fast_5'] = (ema_fast - ema_fast_5) / ema_fast_5 
        data['ema_slow_5'] = (ema_slow - ema_slow_5) / ema_slow_5 
        data['ema_spread_5'] = (ema_spread - ema_spread_5) / ema_slow_5 

        candle_9 = chart[-10]
        average_9 = candle_9.average
        ema_fast_9 = candle_9.ema_fast
        ema_slow_9 = candle_9.ema_slow
        ema_spread_9 = candle_9.ema_spread
        data['average_9'] = (average - average_9) / average_9
        data['ema_fast_9'] = (ema_fast - ema_fast_9) / ema_fast_9 
        data['ema_slow_9'] = (ema_slow - ema_slow_9) / ema_slow_9 
        data['ema_spread_9'] = (ema_spread - ema_spread_9) / ema_slow_9 

        return data

    FEATURE_FIELDNAMES = [
       #'index',
       'open', 'low', 'high', 'close', 'global_high', 'global_low', 'ema_fast', 'ema_slow', 'ema_spread', 'range', 'body', 'delta', 'atr',
       'open_1', 'low_1', 'average_1', 'high_1', 'close_1', 'ema_fast_1', 'ema_slow_1', 'ema_spread_1', 'volume_1',
       'low_2', 'average_2', 'high_2', 'ema_fast_2', 'ema_slow_2', 'ema_spread_2', 'volume_2',
       'average_accel', 'ema_fast_accel', 'ema_slow_accel', 'ema_spread_accel', 'volume_accel',
       'average_3', 'ema_fast_3', 'ema_slow_3', 'ema_spread_3',
       'average_5', 'ema_fast_5', 'ema_slow_5', 'ema_spread_5',
       'average_9', 'ema_fast_9', 'ema_slow_9', 'ema_spread_9',
    ]

    def append_targets(feature_set: dict, candle: Candle):
        """ append target values to feature set """
        feature_set['profit_chance'] = candle.profit_chance
        feature_set['trade'] = candle.trade

    TARGET_FIELDNAMES = ['profit_chance', 'trade']

    def __iter__(self):
        """ iterate through the chart and yield features sets """
        for candle in self.chart:
            feature_set = FeatureGenerator.feature_set(candle, self.chart)
            if not feature_set:
                continue
            FeatureGenerator.append_targets(feature_set, candle)
            yield feature_set


    def data_path(file: Path, dir: Path) -> Path:
        """ generates the path for feature data file from a source file path

        Home directory of file ist 'dir'/[training | eval | test] 
        File name content will be changed to 'features' and suffix to '.csv'
        """
        parts = marketdata.parse_path(file)
        parts['parent'] = dir / datasetcategory.category_path(parts['date'])
        parts['content'] = 'features'
        parts['suffix'] = '.csv'
        return marketdata.assemble_path(parts)


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


def split_target(df: pd.DataFrame): # pragma: no cover
    """ split target columns from feature values """
    x = df[FeatureGenerator.FEATURE_FIELDNAMES]
    y_short = (df[FeatureGenerator.TARGET_FIELDNAMES[0]] == 'short').astype(int)
    y_long  = (df[FeatureGenerator.TARGET_FIELDNAMES[0]] == 'long').astype(int)
    y_trade = (df[FeatureGenerator.TARGET_FIELDNAMES[1]]).astype(int)

    return x, y_short, y_long, y_trade


def fit_target(model_file_name: str, target_name: str, X_train, y_train, X_eval, y_eval):
    click.echo(f"fitting model for target '{target_name}'...")
    model = xgb.XGBClassifier(
        eval_metric='aucpr',
        #scale_pos_weight=2.0,
        early_stopping_rounds=25,
        n_estimators = 1500,
        learning_rate = 0.01,
        max_depth = 4,
        random_state = 42,
    )
    model.fit(X_train, y_train, eval_set=[(X_eval, y_eval)], verbose=True)
    file_name = model_file_name + '_' + target_name + '.json'
    model.save_model(file_name)
    click.echo(f"model written to '{file_name}'\n")
    return model


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
@click.option('-m', '--model-file', type=str, default='hephaistos-model', help="prefix of model file, default='hephaistos-model'")
def fit_cmd(training_dir: tuple[Path], eval_dir: tuple[Path], model_file: str): #pragma: no cover
    """ fit the model to training data """
    print('Fitting a model to training data...')

    training_files = tuple(f for f in training_dir.glob("*_features.csv") if f.is_file())
    df_training = load_files(training_files)
    X_train, y_short, y_long, y_trade = split_target(df_training)

    eval_files = tuple(f for f in eval_dir.glob("*_features.csv") if f.is_file())
    df_eval = load_files(eval_files)
    X_eval, y_eval_short, y_eval_long, y_eval_trade = split_target(df_eval)

    model_short = fit_target(model_file, 'short', X_train, y_short, X_eval, y_eval_short)
    model_long  = fit_target(model_file, 'long',  X_train, y_long,  X_eval, y_eval_long)
    model_trade = fit_target(model_file, 'trade', X_train, y_trade, X_eval, y_eval_trade)

    df_features = pd.DataFrame({
        "feature": X_train.columns, 
        "short [%]": model_short.feature_importances_ * 100,
        "long [%]":  model_long.feature_importances_ * 100,
        "trade [%]": model_trade.feature_importances_ * 100,
    })
    df_features['max [%]'] = df_features[['short [%]', 'long [%]', 'trade [%]']].max(axis=1)
    df_features = df_features.sort_values(by="max [%]", ascending=False).reset_index(
        drop=True
    )
    click.secho("Feature importance:", bold=True)
    click.echo(df_features.to_string(index=False, float_format="{:.2f}%".format))
    click.echo()


@click.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True, path_type=Path), required=True, help='eval files to compute precision recall for long')
@click.option('-m', '--model-file', type=str, default='hephaistos-model', help="model file, default='hephaistos-model'")
def prec_recall(files: list[Path], model_file: str):
    """ calculate precision reacall for long signals """
    """ predict based on a given model """
    click.echo(f"Precision recall based on model '{model_file}' with files {[f.name for f in files]}")

    df = load_files(files)
    X, y_short, y_long, y_trade = split_target(df)

    model_short, model_long, model_trade = xgb.XGBClassifier(), xgb.XGBClassifier(), xgb.XGBClassifier()
    model_short.load_model(model_file + '_short.json')
    model_long.load_model(model_file + '_long.json')
    model_trade.load_model(model_file + '_trade.json')
    proba_short = model_short.predict_proba(X)[:,1]
    proba_long = model_long.predict_proba(X)[:,1]
    proba_trade = model_trade.predict_proba(X)[:,1]

    # Precision und Recall für alle möglichen Schwellenwerte berechnen
    prec_short, _, thres_short = precision_recall_curve(y_short, proba_short)
    prec_long, _, thres_long = precision_recall_curve(y_long, proba_long)
    prec_trade, _, thres_trade = precision_recall_curve(y_trade, proba_trade)
    ap_short = average_precision_score(y_short, proba_short)
    ap_long = average_precision_score(y_long, proba_long)
    ap_trade = average_precision_score(y_long, proba_trade)

    plt.figure(figsize=(9, 6))
    plt.plot(thres_short, prec_short[:-1], label=f'short precision', color='red', linewidth=2)
    plt.plot(thres_long,  prec_long[:-1],  label=f'long precision',  color='green', linewidth=2)
    plt.plot(thres_trade, prec_trade[:-1],  label=f'trade precision', color='blue', linewidth=2)

    # Optional: Zufalls-Baselines (Anteil der positiven Labels im Testset)
    plt.axhline(y_short.mean(), color='red', linestyle='--', alpha=0.4, label=f'Short Baseline ({y_short.mean():.2%})')
    plt.axhline(y_long.mean(), color='green', linestyle='--', alpha=0.4, label=f'Long Baseline ({y_long.mean():.2%})')
    plt.axhline(y_trade.mean(), color='blue', linestyle='--', alpha=0.4, label=f'trade baseline ({y_trade.mean():.2%})')

    plt.title('precision recall curve')
    plt.xlabel('recall')
    plt.ylabel('precision')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


@click.command('prepare')
@click.argument('files', nargs=-1, type=click.Path(exists=True, path_type=Path), required=True, help='files with historical data in Databento native file (.dbn)')
@click.option('-d', '--dir', type=click.Path(), help="directory where to put the output files")
@click.option('-s', '--candle-size', type=int, default=36, help="size of a candle (default=36s)")
@click.option('-l', '--trend-length', type=int, default=5, help="length of trend (in candles) to be labeled")
@click.option('-r', '--risk', type=int, default=24, help="maximum risk to be taken (in ticks)")
@click.option('-p', '--profit', type=int, default=48, help="profit to be achieved (in ticks)")
@click.option('-w', '--window-size', type=int, default=12, help="size of tripple barrier window in candles")
def prepare_cmd(files: list[Path], dir: Path, candle_size: int, trend_length: int, risk: int, profit: int, window_size: int):  #pragma: no cover
    """ prepare training data from historical data """
    click.echo(f'Generating training data...')

    if not dir:
        dir = Path(os.environ.get('HEPHAISTOS_DIR', '.'))
    click.echo(f'Output directory: {dir}')

    for path in datasetcategory.CATEGORY:
        (dir / path).mkdir(parents=True, exist_ok=True)
    
    for path in files:
        main_chart = Chart(candle_size=candle_size)
        model = MarketModel()
        model.charts.append(main_chart)
        model.simulate_file(path)
        labeler.label(main_chart, trend_length, risk, profit, window_size)
        features = FeatureGenerator(main_chart)
        with open(FeatureGenerator.data_path(path, dir), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FeatureGenerator.FEATURE_FIELDNAMES + FeatureGenerator.TARGET_FIELDNAMES)
            writer.writeheader()
            for feature_set in features:
                writer.writerow(feature_set)


@click.command('predict')
@click.argument('files', nargs=-1, type=click.Path(exists=True, path_type=Path), required=True, help='files with test data (.csv)')
@click.option('-m', '--model-file', type=str, default='hephaistos-model', help='model file prefix')
@click.option('-p', '--probability', type=float, default=0.30, help="threshold probability for trades")
def predict_cmd(files: tuple[Path,...], model_file: Path, probability: float): # pragma: no cover
    """ predict based on a given model """
    click.echo(f"Predicting based on model '{model_file}'...")

    df = load_files(files)
    X, y_short, y_long, y_trades = split_target(df)

    model_short, model_long, model_trade = xgb.XGBClassifier(), xgb.XGBClassifier(), xgb.XGBClassifier()
    model_short.load_model(model_file + '_short.json')
    model_long.load_model(model_file + '_long.json')
    model_trade.load_model(model_file + '_trade.json')
    proba_trade = model_trade.predict_proba(X)[:,1]
    proba_short = model_short.predict_proba(X)[:,1]
    proba_long  = model_long.predict_proba(X)[:,1]
    proba_flat  = 1 - (proba_long + proba_short)

    df_proba = pd.DataFrame({'short': proba_short, 'neutral': proba_flat, 'long': proba_long, 'trade': proba_trade})
    click.secho("distribution of probabilities:", bold=True)
    click.echo(df_proba.describe(percentiles=[0.5, 0.75, 0.90, 0.95, 0.99]))

    # using probability as threshold
    raw_short = proba_short >= probability
    raw_long = proba_long >= probability

    both_active = raw_short & raw_long
    final_short = np.where(both_active, False, raw_short).astype(int)
    final_long = np.where(both_active, False, raw_long).astype(int)
    final_neutral = np.where((final_short == 0) & (final_long == 0), 1, 0)

    y_pred_final = np.zeros(len(X), dtype=int)
    y_pred_final[final_short == 1] = 0
    y_pred_final[final_neutral == 1] = 1
    y_pred_final[final_long == 1] = 2

    target = np.ones(len(X))
    target[y_short == 1] = 0
    target[y_long == 1] = 2
    # Die echte 3x3 Konfusionsmatrix berechnen
    cm = confusion_matrix(target, y_pred_final, labels=[0, 1, 2])

    # 1. Definiere lesbare Labels für die Achsen
    labels = ['short', 'neutral', 'long']

    # 2. Erstelle das DataFrame aus deiner berechneten Matrix 'cm'
    df_cm = pd.DataFrame(cm, index=labels, columns=labels)
    df_cm.index.name = "reality"
    df_cm['total'] = df_cm.sum(axis=1)
    df_cm.loc['total'] = df_cm.sum(axis=0)

    precision_row = []
    for label in labels:
        hit = df_cm.loc[label, label]
        total = df_cm.loc['total',  label]
        precision = (hit / total) * 100 if total > 0 else 0.0
        precision_row.append(f"{precision:.2f}")

    total_hit = df_cm.iloc[0, 0] + df_cm.iloc[1, 1] + df_cm.iloc[2, 2]
    total_samples = df_cm.loc['total', 'total']
    total_precision = (total_hit / total_samples) * 100 if total_samples > 0 else 0.0
    precision_row.append(f"{total_precision:.2f}")
    df_cm.loc["precision [%]"] = precision_row

    click.echo()
    click.secho(f'prediction for probability {probability:.2f}', bold=True)
    click.echo(df_cm.to_string())
    click.echo()


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
