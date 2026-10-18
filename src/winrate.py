#
# Evaluates trading signals
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

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate win rate")
    parser.add_argument('file', help='chart data in csv file')
    parser.add_argument('-l', '--look-ahead', type=int, default=3, help="look ahead distance (default == 3)")
    parser.add_argument('-b', '--bar-size', type=int, default=36, help="size of bar in seconds")
    args = parser.parse_args()

    chart = YesterdaysWeather.simulate(args.file, bar_size=args.bar_size)
    df = pd.DataFrame([bar.to_filtered_dict(['average', 'contracts']) for bar in chart])
    wins, trades = win_rate(df, args.look_ahead)
    print(f'{parser.prog}: win rate: {wins/trades*100:.2f}% ({wins} of {trades} trades)')
