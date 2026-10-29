#
# main cli for chart commands
#

import click
from . import findcontracts
from . import visu
from . import chartsim
from . import marketdata
from . import model

@click.group()
def plutos():
    pass

plutos.add_command(findcontracts.find_contracts)
plutos.add_command(visu.show)
plutos.add_command(chartsim.sim)
plutos.add_command(marketdata.download_session)
plutos.add_command(model.chart_cmd)

if __name__ == "__main__":
    plutos()
