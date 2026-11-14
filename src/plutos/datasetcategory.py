#
# split market data into training, eval and test set
#

from datetime import date, datetime
import click

START_OF_PLUTOS_EPOCHE = datetime(2026, 8, 31)
CATEGORY = ['training', 'training', 'eval', 'training', 'training', 'test']

def category_index(d: date | datetime) -> int:
    if isinstance(d, date):
        d = datetime(d.year, d.month, d.day)

    delta_days = (d - START_OF_PLUTOS_EPOCHE).days
    weeks = delta_days // 7
    delta_week_days = delta_days - weeks * 2
    return delta_week_days % 6

def category_path(d: date | datetime) -> str:
    return CATEGORY[category_index(d)]

@click.command()
@click.argument('date', type=click.DateTime(), help="date of session in ISO format")
def category(date: datetime) -> str:
    """ determines the data set to which 'date' belongs """
    click.echo(category_path(date))

if __name__ == "__main__":
    category()
