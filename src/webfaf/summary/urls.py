from django.conf.urls import patterns, url

urlpatterns = patterns('webfaf.summary.views',
    url(r'^$', 'summary'),
    url(r'^(?P<os_release>[^/]+)/$', 'summary'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/$', 'summary'),
    url(r'^(?P<os_release>[^/]+)/(?P<component>[^/]+)/(?P<duration>[^/]+)/$', 'summary'),
)
