from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.summary.views',
    url(r'^$', 'index'),
    url(r'^(?P<os_release>[^/]+)/$', 'index'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'index'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<duration>[^/]+)/$', 'index'),
)
