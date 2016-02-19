import datetime

from datetime import date


def combine_time(d1, d2):
    dt1 = datetime.timedelta(minutes=d1.minute, seconds=d1.second)
    dt2 = datetime.timedelta(minutes=d2.minute, seconds=d2.second)
    fin = dt1 + dt2
    return fin


def calculate_age(born, today=None):
    if today is None:
        today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
