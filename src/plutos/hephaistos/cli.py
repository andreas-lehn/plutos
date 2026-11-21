#
# main cli for chart commands
#

import click
from . import core
from . import datasetcategory
from . import labeler

@click.group()
def hephaistos():
    pass

hephaistos.add_command(labeler.label_cmd)
hephaistos.add_command(core.prepare_cmd)
hephaistos.add_command(core.fit_cmd)
hephaistos.add_command(core.predict_cmd)
hephaistos.add_command(core.sim)
hephaistos.add_command(core.prec_recall)
hephaistos.add_command(datasetcategory.category)

if __name__ == "__main__":
    hephaistos()
