#
# find contracts in a charts file
#

import csv

def find_contracts(file: str):
    print(f'searching for contracts in file "{file}"')

    with open(file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        i = 0
        print('    time  contracts  stop_loss')
        for candle in reader:
            if int(candle['contracts']) != 0:
                print(f"    {i:4d}  {int(candle['contracts']):9d}  {int(candle['stop_loss']):9d}")
            i += 1

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="find contracts in chart file")
    parser.add_argument('file', type=str, help="chart file")
    args = parser.parse_args()

    find_contracts(args.file)       
