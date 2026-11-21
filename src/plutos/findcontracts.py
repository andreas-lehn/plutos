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

@click.command()
@click.argument('file', type=click.File('r', encoding='utf-8'), help="chart file")
def find_signals(file: io.TextIOWrapper):
    """ find signals in chart file """
    click.echo(f"searching for signals in file '{file.name}'")

    reader = csv.DictReader(file)
    click.secho('  index  signal  probability', bold=True)
    for candle in reader:
        index = int(candle['index'])
        p_short = float(candle['p_short'])
        p_long  = float(candle['p_long'])
        if candle['signal_short'] == 'True':
            print(f"  {index:5d}   short  {p_short:11.2f}")
        if candle['signal_long'] == 'True':
            print(f"  {index:5d}    long  {p_long:11.2f}")


if __name__ == '__main__':
    find_contracts()       
