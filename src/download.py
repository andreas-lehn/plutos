import argparse


def session_cmd(args):
    print('download session', args.date, 'level', args.level)

def trades_cmd(args):
    print('download trades'. args.start, args.end, 'level', args.level)

parser = argparse.ArgumentParser(description="download trades from databento")
parser.add_argument('-l', '--level', type=int, default='1', help="go to level <n>")
parser.set_defaults(command=lambda args: parser.print_usage())
subparsers = parser.add_subparsers()

session = subparsers.add_parser('session')
session.add_argument('-d', '--date', type=str, required=True, help="date of session")
session.set_defaults(command=session_cmd)

trades = subparsers.add_parser('trades')
trades.add_argument('-s', '--start', type=str, required=True, help="start date")
trades.add_argument('-e', '--end', type=str, required=True, help="end date")
trades.set_defaults(command=trades_cmd)

#parser.print_usage()
args = parser.parse_args()
args.command(args)
