from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.reports.views',
    url(r'^$', 'index'),
    url(r'^list/$', 'list'),
    url(r'^(?P<problem_id>\d+)/$', 'item'),
)
