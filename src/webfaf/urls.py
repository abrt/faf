# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from dajaxice.core import dajaxice_autodiscover

admin.autodiscover()
dajaxice_autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^summary/', include('webfaf.summary.urls')),
    url(r'^stats/', include('webfaf.stats.urls')),
    url(r'^$', 'webfaf.summary.views.index'),
    url(r'^problems/', include('webfaf.problems.urls')),
    url(r'^query/', include('webfaf.query.urls')),
    url(r'^reports/', include('webfaf.reports.urls')),
    url(r'^status/', include('webfaf.status.urls')),
    url(r'^dumpdirs/', include('webfaf.dumpdirs.urls')),
    url(r'^auth/', include('kobo.hub.urls.auth')),
    url(r'^task/', include('kobo.hub.urls.task')),
    url(r'^info/arch/', include('kobo.hub.urls.arch')),
    url(r'^info/channel/', include('kobo.hub.urls.channel')),
    url(r'^info/user/', include('kobo.hub.urls.user')),
    url(r'^info/worker/', include('kobo.hub.urls.worker')),
    url(r'^admin/', include(admin.site.urls)),
    # Include kobo hub xmlrpc module urls:
    url(r'^xmlrpc/', include('webfaf.xmlrpc.urls')),
    # Include Django AJAX library
    url(r'^(faf/)?dajaxice/', include('dajaxice.urls')),
    url(r'^openid/', include('django_openid_auth.urls')),
)


# this is a hack to enable media (with correct prefix) while debugging
if settings.DEBUG:
    import os
    import kobo
    import urlparse

    scheme, netloc, path, params, query, fragment = urlparse.urlparse(settings.MEDIA_URL)
    if not netloc:
        # netloc is empty -> media is not on remote server
        urlpatterns.extend(patterns('',
            url(r'^%s/kobo/(?P<path>.*)$' % path[1:-1], 'django.views.static.serve', kwargs={'document_root': os.path.join(os.path.dirname(kobo.__file__), 'hub', 'media')}),
        ))

    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static('/js/flot', document_root='/usr/share/flot')
    urlpatterns += static('/css/bootstrap', document_root='/usr/share/bootstrap/css')
    urlpatterns += static('/js/bootstrap', document_root='/usr/share/bootstrap/js')
    urlpatterns += static('/img/bootstrap', document_root='/usr/share/bootstrap/img')
    urlpatterns += static('/js/jquery', document_root='/usr/share/jquery')
    urlpatterns += static('/js/bootstrap', document_root='/usr/share/bootstrap/js')
    urlpatterns += static('/js/dajax', document_root='/usr/share/django-dajax/js')
    urlpatterns += static('/css/select2', document_root='/usr/share/select2/css')
    urlpatterns += static('/js/select2', document_root='/usr/share/select2/js')
    urlpatterns += static('/img/select2', document_root='/usr/share/select2/img')
    urlpatterns += staticfiles_urlpatterns()
