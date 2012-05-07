from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.summary.views',
    url(r'^$', 'summary'),
    url(r'^(?P<os_release>[^/]+)/$', 'summary'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'summary'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<duration>[^/]+)/$', 'summary'),
)
