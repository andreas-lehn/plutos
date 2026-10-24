#
# Evaluates trading signals
#
# a signal is considered as correct,
# if the trend of the next 3 candles (average) goes in the direction of the signal
#
# let b_0 be the candle of the signal.
# then the following conditions must be fulfilled:
#
#  (1) b_3.average > b_1.average
#  (2) b_2.average > b_1.average
#  (3) b_3.average - b_1.avarage > average_range(9) / 2
#
# these condition are for a long signal.
#

import pandas as pd
from yw import YesterdaysWeather

def win_rate(df: pd.DataFrame, look_ahead: int):
    """ computes the total win, win_rate, profit_faktor """

    df['look_ahead'] = df['average'].shift(-look_ahead)
    df['result'] = (df['look_ahead'] - df['average']) * df['contracts']
    wins = (df['result'] > 0).sum()
    trades = (df['contracts'] != 0).sum()
    return wins, trades

def split_filename(filename: str):
    from pathlib import Path
    p = Path(filename)
    s = p.stem.split('_')
    return s[0], s[1], s[2], p.suffix

if __name__ == '__main__':
    import argparse
    from datetime import date

    parser = argparse.ArgumentParser(description="Evaluate win rate")
    parser.add_argument('files', nargs="+", help='chart data in csv file')
    parser.add_argument('-l', '--look-ahead', type=int, default=3, help="look ahead distance (default == 3)")
    parser.add_argument('-b', '--candle-size', type=int, default=36, help="size of candle in seconds")
    args = parser.parse_args()

    results = []
    for file in args.files:
        chart = YesterdaysWeather.simulate(file, candle_size=args.candle_size)
        df = pd.DataFrame([candle.to_filtered_dict(['average', 'contracts']) for candle in chart])
        wins, trades = win_rate(df, args.look_ahead)
        symbol, d, _, _ = split_filename(file)
        results.append({'date': date.fromisoformat(d), 'symbol': symbol, 'wins': wins, 'trades': trades})

    df_results = pd.DataFrame(results)
    df_results['win_rate'] = df_results['wins'] / df_results['trades']
    sum_wins = df_results['wins'].sum()
    sum_trades = df_results['trades'].sum()
    df_results = pd.concat([df_results, pd.DataFrame([{
            'date': None, 
            'symbol': 'Total', 
            'wins': sum_wins, 
            'trades': sum_trades,
            'win_rate': sum_wins/sum_trades
        }])])
    print(df_results)
