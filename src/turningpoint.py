#
# TurningPoint
#
# dieser Trader steigt ein, wenn EMA9 die Richtung wechselt...
#

from model import MarketModel, Chart, Bar

class TurningPoint:

    FIELDNAMES = ['contracts', 'stop_loss', 'ema_9', 'ema_48']
    EMA_MID_FACTOR = 0.5

    def __init__(self, max_loss: int = 100, stop_loss_factor: float = 4.0, threshold_factor: float = 2.0, gradient_factor: float = 1.2):
        self.MAX_LOSS = max_loss
        self.STOP_LOSS_FACTOR = stop_loss_factor
        self.THRESHOLD_FACTOR = threshold_factor
        self.GRADIENT_FACTOR = gradient_factor
        self.ema_9 = None
        self.ema_48 = None

    def contract_size(self, direction: int, atr: int) -> (int, int):
        """ calculates contract size and stop loss of a contract """
        stop_loss = round(atr * self.STOP_LOSS_FACTOR)
        max_contracts = 1#self.MAX_LOSS // stop_loss
        if direction < 0:
            return -max_contracts, stop_loss
        elif direction > 0:
            return max_contracts, stop_loss
        else:
            return 0, 0 # pragma: no cover

    def on_bar(self, bar: Bar, chart: Chart):
        contracts, stop_loss = 0, 0

        if len(chart) > 48:
            ema_9 = bar.ema_9
            if self.ema_9 is None:
                self.ema_9 = ema_9
            ema_48 = bar.ema_48
            if self.ema_48 is None:
                self.ema_48 = ema_48

            atr = chart.average_range(9)
            threshold = self.THRESHOLD_FACTOR * atr
            delta_ema = ema_9 - ema_48

            if delta_ema > threshold and bar.delta < 0 and -(ema_9 - self.ema_9) > (ema_48 - self.ema_48) * self.GRADIENT_FACTOR:
                # ema_9 ist weit über ema_48 und fällt schnelle als ema_48 steigt
                # we go short
                contracts, stop_loss = self.contract_size(-1, atr)
            elif delta_ema < -threshold and bar.delta > 0 and (ema_9 - self.ema_9) > -(ema_48 - self.ema_48) * self.GRADIENT_FACTOR:
                # ema_9 is far below ema_48 and current bar is rising and ema short is rising much faster than ema long is sinking
                # we go long
                contracts, stop_loss = self.contract_size(1, atr)

            self.ema_9 = ema_9
            self.ema_48 = ema_48

        bar.contracts = contracts
        bar.stop_loss = stop_loss

    def simulate(file, num_bars: int = None, bar_size: int = 36, **kwargs): # pragma: no cover
        main_chart = Chart(bar_size=bar_size)
        model = MarketModel()
        model.charts.append(main_chart)
        trader = TurningPoint(**kwargs)
        main_chart.register_callback(trader.on_bar)
        model.simulate_file(file, num_bars * bar_size if num_bars else 24*60*60*10**9)
        return main_chart

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Simulate Yesterdays Weather trader on historical data")
    parser.add_argument('file', help='name of Databento native file (.dbn)')
    parser.add_argument('-b', '--bar-size', type=int, default=36, help="size of bar in seconds")
    parser.add_argument('-n', '--num-bars', type=int, default=sys.maxsize, help='number of bars to simulate')
    parser.add_argument('-o', '--out-file', type=str, required=True, help="name of output file")
    parser.add_argument('-m', '--max-loss', type=int, default=100, help="name of file for volume profile data")
    parser.add_argument('-s', '--stop-loss-factor', type=float, default=1.0, help="stop loss adjustment factor")
    parser.add_argument('-t', '--threshold-factor', type=float, default=1.5, help="threshold factor of distance between short and long EMA")
    parser.add_argument('-g', '--gradient-factor', type=float, default=1.8, help="factor used in gradient comparison between EMA short and long")
    args = parser.parse_args()

    main_chart = TurningPoint.simulate(
        file=args.file,
        bar_size=args.bar_size,
        num_bars=args.num_bars,
        max_loss=args.max_loss,
        stop_loss_factor=args.stop_loss_factor,
        threshold_factor=args.threshold_factor,
        gradient_factor=args.gradient_factor,
    )
    main_chart.to_file(args.out_file, fieldnames=Bar.OHLC_FIELDNAMES + TurningPoint.FIELDNAMES)
