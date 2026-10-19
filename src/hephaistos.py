#
# Hephaistos is the AI Trader of Plutos
#

def train_cmd(prog_name: str, args): #pragma: no cover
    """ tain the model """
    print('I am training')

def data_cmd(prog_name: str, args):  #pragma: no cover
    """ generate training data from historical data """
    print('I generate training data')

def test_cmd(prog_name: str, args): # pragma: no cover
    """ test a modell """
    print ('I am testing')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Hephaistos training utility")
    parser.set_defaults(command=lambda prog_anme, args: parser.print_usage())
    subparsers = parser.add_subparsers()

    train = subparsers.add_parser('train', description='train a model with historical data')
    train.add_argument('files', nargs='+', help='files with training data (.csv')
    train.add_argument('-m', '--model', help='model file')
    train.set_defaults(command=train_cmd)

    data = subparsers.add_parser('data', description='generate training data out of Databento native files')
    data.add_argument('file', nargs='+', help='files with historical data in Databento native file (.dbn)')
    data.add_argument('-d', '--dir', type=str, default=None, help="directory where to put the output files")
    data.set_defaults(data=data_cmd)

    test = subparsers.add_parser('test', description='test a modell on historical data')
    test.add_argument('files', nargs='+', help='files with historical data in Databento native file (.dbn)')
    test.add_argument('-m', '--model', help='model file')
    test.set_defaults(command=test_cmd)
    args = parser.parse_args()
    args.command(parser.prog, args)
