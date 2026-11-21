#
# main cli for plutos commands
#

import click
from . import findcontracts
from . import visu
from . import chartsim
from . import marketdata
from . import chart

@click.group()
def plutos():
    pass

plutos.add_command(findcontracts.find_contracts)
plutos.add_command(visu.show)
plutos.add_command(chartsim.sim)
plutos.add_command(marketdata.download_session)
plutos.add_command(marketdata.info)
plutos.add_command(marketdata.samples)
plutos.add_command(chart.chart_cmd)

if __name__ == "__main__":
    plutos()
