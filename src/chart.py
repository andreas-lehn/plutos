#
# main cli for chart commands
#

import click
from src.findcontracts import find_contracts
from src.visu import show
from src.chartsim import sim

@click.group()
def chart():
    pass

chart.add_command(find_contracts)
chart.add_command(show)
chart.add_command(sim)

if __name__ == "__main__":
    chart()
