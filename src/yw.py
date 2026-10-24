#
# Yesterdays Weather trader
#

from model import MarketModel, Chart, Candle

class YesterdaysWeather:

    FIELDNAMES = ['contracts', 'stop_loss', 'ema_fast', 'ema_slow']
    def __init__(self, trend_length: int = 3, max_loss: int = 50, stop_loss_factor: float = 0.6):
        self.TREND_LENGTH = trend_length
        self.MAX_LOSS = max_loss
        self.STOP_LOSS_FACTOR = stop_loss_factor

    def contract_size(self, direction: int, candle: Candle, chart: Chart) -> (int, int):
        """ calculates contract size and stop loss of a contract """
        stop_loss = round(chart.average_range(9) * self.STOP_LOSS_FACTOR)
        max_contracts = self.MAX_LOSS // stop_loss
        if direction < 0:
            return -max_contracts, stop_loss
        elif direction > 0:
            return max_contracts, stop_loss
        else:
            return 0, 0 # pragma: no cover

    def on_candle(self, candle: Candle, chart: Chart):
        contracts, stop_loss = 0, 0

        trend = chart.trend_length
        if candle.direction > 0:
            # we may go long...
            if trend >= self.TREND_LENGTH:
                # we have a trend of a least 2 and we are not completely above fast EMA
                contracts, stop_loss = self.contract_size(1, candle, chart)
        elif candle.direction < 0:
            # we may go short...
            if trend >= self.TREND_LENGTH:
                contracts, stop_loss = self.contract_size(-1, candle, chart)

        candle.contracts = contracts
        candle.stop_loss = stop_loss

    def simulate(file, num_candles: int = None, candle_size: int = 36, **kwargs): # pragma: no cover
        main_chart = Chart(candle_size=candle_size)
        model = MarketModel()
        model.charts.append(main_chart)
        trader = YesterdaysWeather(**kwargs)
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
    parser.add_argument('-l', '--trend-length', type=int, default=4, help="length of the trend needed for a signal")
    parser.add_argument('-m', '--max-loss', type=int, default=50, help="name of file for volume profile data")
    parser.add_argument('-s', '--stop-loss-factor', type=float, default=0.6, help="stop loss adjustment factor")
    args = parser.parse_args()

    main_chart = YesterdaysWeather.simulate(
        file=args.file,
        num_candles=args.num_candles,
        candle_size=args.candle_size,
        trend_length=args.trend_length,
        max_loss=args.max_loss,
        stop_loss_factor=args.stop_loss_factor,
    )
    main_chart.to_file(args.out_file, fieldnames=Candle.OHLC_FIELDNAMES + YesterdaysWeather.FIELDNAMES)
