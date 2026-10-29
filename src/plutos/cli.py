#
# main cli for chart commands
#

import click
from .findcontracts import find_contracts
from .visu import show
from .chartsim import sim

@click.group()
def plutos():
    pass

plutos.add_command(find_contracts)
plutos.add_command(show)
plutos.add_command(sim)

if __name__ == "__main__":
    plutos()
