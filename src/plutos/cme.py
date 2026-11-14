"""
interface to market data

 * supports funtionality to load, store and stream market data.
 * streams may be live or from files
 * uses Databento as data provider
"""

import click
import math

from datetime import UTC, date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def symbol_code(product_code: str, date: date) -> str:
    """ construct the symbol code from a product_code for a given date """
    MONTH_CODE = 'FGHJKMNQUVXZ'
    return f'{product_code.upper()}{MONTH_CODE[date.month-1]}{date.year%10}'


def rollover_day(date: date) -> datetime:
    """ calculates the next roll over date for a given month """

    DAYS_BEFORE_3RD_FRIDAY = 4 # amount of days roll over date is before 3. Friday
    quartal = (date.month - 1) // 3 + 1
    first_day = datetime(date.year, quartal * 3, 1)
    first_weekday = first_day.weekday()  # Wochentag des 1. Tages (0 = Montag, 4 = Freitag, 6 = Sonntag)
    days_to_first_friday = (4 - first_weekday) % 7
    return first_day + timedelta(days=(days_to_first_friday + 14 - DAYS_BEFORE_3RD_FRIDAY))


def active_symbol(symbol: str, date: date):
    """
    Ermittelt automatisch das aktive Kontraktsymbol für ein gegebenes Datum.
    Rollover findet am Montag vor dem 3. Freitag im März, Juni, September und Dezember statt.
    """

    rollover = rollover_day(date)
    dt = datetime(date.year, date.month, date.day)
    if not dt < rollover:
        next_month = dt + timedelta(days=30)
        rollover = rollover_day(next_month)
    return symbol_code(symbol, rollover)


def session(dt: datetime) -> (datetime, datetime):
    """ calculate start and end time of a CME session based on a given date """
    end_date = datetime(dt.year, dt.month, dt.day, 17, 0, tzinfo=ZoneInfo("America/Chicago"))
    start_date = end_date - timedelta(days=1)
    return (start_date.astimezone(UTC), end_date.astimezone(UTC))


def sample_index(timestamp: float) -> int:
    """ calculate the index of a sample in a CME session based on a given date """
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    start, end = session(dt)
    if dt >= end:
        start = end
    return math.floor((dt - start).total_seconds())
