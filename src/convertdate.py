from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 2. FUNKTION: Beliebiger Zeitpunkt -> Letzter CME-Session-Start (UTC)
def session_start(dt_input: datetime) -> datetime:
    """Berechnet das CME-Start-datetime (17:00 Chicago) unmittelbar VOR dt_input."""

    tz_chicago = ZoneInfo("America/Chicago")
    dt_chicago = dt_input.astimezone(tz_chicago)
    session_start = datetime.combine(dt_chicago.date(), time(17, 0, 0), tzinfo=tz_chicago)
    return session_start.astimezone(ZoneInfo("UTC"))

# 3. FUNKTION: Session-Start -> Session-Ende (Stoppt vor der CME-Pause)
def session_end(dt_session_start: datetime) -> datetime:
    """Fügt 23 Stunden hinzu, um die tägliche CME-Pause (16:00 Chicago) zu treffen."""
    return dt_session_start + timedelta(hours=23)

# 5. FUNKTION: datetime-Objekt -> String für Tradovate
def tradovate_format(dt_session: datetime) -> str:
    """Wandelt ein datetime in das Tradovate-ISO-Format mit 'Z' um."""
    return dt_session.strftime("%Y-%m-%dT%H:%M:%SZ")

def databento_download_intervall(date: datetime) -> (datetime, datetime):
    """liefert das download intervall eines tages für databento"""
    start_date = session_start(date)
    end_date = start_date + timedelta(hours=24)
    return (start_date, end_date)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser("converts dates")
    parser.add_argument("date", type=str, help="a date in format 'YYYY-MM-DD'")
    args = parser.parse_args()
    
    date_str = args.date
    date = datetime.fromisoformat(date_str)
    start_date = session_start(date)
    end_date = session_end(start_date)
    download = databento_download_intervall(date)

    print(f'{parser.prog}: command line:     {date_str}')
    print(f'{parser.prog}: parsed date:      {date}')
    print(f'{parser.prog}: session start:    {start_date}')
    print(f'{parser.prog}: session end:      {end_date}')
    print(f'{parser.prog}: download:         {download[0]}...{download[1]}')
    print(f'{parser.prog}: databento format: {start_date.isoformat()}')
    print(f'{parser.prog}: tradovate format: {tradovate_format(date)}')
