from django.conf.urls import patterns, url

urlpatterns = patterns('webfaf.dumpdirs.views',
    url(r'^$', 'index'),
    url(r'^(?P<dumpdir_name>[^/]+)$', 'item'),
    url(r'^new/$', 'new'),
    url(r'^new/(?P<dumpdir_name>[^/]+)$', 'new'),
    url(r'^delete/(?P<dumpdir_name>[^/]+)$', 'delete'),
)
