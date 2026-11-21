#
# main cli for chart commands
#

import click
from . import findcontracts
from . import visu
from . import chartsim
from . import marketdata
from . import chart
from . import hephaistos as hep
from . import datasetcategory
from . import labeler

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

@click.group()
def hephaistos():
    pass

hephaistos.add_command(labeler.label_cmd)
hephaistos.add_command(hep.prepare_cmd)
hephaistos.add_command(hep.fit_cmd)
hephaistos.add_command(hep.predict_cmd)
hephaistos.add_command(hep.eval_cmd)
hephaistos.add_command(hep.prec_recall)
hephaistos.add_command(datasetcategory.category)

if __name__ == "__main__":
    plutos()
