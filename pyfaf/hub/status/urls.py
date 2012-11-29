from django.conf.urls.defaults import *

urlpatterns = patterns('pyfaf.hub.status.views',
    url(r'^$', 'index'),
    url(r'^builds/$', 'builds'),
    url(r'^llvm/$', 'llvm'),
    url(r'^llvm/(?P<llvm_build_id>[0-9]+)$', 'llvm_details'),
    url(r'^llvm/(?P<llvm_build_id>[0-9]+)/(?P<lob_name>stdout|stderr)$', 'llvm_lob'),
    url(r'^llvm/bcfile/(?P<fileid>[0-9]+)$', 'llvm_bcfile'),
)
