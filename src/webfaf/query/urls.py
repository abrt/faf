from django.conf.urls import patterns, url

urlpatterns = patterns('webfaf.query.views',
    url(r'^(?P<objnames>[a-zA-Z0-9;_]+)$', 'objects'),
    url(r'^(?P<objname>[a-zA-Z0-9_]+)/(?P<objids>[0-9;]+)$', 'objects_details'),
)
