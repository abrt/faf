from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.status.views',
    url(r'^$', 'index'),
    url(r'^builds/$', 'builds'),
    url(r'^llvm/$', 'llvm'),
)
