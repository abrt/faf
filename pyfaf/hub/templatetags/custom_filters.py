import calendar

from django import template

register = template.Library()

@register.filter(name="epoch")
def epoch(value):
    """Converts date time in Custom Time zone to Unix time stamp in UTC"""
    return calendar.timegm(value.timetuple())
