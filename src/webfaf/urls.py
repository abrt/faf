# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import patterns, include, url

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
    url(r'^admin/', include(admin.site.urls)),
    # Include Django AJAX library
    url(r'^dajaxice/', include('dajaxice.urls')),
    url(r'^openid/', include('django_openid_auth.urls')),
    url(r'^logout/$', 'django.contrib.auth.views.logout', name="auth_logout")
)


# this is a hack to enable media (with correct prefix) while debugging
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
