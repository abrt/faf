import datetime
from django.conf.urls.defaults import *

urlpatterns = patterns(
    'pyfaf.hub.stats.views',

    url(r'^$', 'by_daterange'),

    url(r'^today/$', 'by_daterange',
        {'since': datetime.date.today(),
         'to': datetime.date.today() + datetime.timedelta(days=1)},
        name='today_stats'),

    url(r'^yesterday/$', 'by_daterange',
        {'since': datetime.date.today() - datetime.timedelta(days=1),
         'to': datetime.date.today()},
        name='yesterday_stats'),

    url(r'^last_week/$', 'by_daterange',
        {'since': datetime.date.today() - datetime.timedelta(days=7),
         'to': datetime.date.today()},
        name='last_week_stats'),

    url(r'^last_month/$', 'by_daterange',
        {'since': datetime.date.today() - datetime.timedelta(days=30),
         'to': datetime.date.today()},
        name='last_month_stats'),

    url(r'^last_year/$', 'by_daterange',
        {'since': datetime.date.today() - datetime.timedelta(days=365),
         'to': datetime.date.today()},
        name='last_year_stats'),

    url(r'^date/(?P<year>\d+)/(?P<month>\d+)/(?P<day>\d+)/$', 'by_date',
        name='day_stats'),

    url(r'^date/(?P<year>\d+)/(?P<month>\d+)/$', 'by_date',
        name='month_stats'),

    url(r'^date/(?P<year>\d+)/$', 'by_date',
        name='year_stats'),
)
