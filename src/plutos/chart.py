#
# main cli for chart commands
#

import click
from .findcontracts import find_contracts
from .visu import show
from .chartsim import sim

@click.group()
def chart():
    pass

chart.add_command(find_contracts)
chart.add_command(show)
chart.add_command(sim)

if __name__ == "__main__":
    chart()
