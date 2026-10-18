#
# Yesterdays Weather trader
#

from model import MarketModel, Chart, Bar

class YesterdaysWeather:

    FIELDNAMES = ['contracts', 'stop_loss', 'ema_9', 'ema_50']

    def __init__(self, look_back: int = 9, max_loss: int = 50, stop_loss_factor: float = 1.2):
        self.LOOK_BACK = look_back
        self.MAX_LOSS = max_loss
        self.STOP_LOSS_FACTOR = stop_loss_factor
        self.THRESHOLD = 1

    def contract_size(self, direction: int, bar: Bar) -> (int, int):
        """ calculates contract size and stop loss of a contract """
        if direction < 0:
            stop_loss = round((bar.high - bar.average) * self.STOP_LOSS_FACTOR)
            max_contracts = self.MAX_LOSS // stop_loss
            return -max_contracts, stop_loss
        elif direction > 0:
            stop_loss = round((bar.average - bar.low) * self.STOP_LOSS_FACTOR)
            max_contracts = self.MAX_LOSS // stop_loss
            return max_contracts, -stop_loss
        else:
            return 0, 0 # pragma: no cover

    def on_bar(self, bar: Bar, chart: Chart):
        contracts, stop_loss = 0, 0

        trend = chart.trend_length()
        if bar.direction > 0:
            # we may go long...
            if trend > 1 and bar.low < bar.ema_9:
                # we have a trend of a least 2 and we are not completely above EMA9
                contracts, stop_loss = self.contract_size(1, bar)
            elif bar.high < bar.ema_9:
                # we have a very small (starting?) trend and are completely below the moving average.
                contracts, stop_loss = self.contract_size(1, bar)
        elif bar.direction < 0:
            # we may go short...
            if trend > 1 and bar.high > bar.ema_9:
                contracts, stop_loss = self.contract_size(-1, bar)
            elif bar.low > bar.ema_9:
                contracts, stop_loss = self.contract_size(-1, bar)

        bar.contracts = contracts
        bar.stop_loss = stop_loss

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Simulate Yesterdays Weather trader on historical data")
    parser.add_argument('file', help='name of Databento native file (.dbn)')
    parser.add_argument('-b', '--bar-size', type=int, default=36, help="size of bar in seconds")
    parser.add_argument('-n', '--num-bars', type=int, default=sys.maxsize, help='number of bars to simulate')
    parser.add_argument('-o', '--out-file', type=str, required=True, help="name of output file")
    parser.add_argument('-m', '--max-loss', type=int, default=50, help="name of file for volume profile data")
    parser.add_argument('-l', '--look-back', type=int, default=9, help="look back distance")
    parser.add_argument('-s', '--stop-loss-factor', type=float, default=1.2, help="stop loss adjustment factor")
    args = parser.parse_args()

    main_chart = Chart(bar_size=args.bar_size)
    model = MarketModel()
    model.charts.append(main_chart)
    trader = YesterdaysWeather(
        look_back=args.look_back,
        max_loss=args.max_loss,
        stop_loss_factor=args.stop_loss_factor,
    )
    main_chart.register_callback(trader.on_bar)
    model.simulate_file(args.file, args.num_bars * args.bar_size)
    main_chart.to_file(args.out_file, fieldnames=Bar.OHLC_FIELDNAMES + YesterdaysWeather.FIELDNAMES)
