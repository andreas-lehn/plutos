#
# Yesterdays Weather trader
#

from model import MarketModel, Chart, Bar

class YesterdaysWeather:

    FIELDNAMES = ['contracts', 'stop_loss']

    def __init__(self, look_back: int = 5, threshold: int = 5, max_loss: int = 50, stop_loss_factor: float = 1.2):
        self.LOOK_BACK = look_back
        self.THRESHOLD = threshold
        self.MAX_LOSS = max_loss
        self.STOP_LOSS_FACTOR = stop_loss_factor

    def contract_size(self, delta_1: int, delta_n: int, range:int) -> (int, int):
        """ calculates contract size and stop loss of a contract """
        stop_loss = round((range * self.STOP_LOSS_FACTOR) / 2)
        max_contracts = self.MAX_LOSS // stop_loss
        trend = self.trend(delta_1, delta_n)
        if trend < 0:
            return -max_contracts, stop_loss
        elif trend > 0:
            return max_contracts, -stop_loss
        else:
            return 0, 0

    def trend(self, delta_1: int, delta_n) -> int:
        """ calculate the trend """
        if abs(delta_1) < self.THRESHOLD or abs(delta_n) < self.THRESHOLD:
            return 0
        if abs(delta_1) * self.LOOK_BACK < abs(delta_n):
            return 0
        if delta_1 * delta_n < 0:
            return 0
        return delta_1
    
    def on_bar(self, bar: Bar, chart: Chart):
        if len(chart) <= self.LOOK_BACK:
            contracts = 0
            stop_loss = 0
        else:
            delta_1 = bar.delta
            delta_n = chart.delta(self.LOOK_BACK)
            range_n = chart.average_range(self.LOOK_BACK)
            contracts, stop_loss = self.contract_size(delta_1, delta_n, range_n)

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
    parser.add_argument('-t', '--threshold', type=int, default=5, help="trend threshold")
    parser.add_argument('-l', '--look-back', type=int, default=5, help="look back distance of long term trend")
    parser.add_argument('-s', '--stop-loss-factor', type=float, default=1.2, help="stop loss in relation to average range")
    args = parser.parse_args()

    main_chart = Chart(bar_size=args.bar_size)
    model = MarketModel()
    model.charts.append(main_chart)
    trader = YesterdaysWeather(
        look_back=args.look_back,
        threshold=args.threshold,
        max_loss=args.max_loss,
        stop_loss_factor=args.stop_loss_factor,
    )
    main_chart.register_callback(trader.on_bar)
    model.simulate_file(args.file, args.num_bars * args.bar_size)
    main_chart.to_file(args.out_file, fieldnames=Bar.OHLC_FIELDNAMES + YesterdaysWeather.FIELDNAMES)
