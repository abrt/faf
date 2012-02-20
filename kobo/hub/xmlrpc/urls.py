# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *


urlpatterns = patterns("",
    # customize the index XML-RPC page if needed:
    # url(r"^$", "django.views.generic.simple.direct_to_template", kwargs={"template": "xmlrpc_help.html"}, name="help/xmlrpc"),
    url(r"^upload/", "kobo.django.upload.views.file_upload"),
    url(r"^client/", "kobo.django.xmlrpc.views.client_handler", name="help/xmlrpc/client"),
    url(r"^worker/", "kobo.django.xmlrpc.views.worker_handler", name="help/xmlrpc/worker"),
)
