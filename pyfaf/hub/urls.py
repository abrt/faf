# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    #url(r"^$", 'hub.home.views.index_redirect', name="task/list"),
    url(r"^$", "django.views.generic.simple.direct_to_template", kwargs={"template": "index.html"}, name="index"),
    url(r"^auth/", include("kobo.hub.urls.auth")),
    url(r"^task/", include("kobo.hub.urls.task")),
    url(r"^info/arch/", include("kobo.hub.urls.arch")),
    url(r"^info/channel/", include("kobo.hub.urls.channel")),
    url(r"^info/user/", include("kobo.hub.urls.user")),
    url(r"^info/worker/", include("kobo.hub.urls.worker")),

    url(r'^admin/', include(admin.site.urls)),

    # Include kobo hub xmlrpc module urls:
    url(r"^xmlrpc/", include("pyfaf.hub.xmlrpc.urls")),
)


# this is a hack to enable media (with correct prefix) while debugging
if settings.DEBUG:
    import os
    import kobo
    import urlparse

    scheme, netloc, path, params, query, fragment = urlparse.urlparse(settings.MEDIA_URL)
    if not netloc:
        # netloc is empty -> media is not on remote server
        urlpatterns.extend(patterns("",
            url(r"^%s/kobo/(?P<path>.*)$" % path[1:-1], "django.views.static.serve", kwargs={"document_root": os.path.join(os.path.dirname(kobo.__file__), "hub", "media")}),
            url(r"^%s/(?P<path>.*)$" % path[1:-1], "django.views.static.serve", kwargs={"document_root": settings.MEDIA_ROOT}),
        ))
