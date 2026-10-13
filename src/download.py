#
# download script for Databento historical data
#

from datetime import datetime, timezone

import marketdata


def download(prog_name: str, product_code: str, start: datetime, end: datetime): #pragma: no cover
    symbol = marketdata.active_symbol(args.product_code, end)
    print(f"{prog_name}: loading trades of {symbol} for intervall [{start.isoformat()}, {end.isoformat()}]")
    return marketdata.download_trades(symbol, start.isoformat(), end.isoformat())

def session_cmd(prog_name: str, args): #pragma: no cover
    """load trades of a CME session from databento"""

    dt = datetime.fromisoformat(args.date)
    start_date, end_date = marketdata.CME_session(dt)
    return download(prog_name, args.product_code, start_date, end_date)

def trades_cmd(prog_name: str, args):  #pragma: no cover
    return download(
        prog_name, 
        args.product_code,
        start = datetime.fromisoformat(args.start),
        end = datetime.fromisoformat(args.end),
    )
   
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="download trades from databento")
    parser.set_defaults(command=lambda args: parser.print_usage())
    subparsers = parser.add_subparsers()

    session = subparsers.add_parser('session', description='download a complete CME session')
    session.add_argument('file', help='name of Databento native file (.dbn)')
    session.add_argument('-p', '--product-code', type=str, default='MNQ', help="product code of future (NQ/MNQ/ES)")
    session.add_argument('-d', '--date', type=str, required=True, help="date of session")
    session.set_defaults(command=session_cmd)

    trades = subparsers.add_parser('trades', description='download trades by time stamp')
    trades.add_argument('file', help='name of Databento native file (.dbn)')
    trades.add_argument('-p', '--product-code', type=str, default='MNQ', help="product code of future (NQ/MNQ/ES)")
    trades.add_argument('-s', '--start', type=str, required=True, help="start time in ISO format")
    trades.add_argument('-e', '--end', type=str, required=True, help="end time in ISO format")
    trades.set_defaults(command=trades_cmd)

    args = parser.parse_args()
    data = args.command(parser.prog, args)

    if data:
        download_start = datetime.fromtimestamp(data.metadata.start // 10**9, timezone.utc)
        download_end = datetime.fromtimestamp(data.metadata.end // 10**9, timezone.utc)
        print(f"{parser.prog}: records downloaded: [{download_start.isoformat()}, {download_end.isoformat()}]")
        data.to_file(args.file)
        print(f"{parser.prog}: {data.nbytes} bytes written to {args.file}")
    else:
        print(f'{parser.prog}: download failed.')
