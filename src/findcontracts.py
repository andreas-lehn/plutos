#
# find contracts in a charts file
#

import io
import csv
import click

@click.command()
@click.argument('file', type=click.File('r', encoding='utf-8'), help="chart file")
def find_contracts(file: io.TextIOWrapper):
    """ find contracts in a chart file """
    click.echo(f'searching for contracts in file "{file.name}"')

    reader = csv.DictReader(file)
    i = 0
    click.secho('    time  contracts  stop_loss', bold=True)
    for candle in reader:
        if int(candle['contracts']) != 0:
            print(f"    {i:4d}  {int(candle['contracts']):9d}  {int(candle['stop_loss']):9d}")
        i += 1


if __name__ == '__main__':
    find_contracts()       
