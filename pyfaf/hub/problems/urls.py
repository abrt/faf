from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.problems.views',
    url(r'^hot/$', 'hot'),
    url(r'^longterm/$', 'longterm'),
    url(r'^(?P<problem_id>\d+)/$', 'summary'),
    url(r'^(?P<problem_id>\d+)/backtraces/$', 'backtraces'),
    url(r'^(?P<problem_id>\d+)/cluster/$', 'cluster'),
)
