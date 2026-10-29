#
# TurningPoint
#
# dieser Trader steigt ein, wenn EMA9 die Richtung wechselt...
#

from .model import MarketModel, Chart, Candle

class TurningPoint:

    FIELDNAMES = ['contracts', 'stop_loss', 'ema_fast', 'ema_slow', 'ema_fast_grad']

    def __init__(self, max_loss: int, stop_loss: int, min_distance: int, min_gradient: float):
        self.MAX_LOSS = max_loss
        self.STOP_LOSS = stop_loss
        self.MIN_DISTANCE = min_distance
        self.MIN_GRADIENT = min_gradient

    def contract_size(self, direction: int, avg_range: int) -> (int, int):
        """ calculates contract size and stop loss of a contract """
        stop_loss = self.STOP_LOSS
        max_contracts = self.MAX_LOSS // stop_loss
        if direction < 0:
            return -max_contracts, stop_loss
        elif direction > 0:
            return max_contracts, stop_loss
        else:
            return 0, 0 # pragma: no cover

    def on_candle(self, candle: Candle, chart: Chart):
        contracts, stop_loss = 0, 0
        delta_ema, delta_threshold, ema_fast_grad, ema_slow_grad = 0, 0, 0, 0

        if len(chart) > 48: # TODO: Konstante definieren: wir können starten, wenn alle daten aus der vergangenheit vorhanden sind.
            avg_range = chart.average_range(9)
            ema_fast = candle.ema_fast
            ema_slow = candle.ema_slow

            candle_1 = chart.look_back(1)
            ema_fast_1 = candle_1.ema_fast
            ema_slow_1 = candle_1.ema_slow
            delta_ema = ema_fast - ema_slow
            ema_slow_grad = ema_slow - ema_slow_1
            ema_fast_grad = ema_fast - ema_fast_1

            if (                delta_ema > self.MIN_DISTANCE  # ema_fast is far above ema_slow, we may go short...
                and candle.low - ema_slow < self.MIN_DISTANCE  # candle is in touch with ema_slow
                and            candle.low > ema_slow           # but is still above
                and         -candle.delta > self.MIN_GRADIENT  # candle is falling fast
                and        -ema_fast_grad > self.MIN_GRADIENT):# ema_fast is falling fast
                # we take our chance go short
                contracts, stop_loss = self.contract_size(-1, avg_range)
            elif (               delta_ema < -self.MIN_DISTANCE # ema_fast is far below ema_slow, we may go long... 
                and candle.high - ema_slow > -self.MIN_DISTANCE # candle is in touch we ema_slow
                and            candle.high < ema_slow           # but still below
                and           candle.delta > self.MIN_GRADIENT  # candle is rising fast
                and          ema_fast_grad > self.MIN_GRADIENT):# ema_fast is rising fast
                # we take our chance and go long
                contracts, stop_loss = self.contract_size(1, avg_range)

        candle.delta_ema = delta_ema
        candle.delta_threshold = delta_threshold
        candle.ema_fast_grad = ema_fast_grad
        candle.ema_slow_grad = ema_slow_grad
        candle.contracts = contracts
        candle.stop_loss = stop_loss

    def on_overlap(self, candle, chart):
        contracts, stop_loss = 0, 0
        ema_fast_grad = 0

        if len(chart) > 48: # TODO: Konstante definieren: wir können starten, wenn alle daten aus der vergangenheit vorhanden sind.
            ema_fast = candle.ema_fast
            ema_slow = candle.ema_slow

            if candle.range < 50 and abs(ema_fast - ema_slow) > 20:
                # we only do something if volatility is not too high
                candle_1 = chart.look_back(1)
                ema_fast_1 = candle_1.ema_fast
                ema_fast_grad = ema_fast - ema_fast_1

                if (                  ema_fast  >  ema_slow               # ema_fast is far above ema_slow, we may go short...
                    and candle.high > ema_fast and candle.low < ema_slow  # candle overlaps both
                    and         candle.average  >  ema_slow               # average is still above ema_slow, it is not too late..
                    and          -candle.delta  >  self.MIN_GRADIENT      # candle is falling fast
                    and         -ema_fast_grad  >  self.MIN_GRADIENT):    # ema_fast is falling fast
                    # we take our chance go short
                    contracts, stop_loss = self.contract_size(-1, self.STOP_LOSS)
                elif (                ema_fast  <  ema_slow               # ema_fast is far below ema_slow, we may go long... 
                    and  candle.low < ema_fast and candle.high > ema_slow # there is an overlap
                    and         candle.average  <  ema_slow               # average is still below ema_slow
                    and           candle.delta  >  self.MIN_GRADIENT      # candle is rising fast
                    and          ema_fast_grad  >  self.MIN_GRADIENT):    # ema_fast is rising fast
                    # we take our chance and go long
                    contracts, stop_loss = self.contract_size( 1, self.STOP_LOSS)

        candle.ema_fast_grad = ema_fast_grad
        candle.contracts = contracts
        candle.stop_loss = stop_loss

    def simulate(file, num_candles: int = None, candle_size: int = 36, **kwargs): # pragma: no cover
        main_chart = Chart(candle_size=candle_size)
        model = MarketModel()
        model.charts.append(main_chart)
        trader = TurningPoint(**kwargs)
        #main_chart.register_callback(trader.on_candle)
        main_chart.register_callback(trader.on_overlap)
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
    parser.add_argument('-s', '--stop-loss', type=int, default=80, help="stop loss adjustment factor")
    parser.add_argument('-d', '--min-distance', type=float, default=12, help="threshold factor of distance between short and long EMA")
    parser.add_argument('-g', '--min-gradient', type=float, default=15, help="factor used in gradient comparison between EMA short and long")
    args = parser.parse_args()

    main_chart = TurningPoint.simulate(
        file=args.file,
        candle_size=args.candle_size,
        num_candles=args.num_candles,
        max_loss=args.max_loss,
        stop_loss=args.stop_loss,
        min_distance=args.min_distance,
        min_gradient=args.min_gradient,
    )
    main_chart.to_file(args.out_file, fieldnames=Candle.OHLC_FIELDNAMES + TurningPoint.FIELDNAMES)
