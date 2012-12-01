from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.reports.views',
    url(r'^list/$', 'listing'),
    url(r'^list/(?P<os_release>[^/]+)/$', 'listing'),
    url(r'^list/(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'listing'),
    url(r'^list/(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<status>[^/]+)/$', 'listing'),

    url(r'^new/$', 'new'),
    url(r'^attach/$', 'attach'),

    url(r'^diff/(?P<lhs_id>\d+)/(?P<rhs_id>\d+)/$', 'diff'),

    url(r'^(?P<report_id>\d+)/$', 'item'),
    url(r'^$', 'index'),
    url(r'^(?P<os_release>[^/]+)/$', 'index'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'index'),
)
