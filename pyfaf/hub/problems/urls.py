from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.problems.views',
    url(r'^hot/$', 'hot'),
    url(r'^hot/(?P<os_release>[^/]+)/$', 'hot'),
    url(r'^hot/(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'hot'),
    url(r'^hot/(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<duration>[^/]+)/$', 'hot'),

    url(r'^longterm/$', 'longterm'),
    url(r'^longterm/(?P<os_release>[^/]+)/$', 'longterm'),
    url(r'^longterm/(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'longterm'),
    url(r'^longterm/(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<duration>[^/]+)/$', 'longterm'),

    url(r'^(?P<problem_id>\d+)/$', 'summary'),
    url(r'^(?P<problem_id>\d+)/backtraces/$', 'backtraces'),
    url(r'^(?P<problem_id>\d+)/cluster/$', 'cluster'),
)
