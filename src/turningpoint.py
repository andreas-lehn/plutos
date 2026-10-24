#
# TurningPoint
#
# dieser Trader steigt ein, wenn EMA9 die Richtung wechselt...
#

from model import MarketModel, Chart, Candle

class TurningPoint:

    FIELDNAMES = ['contracts', 'stop_loss', 'ema_fast', 'ema_slow']

    def __init__(self, max_loss: int = 100, stop_loss_factor: float = 4.0, threshold_factor: float = 2.0, gradient_factor: float = 1.2):
        self.MAX_LOSS = max_loss
        self.STOP_LOSS_FACTOR = stop_loss_factor
        self.THRESHOLD_FACTOR = threshold_factor
        self.GRADIENT_FACTOR = gradient_factor

    def contract_size(self, direction: int, avg_range: int) -> (int, int):
        """ calculates contract size and stop loss of a contract """
        stop_loss = round(avg_range * self.STOP_LOSS_FACTOR)
        max_contracts = 1#self.MAX_LOSS // stop_loss
        if direction < 0:
            return -max_contracts, stop_loss
        elif direction > 0:
            return max_contracts, stop_loss
        else:
            return 0, 0 # pragma: no cover

    def on_candle(self, candle: Candle, chart: Chart):
        contracts, stop_loss = 0, 0

        if len(chart) > 48: # TODO: Konstante definieren: wir können starten, wenn alle daten aus der vergangenheit vorhanden sind.
            avg_range = chart.average_range(9)
            threshold = self.THRESHOLD_FACTOR * avg_range
            ema_fast = candle.ema_fast
            ema_slow = candle.ema_slow

            candle_1 = chart.look_back(1)
            ema_fast_1 = candle_1.ema_fast
            ema_slow_1 = candle_1.ema_slow
            delta_ema = ema_fast - ema_slow

            if delta_ema > threshold and candle.delta < 0 and -(ema_fast - ema_fast_1) > (ema_slow - ema_slow_1) * self.GRADIENT_FACTOR:
                # ema_fast ist weit über ema_slow und fällt schneller als ema_slow steigt
                # we go short
                contracts, stop_loss = self.contract_size(-1, avg_range)
            elif delta_ema < -threshold and candle.delta > 0 and (ema_fast - ema_fast_1) > -(ema_slow - ema_slow_1) * self.GRADIENT_FACTOR:
                # ema_fast is far below ema_slow and current candle is rising and ema short is rising much faster than ema long is sinking
                # we go long
                contracts, stop_loss = self.contract_size(1, avg_range)

        candle.contracts = contracts
        candle.stop_loss = stop_loss

    def simulate(file, num_candles: int = None, candle_size: int = 36, **kwargs): # pragma: no cover
        main_chart = Chart(candle_size=candle_size)
        model = MarketModel()
        model.charts.append(main_chart)
        trader = TurningPoint(**kwargs)
        main_chart.register_callback(trader.on_candle)
        model.simulate_file(file, num_candles * candle_size if num_candles else 24*60*60*10**9)
        return main_chart

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Simulate Yesterdays Weather trader on historical data")
    parser.add_argument('file', help='name of Databento native file (.dbn)')
    parser.add_argument('-b', '--candle-size', type=int, default=36, help="size of candle in seconds")
    parser.add_argument('-n', '--num-candles', type=int, default=sys.maxsize, help='number of candles to simulate')
    parser.add_argument('-o', '--out-file', type=str, required=True, help="name of output file")
    parser.add_argument('-m', '--max-loss', type=int, default=100, help="name of file for volume profile data")
    parser.add_argument('-s', '--stop-loss-factor', type=float, default=1.0, help="stop loss adjustment factor")
    parser.add_argument('-t', '--threshold-factor', type=float, default=1.5, help="threshold factor of distance between short and long EMA")
    parser.add_argument('-g', '--gradient-factor', type=float, default=1.8, help="factor used in gradient comparison between EMA short and long")
    args = parser.parse_args()

    main_chart = TurningPoint.simulate(
        file=args.file,
        candle_size=args.candle_size,
        num_candles=args.num_candles,
        max_loss=args.max_loss,
        stop_loss_factor=args.stop_loss_factor,
        threshold_factor=args.threshold_factor,
        gradient_factor=args.gradient_factor,
    )
    main_chart.to_file(args.out_file, fieldnames=Candle.OHLC_FIELDNAMES + TurningPoint.FIELDNAMES)
