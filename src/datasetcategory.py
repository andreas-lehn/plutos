#
# split market data into training, eval and test set
#

from datetime import datetime
import click

START_OF_PLUTOS_EPOCHE = datetime(2026, 8, 31)
CATEGORY = ['training', 'training', 'eval', 'training', 'training', 'test']

def category_index(date: datetime) -> str:
    delta_days = (date - START_OF_PLUTOS_EPOCHE).days
    weeks = delta_days // 7
    delta_week_days = delta_days - weeks * 2
    return delta_week_days % 6

@click.command()
@click.argument('date', type=click.DateTime(), help="date of session in ISO format")
def category(date: datetime) -> str:
    """ determines the data set to which 'date' belongs """
    click.echo(CATEGORY[category_index(date)])

if __name__ == "__main__":
    category()
