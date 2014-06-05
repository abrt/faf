from django.conf.urls import patterns, url
from django.views.generic import RedirectView

urlpatterns = patterns('webfaf.problems.views',
    url(r'^$', RedirectView.as_view(url='/problems/hot/')),

    url(r'^hot/$', 'hot'),
    url(r'^hot/(?P<os_release>[^/]+)/$', 'hot'),
    url(r'^hot/(?P<os_release>[^/]+)/(?P<associate>[^/]+)/$', 'hot'),
    url(r'^hot/(?P<os_release>[^/]+)/(?P<associate>[^/]+)/(?P<component>[^/]+)/$', 'hot'),

    url(r'^longterm/$', 'longterm'),
    url(r'^longterm/(?P<os_release>[^/]+)/$', 'longterm'),
    url(r'^longterm/(?P<os_release>[^/]+)/(?P<associate>[^/]+)/$', 'longterm'),
    url(r'^longterm/(?P<os_release>[^/]+)/(?P<associate>[^/]+)/(?P<component>[^/]+)/$', 'longterm'),

    url(r'^bthash/(?P<bthash>[a-fA-F0-9]+)/?$', 'bthash_forward'),

    url(r'^(?P<problem_id>\d+)/$', 'item'),
    url(r'^(?P<problem_id>\d+)/backtraces/$', 'backtraces'),
    url(r'^(?P<problem_id>\d+)/cluster/$', 'cluster'),
)
