from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.reports.views',
    url(r'^list/$', 'listing'),
    url(r'^list/(?P<os_release>[^/]+)/$', 'listing'),
    url(r'^list/(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'listing'),
    url(r'^list/(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<destination>[^/]+)/$', 'listing'),
    url(r'^list/(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<destination>[^/]+)/(?P<status>[^/]+)/$', 'listing'),

    url(r'^new/$', 'new'),

    url(r'^(?P<report_id>\d+)/$', 'item'),
    url(r'^$', 'index'),
    url(r'^(?P<os_release>[^/]+)/$', 'index'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'index'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<duration>[^/]+)/$', 'index'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<duration>[^/]+)/(?P<graph_type>[^/]+)/$', 'index'),
)
