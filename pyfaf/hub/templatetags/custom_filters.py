import calendar
import datetime

from django import template

register = template.Library()

@register.filter(name="epoch")
def epoch(value):
    """Converts date time in Custom Time zone to Unix time stamp in UTC"""
    return calendar.timegm(value.timetuple())

@register.filter(name="fancydate")
def fancydate(value, base_date=None):
    """
    Converts a date to a fancy string

    fancydate(datetime.date(2012,6,29), datetime.date(2012,6,28))
    "Future"
    fancydate(datetime.date(2012,6,28), datetime.date(2012,6,28))
    "Today"
    fancydate(datetime.date(2012,6,27), datetime.date(2012,6,28))
    "Yesterday"
    fancydate(datetime.date(2012,6,26), datetime.date(2012,6,28))
    "Thursday"
    fancydate(datetime.date(2012,6,25), datetime.date(2012,6,28))
    "Wednesday"
    fancydate(datetime.date(2012,6,24), datetime.date(2012,6,28))
    "Tuesday"
    fancydate(datetime.date(2012,6,23), datetime.date(2012,6,28))
    "Monday"
    fancydate(datetime.date(2012,6,22), datetime.date(2012,6,28))
    "Last week"
    fancydate(datetime.date(2012,6,2), datetime.date(2012,6,28))
    "3 weeks"
    fancydate(datetime.date(2012,6,1), datetime.date(2012,6,28))
    "4 weeks"
    fancydate(datetime.date(2012,5,31), datetime.date(2012,6,28))
    "Last month"
    """
    if not base_date:
        base_date = datetime.date.today()

    old_date = value.date()

    if base_date < old_date:
        return 'Future'

    d = base_date - old_date

    if d.days == 0:
        return 'Today'
    elif d.days == 1:
        return 'Yesterday'

    # this week - return a name of a day
    if d.days < base_date.isoweekday():
        return calendar.day_name[base_date.weekday() - d.days]

    if old_date.month == base_date.month and old_date.year == base_date.year:
        # computes a number of calendar weeks (not only 7 days)
        offset = round((d.days - base_date.isoweekday())/7, 0) + 1;
        name = 'week'
    elif old_date.year == base_date.year:
        offset = base_date.month - old_date.month
        name = 'month'
    else:
        offset = base_date.year - old_date.year
        name = 'year'

    if offset == 1:
        return "Last %s" % (name);

    return "%d %ss ago" % (offset, name);
