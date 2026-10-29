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
# 
#

import pandas as pd

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

class Evaluator():

    def __init__(self, stop_loss_factor: float):
        self.stop_loss_factor: float = stop_loss_factor
        self.candles: list = []
        self.traded_candles: list = []
        self.tick_capture: int = 0
        self.wins: int = 0
        self.total_win: int = 0
        self.total_loss: int = 0

    @property
    def total_ticks(self):
        return self.total_win - self.total_loss
    
    @property
    def total_trades(self):
        return len(self.traded_candles)
    
    @property
    def win_rate(self):
        return self.wins / self.total_trades if self.total_trades != 0 else 0

    @property
    def profit_factor(self):
        return self.total_win / self.total_loss if self.total_loss != 0 else 0
    
    def load(self, reader):
        index = 0
        for row in reader:
            candle = {
                'index': index,
                'low': int(row['low']),
                'open': int(row['open']),
                'high': int(row['high']),
                'contracts': int(row['contracts']),
                'stop_loss': int(row['stop_loss']),
            }
            self.candles.append(candle)
            index += 1

    SPREAD = 1

    def evaluate(self):
        trading_candle = None
        open_price = None
        close_price = None
        stop_loss = None
        for candle in self.candles:
            if trading_candle:
                contracts = trading_candle['contracts']
                if open_price is None:
                    if contracts > 0:
                        open_price = candle['open'] + Evaluator.SPREAD
                        stop_loss = open_price - stop_loss
                    elif contracts < 0:
                        open_price = candle['open'] - Evaluator.SPREAD
                        stop_loss = open_price + stop_loss
                else:
                    if contracts > 0:
                        if stop_loss >= candle['low']:
                            close_price = stop_loss - Evaluator.SPREAD
                        stop_loss = round(self.stop_loss_factor * candle['low'] + (1 - self.stop_loss_factor) * stop_loss)
                    elif contracts < 0:
                        if stop_loss <= candle['high']:
                            close_price = stop_loss + Evaluator.SPREAD
                        stop_loss = round(self.stop_loss_factor * candle['high'] + (1 - self.stop_loss_factor) * stop_loss)
                if close_price:
                    self.fill_candle(trading_candle, open_price, close_price)
                    self.traded_candles.append(trading_candle)
                    trading_candle = None
            else:
                contracts = candle['contracts']
                if contracts != 0:
                    trading_candle = candle
                    stop_loss = candle['stop_loss']
                    open_price = None
                    close_price = None

    def fill_candle(self, candle, open_price, close_price):
        contracts = candle['contracts']
        total_ticks = (close_price - open_price) * contracts
        tick_capture = total_ticks / abs(contracts) if contracts != 0 else 0
        candle['open_price'] = open_price
        candle['close_price'] = close_price
        candle['tick_capture'] = tick_capture
        candle['total_ticks'] = total_ticks
        self.wins += 1 if total_ticks > 0 else 0
        self.tick_capture += tick_capture
        self.total_win += total_ticks if total_ticks > 0 else 0
        self.total_loss -= total_ticks if total_ticks < 0 else 0

    def __str__(self):
        return (
            f"total trades: {self.total_trades}, "
            f"ticks captured: {self.tick_capture}, total ticks: {self.total_ticks} ({self.total_win}/{self.total_loss}), "
            f"win rate: {self.win_rate*100:.2f}%, profit factor: {self.profit_factor:.2f}"
        )

if __name__ == '__main__':
    import argparse
    import csv
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Evaluate trading signal")
    parser.add_argument('file', type=Path, help='chart data in csv file')
    parser.add_argument('-s', '--stop-loss-factor', default=0.8, type=float, help="factor for adjusting the stop loss")
    args = parser.parse_args()

    evaluator = Evaluator(args.stop_loss_factor)
    with open(args.file, encoding="utf-8") as f:
        evaluator.load(csv.DictReader(f))
    evaluator.evaluate()

    df = pd.DataFrame(evaluator.traded_candles)
    print(df.to_string())
    print(f"{parser.prog}: {evaluator}")
